"""Pytest fixtures for Cosori Kettle BLE tests."""
import sys
from pathlib import Path

import pytest

# Add custom_components to Python path
custom_components_path = Path(__file__).parent.parent.parent / "custom_components"
sys.path.insert(0, str(custom_components_path))


@pytest.fixture
def hex_to_bytes():
    """Convert hex string to bytes."""
    def _hex_to_bytes(hex_str: str) -> bytes:
        # Remove spaces and colons
        hex_str = hex_str.replace(" ", "").replace(":", "")
        return bytes.fromhex(hex_str)
    return _hex_to_bytes


@pytest.fixture
def bytes_to_hex():
    """Convert bytes to hex string."""
    def _bytes_to_hex(data: bytes) -> str:
        return data.hex().upper()
    return _bytes_to_hex


@pytest.fixture
def registration_key():
    """Sample registration key for testing."""
    return bytes.fromhex("9903e01a3c3baa8f6c71cbb5167e7d5f")
