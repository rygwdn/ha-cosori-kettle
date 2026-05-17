"""Tests for the diagnostics module."""
import pytest
from unittest.mock import MagicMock, AsyncMock

from custom_components.cosori_kettle_ble.diagnostics import async_get_config_entry_diagnostics
from custom_components.cosori_kettle_ble.const import CONF_REGISTRATION_KEY


@pytest.fixture
def mock_coordinator():
    coordinator = MagicMock()
    coordinator._ble_device.address = "AA:BB:CC:DD:EE:FF"
    coordinator.protocol_version = 1
    coordinator.hardware_version = "1.0"
    coordinator.software_version = "2.0"
    coordinator.model_number = "GK172"
    coordinator.manufacturer = "Cosori"
    coordinator._client.is_connected = True
    coordinator.data = {"temperature": 72, "setpoint": 212, "heating": True}
    return coordinator


@pytest.fixture
def mock_entry(mock_coordinator):
    entry = MagicMock()
    entry.data = {
        "device_id": "AA:BB:CC:DD:EE:FF",
        CONF_REGISTRATION_KEY: "deadbeef" * 4,
    }
    entry.runtime_data = mock_coordinator
    return entry


@pytest.mark.asyncio
async def test_diagnostics_redacts_registration_key(mock_entry):
    hass = MagicMock()
    result = await async_get_config_entry_diagnostics(hass, mock_entry)
    assert CONF_REGISTRATION_KEY not in result["entry"] or result["entry"][CONF_REGISTRATION_KEY] == "**REDACTED**"


@pytest.mark.asyncio
async def test_diagnostics_includes_device_info(mock_entry):
    hass = MagicMock()
    result = await async_get_config_entry_diagnostics(hass, mock_entry)
    assert result["device"]["address"] == "AA:BB:CC:DD:EE:FF"
    assert result["device"]["protocol_version"] == 1
    assert result["device"]["connected"] is True


@pytest.mark.asyncio
async def test_diagnostics_includes_state(mock_entry):
    hass = MagicMock()
    result = await async_get_config_entry_diagnostics(hass, mock_entry)
    assert result["state"]["temperature"] == 72
    assert result["state"]["heating"] is True


@pytest.mark.asyncio
async def test_diagnostics_disconnected_client(mock_entry, mock_coordinator):
    mock_coordinator._client = None
    hass = MagicMock()
    result = await async_get_config_entry_diagnostics(hass, mock_entry)
    assert result["device"]["connected"] is False
