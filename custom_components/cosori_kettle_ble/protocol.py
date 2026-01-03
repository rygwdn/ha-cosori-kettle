"""BLE protocol implementation for Cosori Kettle.

This module now imports from the standalone cosori_kettle library.
"""
from __future__ import annotations

# Import everything from standalone library
import sys
from pathlib import Path

# Add library to path
lib_path = Path(__file__).parent.parent.parent / "cosori_kettle"
sys.path.insert(0, str(lib_path))

from cosori_kettle.protocol import (
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
    CompactStatus,
    ExtendedStatus,
    FRAME_MAGIC,
    Frame,
    MAX_TEMP_F,
    MAX_VALID_READING_F,
    MESSAGE_HEADER_TYPE,
    MIN_TEMP_F,
    MIN_VALID_READING_F,
    build_compact_status_request_frame,
    build_hello_frame,
    build_packet,
    build_register_frame,
    build_set_baby_formula_frame,
    build_set_hold_time_frame,
    build_set_mode_frame,
    build_set_my_temp_frame,
    build_status_request_frame,
    build_stop_frame,
    parse_compact_status,
    parse_extended_status,
    parse_frames,
    split_into_packets,
)

__all__ = [
    "ACK_HEADER_TYPE",
    "BLE_CHUNK_SIZE",
    "CMD_CTRL",
    "CMD_HELLO",
    "CMD_POLL",
    "CMD_REGISTER",
    "CMD_SET_BABY_FORMULA",
    "CMD_SET_HOLD_TIME",
    "CMD_SET_MODE",
    "CMD_SET_MY_TEMP",
    "CMD_STOP",
    "CMD_TYPE_40",
    "CMD_TYPE_A3",
    "CMD_TYPE_D1",
    "CompactStatus",
    "ExtendedStatus",
    "FRAME_MAGIC",
    "Frame",
    "MAX_TEMP_F",
    "MAX_VALID_READING_F",
    "MESSAGE_HEADER_TYPE",
    "MIN_TEMP_F",
    "MIN_VALID_READING_F",
    "build_compact_status_request_frame",
    "build_hello_frame",
    "build_packet",
    "build_register_frame",
    "build_set_baby_formula_frame",
    "build_set_hold_time_frame",
    "build_set_mode_frame",
    "build_set_my_temp_frame",
    "build_status_request_frame",
    "build_stop_frame",
    "parse_compact_status",
    "parse_extended_status",
    "parse_frames",
    "split_into_packets",
]
