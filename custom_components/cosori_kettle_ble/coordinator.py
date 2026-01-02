"""DataUpdateCoordinator for Cosori Kettle BLE."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import establish_connection

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CHAR_RX_UUID,
    CHAR_TX_UUID,
    DOMAIN,
    PROTOCOL_VERSION_V1,
    SERVICE_UUID,
    UPDATE_INTERVAL,
)
from .protocol import (
    Envelope,
    ExtendedStatus,
    Frame,
    build_hello_payload,
    build_set_baby_formula_payload,
    build_set_mode_payload,
    build_set_my_temp_payload,
    build_status_request_payload,
    build_stop_payload,
    parse_extended_status,
)

_LOGGER = logging.getLogger(__name__)


class CosoriKettleCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for Cosori Kettle BLE communication."""

    def __init__(
        self,
        hass: HomeAssistant,
        ble_device: BLEDevice,
        device_id: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{device_id}",
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self._ble_device = ble_device
        self._device_id = device_id
        self._protocol_version = PROTOCOL_VERSION_V1
        self._registration_key = bytes.fromhex(device_id.replace(":", ""))
        self._client: BleakClient | None = None
        self._rx_envelope = Envelope()
        self._tx_seq = 0
        self._connected = False
        self._lock = asyncio.Lock()

        # ACK handling
        self._pending_ack: dict[int, asyncio.Future[tuple[int, bytes]]] = {}
        self._ack_timeout = 5.0  # seconds

    async def async_start(self) -> None:
        """Start the coordinator."""
        try:
            await self._connect()
            # Do initial update
            await self.async_config_entry_first_refresh()
        except Exception as err:
            _LOGGER.error("Failed to start coordinator: %s", err)
            raise

    async def async_stop(self) -> None:
        """Stop the coordinator."""
        await self._disconnect()

    async def _connect(self) -> None:
        """Connect to the device."""
        if self._connected:
            return

        _LOGGER.debug("Connecting to %s", self._ble_device.address)

        try:
            # Get updated BLE device from HA's Bluetooth manager
            ble_device = bluetooth.async_ble_device_from_address(
                self.hass, self._ble_device.address, connectable=True
            )

            if ble_device is None:
                raise UpdateFailed("Device not found")

            # Use retry connector for robust connection
            self._client = await establish_connection(
                BleakClient,
                ble_device,
                self._ble_device.address,
                disconnected_callback=self._on_disconnect,
            )

            # Subscribe to notifications
            await self._client.start_notify(CHAR_RX_UUID, self._notification_handler)

            # Send hello
            await self._send_hello()

            self._connected = True
            _LOGGER.info("Connected to %s", self._ble_device.address)

        except (BleakError, asyncio.TimeoutError) as err:
            _LOGGER.error("Failed to connect: %s", err)
            await self._disconnect()
            raise UpdateFailed(f"Failed to connect: {err}") from err

    def _on_disconnect(self, client: BleakClient) -> None:
        """Handle disconnection."""
        _LOGGER.warning("Disconnected from %s", self._ble_device.address)
        self._connected = False

    async def _disconnect(self) -> None:
        """Disconnect from the device."""
        if self._client and self._client.is_connected:
            try:
                await self._client.stop_notify(CHAR_RX_UUID)
                await self._client.disconnect()
            except BleakError as err:
                _LOGGER.debug("Error during disconnect: %s", err)
        self._client = None
        self._connected = False

    @callback
    def _notification_handler(self, sender: int, data: bytearray) -> None:
        """Handle BLE notifications."""
        _LOGGER.debug("Received notification: %s", data.hex())
        self._rx_envelope.append(bytes(data))

        # Process all available frames
        for frame in self._rx_envelope:
            _LOGGER.debug(
                "Processed frame: type=%02x seq=%02x payload=%s",
                frame.frame_type,
                frame.seq,
                frame.payload.hex(),
            )

            # Handle ACK frames
            if frame.frame_type == 0x12:  # ACK_HEADER_TYPE
                self._handle_ack(frame.seq, frame.payload)

            # Parse status
            status = parse_extended_status(frame.payload)
            if status.valid:
                self._update_data_from_status(status)

        # Compact buffer
        self._rx_envelope.compact()

    def _handle_ack(self, seq: int, payload: bytes) -> None:
        """Handle ACK frame."""
        # Extract error code from payload[4] if available
        error_code = payload[4] if len(payload) > 4 else 0
        _LOGGER.debug("ACK received: seq=%02x error_code=%02x", seq, error_code)

        # Complete pending future if exists
        if seq in self._pending_ack:
            future = self._pending_ack.pop(seq)
            if not future.done():
                future.set_result((error_code, payload))
                _LOGGER.debug("ACK future completed for seq=%02x", seq)

    def _update_data_from_status(self, status: ExtendedStatus) -> None:
        """Update coordinator data from status."""
        self.async_set_updated_data({
            "stage": status.stage,
            "mode": status.mode,
            "setpoint": status.setpoint,
            "temperature": status.temp,
            "my_temp": status.my_temp,
            "configured_hold_time": status.configured_hold_time,
            "remaining_hold_time": status.remaining_hold_time,
            "on_base": status.on_base,
            "baby_formula_enabled": status.baby_formula_enabled,
            "heating": status.stage > 0,
        })

    async def _send_hello(self) -> None:
        """Send hello packet."""
        payload = build_hello_payload(self._protocol_version, self._registration_key)
        await self._send_packet(payload)

    async def _send_packet(self, payload: bytes, wait_for_ack: bool = False) -> tuple[int, bytes] | None:
        """Send a packet to the device.

        Args:
            payload: The payload to send
            wait_for_ack: If True, wait for ACK response from device

        Returns:
            If wait_for_ack is True: (error_code, ack_payload) tuple
            If wait_for_ack is False: None

        Raises:
            UpdateFailed: If not connected or ACK timeout
        """
        if not self._client or not self._client.is_connected:
            raise UpdateFailed("Not connected to device")

        envelope = Envelope()
        packet = envelope.set_message_payload(self._tx_seq, payload)
        seq = self._tx_seq
        self._tx_seq = (self._tx_seq + 1) & 0xFF

        # Create future for ACK if requested
        ack_future: asyncio.Future[tuple[int, bytes]] | None = None
        if wait_for_ack:
            ack_future = asyncio.Future()
            self._pending_ack[seq] = ack_future

        try:
            # Split into chunks if needed
            chunks = envelope.get_chunks()
            for chunk in chunks:
                _LOGGER.debug("Sending chunk: %s", chunk.hex())
                await self._client.write_gatt_char(CHAR_TX_UUID, chunk, response=False)
                await asyncio.sleep(0.05)  # Small delay between chunks

            # Wait for ACK if requested
            if wait_for_ack and ack_future:
                try:
                    error_code, ack_payload = await asyncio.wait_for(
                        ack_future, timeout=self._ack_timeout
                    )
                    if error_code != 0:
                        _LOGGER.warning("Device returned error code: %02x", error_code)
                    return (error_code, ack_payload)
                except asyncio.TimeoutError:
                    _LOGGER.error("Timeout waiting for ACK (seq=%02x)", seq)
                    raise UpdateFailed(f"Timeout waiting for ACK (seq={seq:02x})")

            return None
        finally:
            # Clean up pending ACK if not completed
            if wait_for_ack and seq in self._pending_ack:
                self._pending_ack.pop(seq, None)

    async def _async_update_data(self) -> dict[str, Any]:
        """Poll the device for status."""
        async with self._lock:
            try:
                # Ensure connection
                if not self._connected:
                    await self._connect()

                # Request status
                payload = build_status_request_payload(self._protocol_version)
                await self._send_packet(payload)

                # Wait for response
                await asyncio.sleep(0.5)

                # Return current data
                return self.data or {}

            except (BleakError, asyncio.TimeoutError) as err:
                _LOGGER.error("Failed to update: %s", err)
                self._connected = False
                raise UpdateFailed(f"Failed to update: {err}") from err

    async def async_set_mode(self, mode: int, temp_f: int, hold_time: int) -> None:
        """Set heating mode."""
        async with self._lock:
            payload = build_set_mode_payload(self._protocol_version, mode, temp_f, hold_time)
            result = await self._send_packet(payload, wait_for_ack=True)
            if result:
                error_code, ack_payload = result
                if error_code != 0:
                    raise UpdateFailed(f"Device rejected set_mode command: error={error_code:02x}")
                # Verify the ACK is for the correct command
                if len(ack_payload) > 1 and ack_payload[1] != 0xF0:  # CMD_SET_MODE
                    _LOGGER.warning("ACK command mismatch: expected F0, got %02x", ack_payload[1])

    async def async_set_my_temp(self, temp_f: int) -> None:
        """Set my temp."""
        async with self._lock:
            payload = build_set_my_temp_payload(self._protocol_version, temp_f)
            result = await self._send_packet(payload, wait_for_ack=True)
            if result:
                error_code, ack_payload = result
                if error_code != 0:
                    raise UpdateFailed(f"Device rejected set_my_temp command: error={error_code:02x}")
                if len(ack_payload) > 1 and ack_payload[1] != 0xF3:  # CMD_SET_MY_TEMP
                    _LOGGER.warning("ACK command mismatch: expected F3, got %02x", ack_payload[1])

    async def async_set_baby_formula(self, enabled: bool) -> None:
        """Set baby formula mode."""
        async with self._lock:
            payload = build_set_baby_formula_payload(self._protocol_version, enabled)
            result = await self._send_packet(payload, wait_for_ack=True)
            if result:
                error_code, ack_payload = result
                if error_code != 0:
                    raise UpdateFailed(f"Device rejected set_baby_formula command: error={error_code:02x}")
                if len(ack_payload) > 1 and ack_payload[1] != 0xF5:  # CMD_SET_BABY_FORMULA
                    _LOGGER.warning("ACK command mismatch: expected F5, got %02x", ack_payload[1])

    async def async_stop_heating(self) -> None:
        """Stop heating."""
        async with self._lock:
            payload = build_stop_payload(self._protocol_version)
            result = await self._send_packet(payload, wait_for_ack=True)
            if result:
                error_code, ack_payload = result
                if error_code != 0:
                    raise UpdateFailed(f"Device rejected stop command: error={error_code:02x}")
                if len(ack_payload) > 1 and ack_payload[1] != 0xF4:  # CMD_STOP
                    _LOGGER.warning("ACK command mismatch: expected F4, got %02x", ack_payload[1])
