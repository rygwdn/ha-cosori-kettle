"""Command state machine for Cosori Kettle control sequences."""

import asyncio
from enum import Enum
from typing import Optional
import time

from .protocol import PacketBuilder


class CommandState(Enum):
    """Command state machine states."""
    IDLE = "idle"
    HANDSHAKE_HELLO = "handshake_hello"
    HANDSHAKE_POLL = "handshake_poll"
    START_HELLO5 = "start_hello5"
    START_SETPOINT = "start_setpoint"
    START_WAIT_STATUS = "start_wait_status"
    START_CTRL = "start_ctrl"
    START_CTRL_REINFORCE = "start_ctrl_reinforce"
    STOP_PRE_F4 = "stop_pre_f4"
    STOP_CTRL = "stop_ctrl"
    STOP_POST_F4 = "stop_post_f4"


# Timing constants (milliseconds)
HANDSHAKE_DELAY_MS = 80
PRE_SETPOINT_DELAY_MS = 60
POST_SETPOINT_DELAY_MS = 100
CONTROL_DELAY_MS = 50


class CommandStateMachine:
    """Async state machine for executing kettle command sequences."""
    
    def __init__(self, send_packet_callback, get_seq_callback, get_status_seq_callback, 
                 use_scan_hello: bool = False):
        """
        Args:
            send_packet_callback: Function(bytes) -> None to send packet
            get_seq_callback: Function() -> int to get next sequence number
            get_status_seq_callback: Function() -> int to get last status sequence
            use_scan_hello: If True, use scan.py hello for hw 1.0.00/sw R0007V0012
        """
        self.state = CommandState.IDLE
        self.state_start_time = 0.0
        self.send_packet = send_packet_callback
        self.get_seq = get_seq_callback
        self.get_status_seq = get_status_seq_callback
        self.use_scan_hello = use_scan_hello
        
        # Pending command parameters
        self.pending_mode: Optional[int] = None
        self.pending_temp_f: Optional[int] = None
    
    def start_registration(self) -> None:
        """Start registration handshake sequence."""
        self.state = CommandState.HANDSHAKE_HELLO
        self.state_start_time = time.time()
    
    def start_heating(self, mode: int, temp_f: int) -> None:
        """Start heating sequence."""
        self.pending_mode = mode
        self.pending_temp_f = temp_f
        self.state = CommandState.START_HELLO5
        self.state_start_time = time.time()
    
    def start_stop(self) -> None:
        """Start stop heating sequence."""
        self.state = CommandState.STOP_PRE_F4
        self.state_start_time = time.time()
    
    def process(self) -> None:
        """Process current state. Call this periodically (synchronous)."""
        now = time.time()
        elapsed_ms = (now - self.state_start_time) * 1000
        
        if self.state == CommandState.IDLE:
            return
        
        elif self.state == CommandState.HANDSHAKE_HELLO:
            # Send registration hello packet (single packet, may span multiple BLE writes)
            # seq = self.get_seq()
            hello_pkt = PacketBuilder.make_hello(0, use_scan_version=self.use_scan_hello)
            self.send_packet(hello_pkt)
            self.state = CommandState.HANDSHAKE_POLL
            self.state_start_time = now
        
        elif self.state == CommandState.HANDSHAKE_POLL:
            if elapsed_ms >= HANDSHAKE_DELAY_MS:
                seq = self.get_seq()
                poll_pkt = PacketBuilder.make_poll(seq)
                self.send_packet(poll_pkt)
                self.state = CommandState.IDLE
        
        elif self.state == CommandState.START_HELLO5:
            seq = self.get_seq()
            hello5_pkt = PacketBuilder.make_hello5(seq)
            self.send_packet(hello5_pkt)
            self.state = CommandState.START_SETPOINT
            self.state_start_time = now
        
        elif self.state == CommandState.START_SETPOINT:
            if elapsed_ms >= PRE_SETPOINT_DELAY_MS:
                seq = self.get_seq()
                setpoint_pkt = PacketBuilder.make_setpoint(
                    seq, self.pending_mode, self.pending_temp_f
                )
                self.send_packet(setpoint_pkt)
                self.state = CommandState.START_WAIT_STATUS
                self.state_start_time = now
        
        elif self.state == CommandState.START_WAIT_STATUS:
            if elapsed_ms >= POST_SETPOINT_DELAY_MS:
                # Proceed to control even if no status received
                seq_base = self.get_status_seq() or self.get_seq()
                ctrl_pkt = PacketBuilder.make_ctrl(seq_base)
                self.send_packet(ctrl_pkt)
                self.state = CommandState.START_CTRL
                self.state_start_time = now
        
        elif self.state == CommandState.START_CTRL:
            if elapsed_ms >= CONTROL_DELAY_MS:
                seq_ack = self.get_seq()
                ctrl_pkt = PacketBuilder.make_ctrl(seq_ack)
                self.send_packet(ctrl_pkt)
                self.state = CommandState.START_CTRL_REINFORCE
                self.state_start_time = now
        
        elif self.state == CommandState.START_CTRL_REINFORCE:
            if elapsed_ms >= CONTROL_DELAY_MS:
                self.state = CommandState.IDLE
        
        elif self.state == CommandState.STOP_PRE_F4:
            seq = self.get_seq()
            f4_pkt = PacketBuilder.make_f4(seq)
            self.send_packet(f4_pkt)
            self.state = CommandState.STOP_CTRL
            self.state_start_time = now
        
        elif self.state == CommandState.STOP_CTRL:
            if elapsed_ms >= CONTROL_DELAY_MS:
                seq_ctrl = self.get_status_seq() or self.get_seq()
                ctrl_pkt = PacketBuilder.make_ctrl(seq_ctrl)
                self.send_packet(ctrl_pkt)
                self.state = CommandState.STOP_POST_F4
                self.state_start_time = now
        
        elif self.state == CommandState.STOP_POST_F4:
            if elapsed_ms >= CONTROL_DELAY_MS:
                seq = self.get_seq()
                f4_pkt = PacketBuilder.make_f4(seq)
                self.send_packet(f4_pkt)
                self.state = CommandState.IDLE
