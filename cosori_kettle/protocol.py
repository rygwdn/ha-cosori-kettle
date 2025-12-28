"""Protocol layer for Cosori Kettle BLE communication."""

from dataclasses import dataclass
from typing import Optional, Tuple
import struct


# Protocol constants
FRAME_MAGIC = 0xA5
FRAME_TYPE_COMPACT_STATUS = 0x22
FRAME_TYPE_EXTENDED_STATUS = 0x12
FRAME_TYPE_COMMAND_A5_22 = 0x22
FRAME_TYPE_COMMAND_A5_12 = 0x12
FRAME_TYPE_POLL = 0x21

# Temperature limits (Fahrenheit)
MIN_TEMP_F = 104
MAX_TEMP_F = 212
MIN_VALID_READING_F = 40
MAX_VALID_READING_F = 230

# Operating modes
MODE_BOIL = 0x04
MODE_HEAT = 0x06

# Registration handshake payloads (header will be computed by build_send)
# Default (from C++ implementation) - works with most firmware versions
HELLO_PAYLOAD_DEFAULT = bytes.fromhex(
    '0181d100'  # Header
    '3634323837613931376537343661303733313136'  # Part 1 + 2
    '366237366634336435636262'  # Part 3
)

# Version-specific (from scan.py) - for hardware 1.0.00, software R0007V0012
HELLO_PAYLOAD_SCAN = bytes.fromhex(
    '0181d100'  # Header
    '39393033653031613363'  # Part 1
    '3362616138663663373163626235313637653764'  # Part 2  
    '3566'  # Part 3
)


@dataclass
class StatusPacket:
    """Status packet from kettle (compact 0x22 or extended 0x12)."""
    seq: int
    temperature_f: int
    setpoint_f: int
    heating: bool
    stage: int
    mode: int
    on_base: Optional[bool] = None  # Only available in extended packets (0x12)
    packet_type: str = "compact"  # "compact" or "extended"


@dataclass
class UnknownPacket:
    """Unknown packet type."""
    seq: int
    frame_type: int
    payload: bytes


class PacketBuilder:
    """Builds protocol packets for Cosori Kettle."""
    
    @staticmethod
    def calculate_checksum(packet: bytes) -> int:
        """Calculate packet checksum.
        
        Algorithm: Build packet with checksum=0x01, then for each byte:
        checksum = (checksum - byte) & 0xFF
        """
        checksum = 0
        for byte in packet:
            checksum = (checksum - byte) & 0xFF
        return checksum
    
    @staticmethod
    def build_send(seq: int, payload: bytes) -> bytes:
        """Build send frame (0x22 - commands sent to kettle)."""
        payload_len = len(payload)
        len_lo = payload_len & 0xFF
        len_hi = (payload_len >> 8) & 0xFF
        
        # Build packet with checksum=0x01 initially
        packet = bytes([FRAME_MAGIC, 0x22, seq, len_lo, len_hi, 0x01]) + payload
        
        # Calculate actual checksum
        checksum = PacketBuilder.calculate_checksum(packet)
        
        # Replace checksum byte
        return packet[:5] + bytes([checksum]) + packet[6:]
    
    @staticmethod
    def build_recv(seq: int, payload: bytes) -> bytes:
        """Build recv frame (0x12 - control/ack packets sent to kettle)."""
        payload_len = len(payload)
        len_lo = payload_len & 0xFF
        len_hi = (payload_len >> 8) & 0xFF
        
        # Build packet with checksum=0x01 initially
        packet = bytes([FRAME_MAGIC, 0x12, seq, len_lo, len_hi, 0x01]) + payload
        
        # Calculate actual checksum
        checksum = PacketBuilder.calculate_checksum(packet)
        
        # Replace checksum byte
        return packet[:5] + bytes([checksum]) + packet[6:]
    
    @staticmethod
    def make_poll(seq: int) -> bytes:
        """Create poll/status request packet (0x21)."""
        # original
        # payload = bytes([0x00, 0x40, 0x40, 0x00])
        # return PacketBuilder.build_send(seq, bytes([0x00, 0x40, 0x40, 0x00]))
        
        # mine..
        return PacketBuilder.build_send(seq, bytes([0x01, 0x40, 0x40, 0x00]))
        # Value: A522 0104 00B2 0140 4000

        # # Build packet with checksum=0x01 initially
        # packet = bytes([FRAME_MAGIC, 0x22, seq, 0x04, 0x00, 0xB2]) + payload
        
        # # Calculate actual checksum
        # # TODO: this should be 'set_checksum' 
        # # TODO: should have a 'make_payload' that takes payload & frame type, sets magic, sets the sequence, and then sets the checksum
        # checksum = PacketBuilder.calculate_checksum(packet)
        
        # # Replace checksum byte
        # return packet[:5] + bytes([checksum]) + packet[6:]
    
    @staticmethod
    def make_hello(seq: int, use_scan_version: bool = False) -> bytes:
        """Create registration hello packet (0x22 with combined payload).
        
        Args:
            seq: Sequence number
            use_scan_version: If True, use scan.py version for hw 1.0.00/sw R0007V0012
        """
        payload = HELLO_PAYLOAD_SCAN if use_scan_version else HELLO_PAYLOAD_DEFAULT
        return PacketBuilder.build_send(seq, payload)
    
    @staticmethod
    def make_hello5(seq: int) -> bytes:
        """Create HELLO5 packet (0x22 with 0xF2A3 payload)."""
        payload = bytes([0x00, 0xF2, 0xA3, 0x00, 0x00, 0x01, 0x10, 0x0E])
        return PacketBuilder.build_send(seq, payload)
    
    @staticmethod
    def make_setpoint(seq: int, mode: int, temp_f: int) -> bytes:
        """Create setpoint packet (0x22 with 0xF0A3 payload)."""
        payload = bytes([0x00, 0xF0, 0xA3, 0x00, mode, temp_f, 0x01, 0x10, 0x0E])
        return PacketBuilder.build_send(seq, payload)
    
    @staticmethod
    def make_f4(seq: int) -> bytes:
        """Create F4 packet (0x22 with 0xF4A3 payload)."""
        payload = bytes([0x00, 0xF4, 0xA3, 0x00])
        return PacketBuilder.build_send(seq, payload)
    
    @staticmethod
    def make_ctrl(seq: int) -> bytes:
        """Create control packet (0x12)."""
        payload = bytes([0x00, 0x41, 0x40, 0x00])
        return PacketBuilder.build_recv(seq, payload)


class PacketParser:
    """Parses protocol packets from Cosori Kettle."""
    
    MAX_FRAME_BUFFER_SIZE = 512
    MAX_PAYLOAD_SIZE = 256
    
    def __init__(self):
        self.frame_buffer = bytearray()
    
    def append_data(self, data: bytes) -> None:
        """Append received BLE notification data to frame buffer."""
        if len(self.frame_buffer) + len(data) > self.MAX_FRAME_BUFFER_SIZE:
            # Buffer overflow - clear it
            self.frame_buffer.clear()
        self.frame_buffer.extend(data)
    
    def process_frames(self) -> list:
        """Process complete frames from buffer. Returns list of parsed packets."""
        packets = []
        
        while True:
            # Find frame start (FRAME_MAGIC)
            start_idx = 0
            while start_idx < len(self.frame_buffer) and self.frame_buffer[start_idx] != FRAME_MAGIC:
                start_idx += 1
            
            # Discard bytes before frame start
            if start_idx > 0:
                self.frame_buffer = self.frame_buffer[start_idx:]
            
            # Need at least 6 bytes for header
            if len(self.frame_buffer) < 6:
                break
            
            # Parse header
            magic = self.frame_buffer[0]
            frame_type = self.frame_buffer[1]
            seq = self.frame_buffer[2]
            payload_len = self.frame_buffer[3] | (self.frame_buffer[4] << 8)
            received_checksum = self.frame_buffer[5]
            frame_len = 6 + payload_len
            
            # Validate payload length
            if payload_len > self.MAX_PAYLOAD_SIZE:
                # Invalid length - discard this byte and continue
                self.frame_buffer = self.frame_buffer[1:]
                continue
            
            # Wait for complete frame (use length field to determine if we have all of it)
            if len(self.frame_buffer) < frame_len:
                # Incomplete frame - wait for more data
                break
            
            # Validate checksum
            # Build packet with received checksum to calculate expected value
            test_packet = bytes(self.frame_buffer[:frame_len])
            # Replace checksum byte with 0x01 for calculation
            test_packet = test_packet[:5] + bytes([0x01]) + test_packet[6:]
            calculated_checksum = PacketBuilder.calculate_checksum(test_packet)
            if received_checksum != calculated_checksum:
                # Bad checksum - discard this byte and continue
                self.frame_buffer = self.frame_buffer[1:]
                continue
            
            # Extract payload
            payload = bytes(self.frame_buffer[6:6+payload_len])
            
            # Parse based on frame type
            parsed = None
            if frame_type == FRAME_TYPE_COMPACT_STATUS:
                parsed = self._parse_compact_status(seq, payload)
            elif frame_type == FRAME_TYPE_EXTENDED_STATUS:
                parsed = self._parse_extended_status(seq, payload)
            else:
                # Unknown frame type
                parsed = UnknownPacket(seq=seq, frame_type=frame_type, payload=payload)
            
            if parsed:
                packets.append(parsed)
            
            # Remove processed frame
            self.frame_buffer = self.frame_buffer[frame_len:]
        
        return packets
    
    def _parse_compact_status(self, seq: int, payload: bytes) -> Optional[StatusPacket]:
        """Parse compact status packet (0x22, 12 bytes payload)."""
        if len(payload) < 9 or payload[0] != 0x01 or payload[1] != 0x41:
            return None
        
        stage = payload[4]  # Heating stage
        mode = payload[5]   # Operating mode
        sp = payload[6]     # Setpoint temperature
        temp = payload[7]   # Current temperature
        status = payload[8]  # Heating status
        
        # Validate temperature range
        if temp < MIN_VALID_READING_F or temp > MAX_VALID_READING_F:
            return None
        
        return StatusPacket(
            seq=seq,
            temperature_f=temp,
            setpoint_f=sp,
            heating=(status != 0),
            stage=stage,
            mode=mode,
            on_base=None,  # Not available in compact packets
            packet_type="compact"
        )
    
    def _parse_extended_status(self, seq: int, payload: bytes) -> Optional[StatusPacket]:
        """Parse extended status packet (0x12, 29 bytes payload)."""
        if len(payload) < 8 or payload[0] != 0x01 or payload[1] != 0x40:
            return None
        
        stage = payload[4]
        mode = payload[5]
        sp = payload[6]
        temp = payload[7]
        
        # Validate temperature range
        if temp < MIN_VALID_READING_F or temp > MAX_VALID_READING_F:
            return None
        
        # On-base detection from payload[14] (byte 20 in full packet)
        on_base = None
        if len(payload) >= 15:
            on_base_byte = payload[14]
            on_base = (on_base_byte == 0x00)  # 0x00=on-base, 0x01=off-base
        
        return StatusPacket(
            seq=seq,
            temperature_f=temp,
            setpoint_f=sp,
            heating=(stage != 0),
            stage=stage,
            mode=mode,
            on_base=on_base,
            packet_type="extended"
        )
