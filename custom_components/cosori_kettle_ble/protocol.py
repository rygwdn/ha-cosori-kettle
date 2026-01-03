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
class Envelope:
    """BLE packet envelope (frame with header).

    Represents a single frame with type, sequence number, and payload.
    Supports tuple unpacking for backward compatibility.
    """

    frame_type: int
    seq: int
    payload: bytes

    def __iter__(self):
        """Support tuple unpacking for backward compatibility."""
        return iter((self.frame_type, self.seq, self.payload))


def build_packet(frame_type: int, seq: int, payload: bytes) -> bytes:
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
    packet[5] = _calculate_checksum(packet)

    return bytes(packet)


def chunk_packet(packet: bytes) -> list[bytes]:
    """Split packet into BLE-sized chunks.

    Args:
        packet: Complete packet to split

    Returns:
        List of chunks, each <= BLE_CHUNK_SIZE bytes
    """
    return [packet[i : i + BLE_CHUNK_SIZE] for i in range(0, len(packet), BLE_CHUNK_SIZE)]


def parse_frames(buffer: bytearray, max_payload_size: int = 512) -> tuple[list[Envelope], int]:
    """Parse all complete frames from buffer.

    Args:
        buffer: Buffer containing received data
        max_payload_size: Maximum allowed payload size

    Returns:
        Tuple of (frames list, bytes_consumed)
    """
    frames = []
    pos = 0

    while pos < len(buffer):
        # Find frame start
        frame_start = _find_frame_start(buffer, pos)
        if frame_start >= len(buffer):
            break

        pos = frame_start

        # Validate header
        if pos + 6 > len(buffer):
            break

        if buffer[pos] != FRAME_MAGIC:
            pos += 1
            continue

        frame_type = buffer[pos + 1]
        seq = buffer[pos + 2]
        payload_len = buffer[pos + 3] | (buffer[pos + 4] << 8)
        checksum = buffer[pos + 5]

        # Validate payload length
        if payload_len > max_payload_size:
            pos += 1
            continue

        frame_len = 6 + payload_len

        # Wait for complete frame
        if pos + frame_len > len(buffer):
            break

        # Validate checksum
        frame_data = buffer[pos : pos + frame_len]
        calculated_checksum = _calculate_checksum(frame_data)

        if checksum != calculated_checksum:
            pos += 1
            continue

        # Extract payload and create envelope
        payload = bytes(frame_data[6:])
        frames.append(Envelope(frame_type=frame_type, seq=seq, payload=payload))

        pos += frame_len

    return frames, pos


def _find_frame_start(buffer: bytearray, start_pos: int) -> int:
    """Find next frame start (FRAME_MAGIC) in buffer."""
    for i in range(start_pos, len(buffer)):
        if buffer[i] == FRAME_MAGIC:
            return i
    return len(buffer)


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


# Backward compatibility alias
Frame = Envelope


class _EnvelopeCompat:
    """Backward compatibility wrapper for old Envelope API used in tests."""

    def __init__(self):
        """Initialize compatibility wrapper."""
        self._buffer = bytearray()
        self._packet = b""

    def set_message_payload(self, seq: int, payload: bytes) -> bytes:
        """Build message packet (backward compat)."""
        self._packet = build_packet(MESSAGE_HEADER_TYPE, seq, payload)
        return self._packet

    def append(self, data: bytes) -> None:
        """Append data to buffer (backward compat)."""
        self._buffer.extend(data)

    def process_next_frame(self, max_payload_size: int = 512) -> Envelope | None:
        """Process next frame (backward compat)."""
        # Parse frames from current buffer
        pos = 0
        while pos < len(self._buffer):
            # Find frame start
            frame_start = _find_frame_start(self._buffer, pos)
            if frame_start >= len(self._buffer):
                break

            pos = frame_start

            # Validate header
            if pos + 6 > len(self._buffer):
                break

            if self._buffer[pos] != FRAME_MAGIC:
                pos += 1
                continue

            frame_type = self._buffer[pos + 1]
            seq = self._buffer[pos + 2]
            payload_len = self._buffer[pos + 3] | (self._buffer[pos + 4] << 8)
            checksum = self._buffer[pos + 5]

            # Validate payload length
            if payload_len > max_payload_size:
                pos += 1
                continue

            frame_len = 6 + payload_len

            # Wait for complete frame
            if pos + frame_len > len(self._buffer):
                break

            # Validate checksum
            frame_data = self._buffer[pos : pos + frame_len]
            calculated_checksum = _calculate_checksum(frame_data)

            if checksum != calculated_checksum:
                pos += 1
                continue

            # Extract payload and create envelope
            payload = bytes(frame_data[6:])
            envelope = Envelope(frame_type=frame_type, seq=seq, payload=payload)

            # Remove consumed bytes (up to and including this frame)
            self._buffer = self._buffer[pos + frame_len :]

            return envelope

        return None

    def get_chunks(self) -> list[bytes]:
        """Get packet chunks (backward compat)."""
        return chunk_packet(self._packet)


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
