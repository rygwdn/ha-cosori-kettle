"""Config flow for Cosori Kettle BLE integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.const import CONF_ADDRESS
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_DEVICE_ID, DOMAIN, SERVICE_UUID

_LOGGER = logging.getLogger(__name__)


class CosoriKettleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Cosori Kettle BLE."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_devices: dict[str, BluetoothServiceInfoBleak] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle the bluetooth discovery step."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        self._discovery_info = discovery_info

        # Check if device has our service
        if SERVICE_UUID.lower() not in [
            str(uuid).lower() for uuid in discovery_info.service_uuids
        ]:
            return self.async_abort(reason="not_supported")

        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle user confirmation of discovered device."""
        assert self._discovery_info is not None

        if user_input is not None:
            return self.async_create_entry(
                title=self._discovery_info.name or "Cosori Kettle",
                data={
                    CONF_DEVICE_ID: self._discovery_info.address,
                    CONF_ADDRESS: self._discovery_info.address,
                },
            )

        self._set_confirm_only()

        return self.async_show_form(
            step_id="confirm",
            description_placeholders={
                "name": self._discovery_info.name or "Cosori Kettle",
                "address": self._discovery_info.address,
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the user step to pick discovered device."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()

            discovery_info = self._discovered_devices[address]

            return self.async_create_entry(
                title=discovery_info.name or "Cosori Kettle",
                data={
                    CONF_DEVICE_ID: address,
                    CONF_ADDRESS: address,
                },
            )

        # Scan for devices
        current_addresses = self._async_current_ids()
        discovered = await bluetooth.async_discovered_service_info(self.hass)

        self._discovered_devices = {}
        for info in discovered:
            if info.address in current_addresses:
                continue
            if SERVICE_UUID.lower() in [str(uuid).lower() for uuid in info.service_uuids]:
                self._discovered_devices[info.address] = info

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_ADDRESS): vol.In({
                    address: f"{info.name or 'Cosori Kettle'} ({address})"
                    for address, info in self._discovered_devices.items()
                }),
            }),
        )
