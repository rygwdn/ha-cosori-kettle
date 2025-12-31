"""Tests for registration/hello commands.

These tests validate the registration and hello command generation
to ensure they match the protocol specification.
"""

import pytest
from cosori_kettle.protocol import PacketBuilder, Command


class TestRegistrationCommands:
    """Test registration and hello command generation."""
    
    def test_register_command_structure(self):
        """Test that register command uses 0x80 command ID."""
        # Registration key: 32-byte ASCII hex string (16 bytes binary = 32 hex chars)
        # Python interface expects 32-byte ASCII hex string
        reg_key = b"9903e01a3c3baa8f6c71cbb5167e7d5f"  # 32 bytes ASCII
        
        packet = PacketBuilder.make_register(seq=0x00, registration_key=reg_key)
        
        # Verify packet structure: A5 22 00 24 00 [cs] 01 80 D1 00 [32-byte hex key]
        assert packet[0] == 0xA5  # magic
        assert packet[1] == 0x22  # message type
        assert packet[2] == 0x00  # seq
        assert packet[3] == 0x24  # payload length low (36 = 0x24)
        assert packet[4] == 0x00  # payload length high
        
        # Verify payload header
        payload_start = 6  # After 6-byte envelope
        assert packet[payload_start] == 0x01  # protocol version V1
        assert packet[payload_start + 1] == 0x80  # CMD_REGISTER
        assert packet[payload_start + 2] == 0xD1  # CMD_TYPE_D1
        assert packet[payload_start + 3] == 0x00  # padding
        
        # Verify hex-encoded key (32 bytes ASCII)
        hex_key_start = payload_start + 4
        expected_hex = "9903e01a3c3baa8f6c71cbb5167e7d5f"
        for i, char in enumerate(expected_hex):
            assert packet[hex_key_start + i] == ord(char)
    
    def test_hello_command_structure(self):
        """Test that hello command uses 0x81 command ID."""
        # Same registration key (32-byte ASCII hex string)
        reg_key = b"9903e01a3c3baa8f6c71cbb5167e7d5f"  # 32 bytes ASCII
        
        packet = PacketBuilder.make_hello(seq=0x00, registration_key=reg_key)
        
        # Verify packet structure: A5 22 00 24 00 [cs] 01 81 D1 00 [32-byte hex key]
        assert packet[0] == 0xA5  # magic
        assert packet[1] == 0x22  # message type
        assert packet[2] == 0x00  # seq
        assert packet[3] == 0x24  # payload length low (36 = 0x24)
        assert packet[4] == 0x00  # payload length high
        
        # Verify payload header
        payload_start = 6
        assert packet[payload_start] == 0x01  # protocol version V1
        assert packet[payload_start + 1] == 0x81  # CMD_HELLO (different from register!)
        assert packet[payload_start + 2] == 0xD1  # CMD_TYPE_D1
        assert packet[payload_start + 3] == 0x00  # padding
        
        # Verify hex-encoded key (should be same as register)
        hex_key_start = payload_start + 4
        expected_hex = "9903e01a3c3baa8f6c71cbb5167e7d5f"
        for i, char in enumerate(expected_hex):
            assert packet[hex_key_start + i] == ord(char)
    
    def test_register_vs_hello_difference(self):
        """Test that register (0x80) and hello (0x81) differ only in command ID."""
        reg_key = b"123456789abcdef01122334455667788"  # 32 bytes ASCII
        
        register_packet = PacketBuilder.make_register(seq=0x10, registration_key=reg_key)
        hello_packet = PacketBuilder.make_hello(seq=0x10, registration_key=reg_key)
        
        # Both should have same length
        assert len(register_packet) == len(hello_packet)
        assert len(register_packet) == 42  # 6 envelope + 36 payload
        
        # Envelope should be identical (same seq, same payload length)
        assert register_packet[:6] == hello_packet[:6]
        
        # Payload should differ only in command ID byte
        payload_start = 6
        assert register_packet[payload_start] == hello_packet[payload_start]  # version
        assert register_packet[payload_start + 1] == 0x80  # REGISTER
        assert hello_packet[payload_start + 1] == 0x81     # HELLO
        assert register_packet[payload_start + 2] == hello_packet[payload_start + 2]  # type
        assert register_packet[payload_start + 3] == hello_packet[payload_start + 3]  # padding
        
        # Hex-encoded key should be identical
        hex_key_start = payload_start + 4
        assert register_packet[hex_key_start:] == hello_packet[hex_key_start:]
    
    def test_hex_encoding(self):
        """Test that registration key is correctly used as-is (already hex-encoded)."""
        # Python interface expects 32-byte ASCII hex string (already encoded)
        # Test with key that exercises all hex digits
        reg_key = b"00010f10fffefeabcd123456789abcdef"  # 32 bytes ASCII hex
        
        packet = PacketBuilder.make_register(seq=0x00, registration_key=reg_key)
        
        # Extract hex-encoded key from packet
        hex_key_start = 6 + 4  # envelope + payload header
        hex_encoded = packet[hex_key_start:hex_key_start + 32]
        
        # Should be identical to input (already hex-encoded)
        assert hex_encoded == reg_key
        
        # Verify it's lowercase hex
        hex_string = hex_encoded.decode('ascii')
        assert hex_string.islower()
        assert all(c in '0123456789abcdef' for c in hex_string)
    
    def test_different_registration_keys(self):
        """Test that different keys produce different packets."""
        key1 = b"9903e01a3c3baa8f6c71cbb5167e7d5f"  # 32 bytes ASCII
        key2 = b"123456789abcdef01122334455667788"  # 32 bytes ASCII
        
        packet1 = PacketBuilder.make_register(seq=0x00, registration_key=key1)
        packet2 = PacketBuilder.make_register(seq=0x00, registration_key=key2)
        
        # Envelope should be same (same seq)
        assert packet1[:6] == packet2[:6]
        
        # Payload header should be same
        assert packet1[6:10] == packet2[6:10]
        
        # But hex-encoded keys should differ
        assert packet1[10:] != packet2[10:]
    
    def test_payload_length(self):
        """Test that payload length is always 36 bytes (4 header + 32 hex key)."""
        reg_key = b"9903e01a3c3baa8f6c71cbb5167e7d5f"  # 32 bytes ASCII
        
        register_packet = PacketBuilder.make_register(seq=0x00, registration_key=reg_key)
        hello_packet = PacketBuilder.make_hello(seq=0x00, registration_key=reg_key)
        
        # Payload length in envelope (bytes 3-4, little-endian)
        payload_len = register_packet[3] | (register_packet[4] << 8)
        assert payload_len == 36
        
        payload_len = hello_packet[3] | (hello_packet[4] << 8)
        assert payload_len == 36
        
        # Actual payload size (excluding envelope)
        assert len(register_packet) - 6 == 36
        assert len(hello_packet) - 6 == 36
    
    def test_sequence_number_preserved(self):
        """Test that sequence number is correctly set in envelope."""
        reg_key = b"9903e01a3c3baa8f6c71cbb5167e7d5f"  # 32 bytes ASCII
        
        for seq in [0x00, 0x10, 0xFF, 0x42]:
            register_packet = PacketBuilder.make_register(seq=seq, registration_key=reg_key)
            hello_packet = PacketBuilder.make_hello(seq=seq, registration_key=reg_key)
            
            assert register_packet[2] == seq
            assert hello_packet[2] == seq


class TestRegistrationProtocol:
    """Test registration protocol compliance."""
    
    def test_register_command_id(self):
        """Verify register command uses 0x80 as specified in protocol."""
        reg_key = b"9903e01a3c3baa8f6c71cbb5167e7d5f"  # 32 bytes ASCII
        packet = PacketBuilder.make_register(seq=0x00, registration_key=reg_key)
        
        # Command ID should be 0x80 (register/pairing)
        assert packet[6 + 1] == 0x80
    
    def test_hello_command_id(self):
        """Verify hello command uses 0x81 as specified in protocol."""
        reg_key = b"9903e01a3c3baa8f6c71cbb5167e7d5f"  # 32 bytes ASCII
        packet = PacketBuilder.make_hello(seq=0x00, registration_key=reg_key)
        
        # Command ID should be 0x81 (hello/reconnect)
        assert packet[6 + 1] == 0x81
    
    def test_command_type_d1(self):
        """Verify both commands use 0xD1 command type."""
        reg_key = b"9903e01a3c3baa8f6c71cbb5167e7d5f"  # 32 bytes ASCII
        
        register_packet = PacketBuilder.make_register(seq=0x00, registration_key=reg_key)
        hello_packet = PacketBuilder.make_hello(seq=0x00, registration_key=reg_key)
        
        # Both should use 0xD1 command type
        assert register_packet[6 + 2] == 0xD1
        assert hello_packet[6 + 2] == 0xD1
    
    def test_protocol_version_v1(self):
        """Verify commands use protocol version 1 (0x01)."""
        reg_key = b"9903e01a3c3baa8f6c71cbb5167e7d5f"  # 32 bytes ASCII
        
        register_packet = PacketBuilder.make_register(seq=0x00, registration_key=reg_key)
        hello_packet = PacketBuilder.make_hello(seq=0x00, registration_key=reg_key)
        
        # Both should use V1 protocol (0x01)
        assert register_packet[6] == 0x01
        assert hello_packet[6] == 0x01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
