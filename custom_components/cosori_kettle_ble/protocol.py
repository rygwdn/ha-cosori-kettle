"""BLE protocol implementation for Cosori Kettle."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .const import (
    ACK_HEADER_TYPE,
    BLE_CHUNK_SIZE,
    CMD_CTRL,
    CMD_HELLO,
    CMD_POLL,
    CMD_REGISTER,
    CMD_SET_BABY_FORMULA,
    CMD_SET_HOLD_TIME,
    CMD_SET_MODE,
    CMD_SET_MY_TEMP,
    CMD_STOP,
    CMD_TYPE_40,
    CMD_TYPE_A3,
    CMD_TYPE_D1,
    FRAME_MAGIC,
    MAX_TEMP_F,
    MAX_VALID_READING_F,
    MESSAGE_HEADER_TYPE,
    MIN_TEMP_F,
    MIN_VALID_READING_F,
)


@dataclass
class CompactStatus:
    """Compact status from kettle."""

    stage: int
    mode: int
    setpoint: int
    temp: int
    valid: bool = False


@dataclass
class ExtendedStatus:
    """Extended status from kettle."""

    stage: int
    mode: int
    setpoint: int
    temp: int
    my_temp: int
    configured_hold_time: int
    remaining_hold_time: int
    on_base: bool
    baby_formula_enabled: bool
    valid: bool = False


@dataclass
class Frame:
    """A parsed BLE frame.

    Supports both attribute access (frame.frame_type) and tuple unpacking
    for backward compatibility (frame_type, seq, payload = frame).
    """

    frame_type: int
    seq: int
    payload: bytes

    def __iter__(self):
        """Support tuple unpacking for backward compatibility."""
        return iter((self.frame_type, self.seq, self.payload))


class Envelope:
    """BLE packet envelope handler with Pythonic interface."""

    def __init__(self) -> None:
        """Initialize envelope."""
        self._buffer = bytearray()
        self._pos = 0

    def clear(self) -> None:
        """Clear the buffer."""
        self._buffer.clear()
        self._pos = 0

    @property
    def size(self) -> int:
        """Get buffer size."""
        return len(self._buffer)

    @property
    def remaining(self) -> int:
        """Get remaining unread data."""
        return max(0, len(self._buffer) - self._pos)

    def append(self, data: bytes) -> None:
        """Append data to buffer."""
        self._buffer.extend(data)

    @staticmethod
    def build(frame_type: int, seq: int, payload: bytes) -> bytes:
        """Build a complete packet with envelope header.

        Args:
            frame_type: Frame type (MESSAGE_HEADER_TYPE or ACK_HEADER_TYPE)
            seq: Sequence number
            payload: Payload bytes

        Returns:
            Complete packet with envelope header and checksum
        """
        payload_len = len(payload)
        packet = bytearray(6 + payload_len)

        packet[0] = FRAME_MAGIC
        packet[1] = frame_type
        packet[2] = seq
        packet[3] = payload_len & 0xFF
        packet[4] = (payload_len >> 8) & 0xFF
        packet[5] = 0x01  # Placeholder, will be calculated

        if payload:
            packet[6:] = payload

        # Calculate and set checksum
        packet[5] = Envelope._calculate_checksum(packet)

        return bytes(packet)

    def set_message_payload(self, seq: int, payload: bytes) -> bytes:
        """Build message packet (A522) and store for chunking.

        Args:
            seq: Sequence number
            payload: Payload bytes

        Returns:
            Complete packet
        """
        packet = self.build(MESSAGE_HEADER_TYPE, seq, payload)
        self._buffer = bytearray(packet)
        return packet

    @staticmethod
    def build_ack(seq: int, payload: bytes) -> bytes:
        """Build ACK packet (A512).

        Args:
            seq: Sequence number
            payload: Payload bytes

        Returns:
            Complete ACK packet
        """
        return Envelope.build(ACK_HEADER_TYPE, seq, payload)

    def get_chunks(self) -> list[bytes]:
        """Get stored packet split into BLE chunks.

        Returns:
            List of chunks, each <= BLE_CHUNK_SIZE bytes
        """
        return [
            bytes(self._buffer[i : i + BLE_CHUNK_SIZE])
            for i in range(0, len(self._buffer), BLE_CHUNK_SIZE)
        ]

    def __iter__(self):
        """Iterate over all available frames in the buffer.

        Yields:
            Frame objects for each complete, valid frame

        Example:
            for frame in envelope:
                print(f"Type: {frame.frame_type:02x}, Seq: {frame.seq}")
        """
        while True:
            frame = self.process_next_frame()
            if frame is None:
                break
            yield frame

    def process_next_frame(self, max_payload_size: int = 512) -> Optional[Frame]:
        """Process next frame from buffer.

        Args:
            max_payload_size: Maximum allowed payload size (prevents buffer overflow)

        Returns:
            Frame object if a valid frame was found, None otherwise
        """
        while True:
            # Find frame start
            frame_start = self._find_frame_start()
            if frame_start >= len(self._buffer):
                self._pos = len(self._buffer)
                return None

            self._pos = frame_start

            # Validate header
            header_info = self._validate_frame_header()
            if not header_info:
                self._pos += 1
                continue

            frame_type, seq, payload_len, checksum = header_info

            # Validate payload length
            if payload_len > max_payload_size:
                self._pos += 1
                continue

            frame_len = 6 + payload_len

            # Wait for complete frame
            if self._pos + frame_len > len(self._buffer):
                return None

            # Validate checksum
            frame_data = self._buffer[self._pos : self._pos + frame_len]
            calculated_checksum = self._calculate_checksum(frame_data)

            if checksum != calculated_checksum:
                self._pos += 1
                continue

            # Extract payload
            payload = bytes(frame_data[6:])

            # Advance position
            self._pos += frame_len

            return Frame(frame_type=frame_type, seq=seq, payload=payload)

    def compact(self) -> None:
        """Compact buffer by removing processed data."""
        if self._pos == 0:
            return
        if self._pos >= len(self._buffer):
            self.clear()
            return

        self._buffer = self._buffer[self._pos :]
        self._pos = 0

    def _find_frame_start(self) -> int:
        """Find next frame start (FRAME_MAGIC)."""
        for i in range(self._pos, len(self._buffer)):
            if self._buffer[i] == FRAME_MAGIC:
                return i
        return len(self._buffer)

    def _validate_frame_header(self) -> Optional[tuple[int, int, int, int]]:
        """Validate frame header at current position.

        Returns: (frame_type, seq, payload_len, checksum) or None
        """
        if self._pos + 6 > len(self._buffer):
            return None

        if self._buffer[self._pos] != FRAME_MAGIC:
            return None

        frame_type = self._buffer[self._pos + 1]
        seq = self._buffer[self._pos + 2]
        payload_len = self._buffer[self._pos + 3] | (self._buffer[self._pos + 4] << 8)
        checksum = self._buffer[self._pos + 5]

        return (frame_type, seq, payload_len, checksum)

    @staticmethod
    def _calculate_checksum(buffer: bytes | bytearray) -> int:
        """Calculate checksum for envelope."""
        # Detect protocol version
        is_v1 = len(buffer) > 6 and buffer[6] == 0x01

        if is_v1:
            # V1: iterative subtraction
            checksum = 0
            for i, byte in enumerate(buffer):
                byte_val = 0x01 if i == 5 else byte
                checksum = (checksum - byte_val) & 0xFF
            return checksum
        else:
            # V0: sum of header bytes
            if len(buffer) < 6:
                return 0
            return (FRAME_MAGIC + buffer[1] + buffer[2] + buffer[3] + buffer[4]) & 0xFF


def build_register_payload(protocol_version: int, registration_key: bytes) -> bytes:
    """Build register/pairing payload."""
    if len(registration_key) != 16:
        raise ValueError("Registration key must be 16 bytes")

    payload = bytearray(36)
    payload[0] = protocol_version
    payload[1] = CMD_REGISTER
    payload[2] = CMD_TYPE_D1
    payload[3] = 0x00

    # Convert binary to hex ASCII
    hex_key = registration_key.hex()
    payload[4:] = hex_key.encode("ascii")

    return bytes(payload)


def build_hello_payload(protocol_version: int, registration_key: bytes) -> bytes:
    """Build hello/reconnect payload."""
    if len(registration_key) != 16:
        raise ValueError("Registration key must be 16 bytes")

    payload = bytearray(36)
    payload[0] = protocol_version
    payload[1] = CMD_HELLO
    payload[2] = CMD_TYPE_D1
    payload[3] = 0x00

    # Convert binary to hex ASCII
    hex_key = registration_key.hex()
    payload[4:] = hex_key.encode("ascii")

    return bytes(payload)


def build_status_request_payload(protocol_version: int) -> bytes:
    """Build status request (POLL) payload."""
    return bytes([protocol_version, CMD_POLL, CMD_TYPE_40, 0x00])


def build_compact_status_request_payload(protocol_version: int) -> bytes:
    """Build compact status request (CTRL) payload."""
    return bytes([protocol_version, CMD_CTRL, CMD_TYPE_40, 0x00])


def build_set_my_temp_payload(protocol_version: int, temp_f: int) -> bytes:
    """Build set my temp payload."""
    # Clamp to valid range
    temp_f = max(MIN_TEMP_F, min(MAX_TEMP_F, temp_f))
    return bytes([protocol_version, CMD_SET_MY_TEMP, CMD_TYPE_A3, 0x00, temp_f])


def build_set_baby_formula_payload(protocol_version: int, enabled: bool) -> bytes:
    """Build set baby formula payload."""
    return bytes([protocol_version, CMD_SET_BABY_FORMULA, CMD_TYPE_A3, 0x00, 0x01 if enabled else 0x00])


def build_set_hold_time_payload(protocol_version: int, seconds: int) -> bytes:
    """Build set hold time payload."""
    return bytes([
        protocol_version,
        CMD_SET_HOLD_TIME,
        CMD_TYPE_A3,
        0x00,
        0x00,
        0x01 if seconds > 0 else 0x00,
        seconds & 0xFF,
        (seconds >> 8) & 0xFF,
    ])


def build_set_mode_payload(
    protocol_version: int, mode: int, temp_f: int, hold_time_seconds: int
) -> bytes:
    """Build set mode payload."""
    return bytes([
        protocol_version,
        CMD_SET_MODE,
        CMD_TYPE_A3,
        0x00,
        mode,
        temp_f,
        0x01 if hold_time_seconds > 0 else 0x00,
        (hold_time_seconds >> 8) & 0xFF,
        hold_time_seconds & 0xFF,
    ])


def build_stop_payload(protocol_version: int) -> bytes:
    """Build stop payload."""
    return bytes([protocol_version, CMD_STOP, CMD_TYPE_A3, 0x00])


def parse_compact_status(payload: bytes) -> CompactStatus:
    """Parse compact status packet."""
    if len(payload) < 9 or payload[1] != CMD_CTRL:
        return CompactStatus(0, 0, 0, 0, False)

    temp = payload[7]
    if temp < MIN_VALID_READING_F or temp > MAX_VALID_READING_F:
        return CompactStatus(0, 0, 0, 0, False)

    return CompactStatus(
        stage=payload[4],
        mode=payload[5],
        setpoint=payload[6],
        temp=temp,
        valid=True,
    )


def parse_extended_status(payload: bytes) -> ExtendedStatus:
    """Parse extended status packet."""
    if len(payload) < 29 or payload[1] != CMD_POLL:
        return ExtendedStatus(0, 0, 0, 0, 0, 0, 0, False, False, False)

    temp = payload[7]
    if temp < MIN_VALID_READING_F or temp > MAX_VALID_READING_F:
        return ExtendedStatus(0, 0, 0, 0, 0, 0, 0, False, False, False)

    my_temp = payload[8]
    if my_temp < MIN_TEMP_F or my_temp > MAX_TEMP_F:
        my_temp = 0

    return ExtendedStatus(
        stage=payload[4],
        mode=payload[5],
        setpoint=payload[6],
        temp=temp,
        my_temp=my_temp,
        configured_hold_time=(payload[11] << 8) | payload[10],
        remaining_hold_time=(payload[13] << 8) | payload[12],
        on_base=payload[14] == 0x00,
        baby_formula_enabled=payload[26] == 0x01,
        valid=True,
    )
