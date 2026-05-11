"""Tests for the number platform module."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from custom_components.cosori_kettle_ble.const import DOMAIN
from custom_components.cosori_kettle_ble.number import CosoriKettleKeepWarmDuration


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = AsyncMock()
    coordinator.data = {
        "configured_hold_time": 1800,  # 30 minutes in seconds
    }
    coordinator.formatted_address = "AA:BB:CC:DD:EE:FF"
    coordinator.device_info = {
        "identifiers": {(DOMAIN, "AA:BB:CC:DD:EE:FF")},
        "name": "Cosori Kettle",
        "manufacturer": "Cosori",
        "model": "Smart Kettle",
    }
    coordinator.async_set_hold_time = AsyncMock()
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


@pytest.fixture
def number_entity(mock_coordinator):
    """Create a keep warm duration entity."""
    return CosoriKettleKeepWarmDuration(mock_coordinator)


class TestCosoriKettleKeepWarmDurationInit:
    def test_unique_id(self, number_entity, mock_coordinator):
        assert number_entity.unique_id == "AA:BB:CC:DD:EE:FF_keep_warm_duration"

    def test_has_entity_name(self, number_entity):
        assert number_entity.has_entity_name is True

    def test_name(self, number_entity):
        assert number_entity.name == "Keep Warm Duration"

    def test_min_value(self, number_entity):
        assert number_entity.native_min_value == 0

    def test_max_value(self, number_entity):
        assert number_entity.native_max_value == 240

    def test_step(self, number_entity):
        assert number_entity.native_step == 1


class TestCosoriKettleKeepWarmDurationValue:
    def test_returns_minutes_from_seconds(self, number_entity):
        # 1800 seconds = 30 minutes
        assert number_entity.native_value == 30

    def test_returns_zero_when_no_hold_time(self, number_entity, mock_coordinator):
        mock_coordinator.data["configured_hold_time"] = 0
        assert number_entity.native_value == 0

    def test_returns_none_when_no_data(self, number_entity, mock_coordinator):
        mock_coordinator.data = None
        assert number_entity.native_value is None

    def test_rounds_to_nearest_minute(self, number_entity, mock_coordinator):
        mock_coordinator.data["configured_hold_time"] = 90  # 1.5 minutes → rounds to 2
        assert number_entity.native_value == 2

    def test_full_duration(self, number_entity, mock_coordinator):
        mock_coordinator.data["configured_hold_time"] = 14400  # 240 minutes
        assert number_entity.native_value == 240


class TestCosoriKettleKeepWarmDurationSetValue:
    @pytest.mark.asyncio
    async def test_set_value_converts_to_seconds(self, number_entity, mock_coordinator):
        await number_entity.async_set_native_value(30)
        mock_coordinator.async_set_hold_time.assert_called_once_with(1800)

    @pytest.mark.asyncio
    async def test_set_zero_disables(self, number_entity, mock_coordinator):
        await number_entity.async_set_native_value(0)
        mock_coordinator.async_set_hold_time.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_requests_refresh_after_set(self, number_entity, mock_coordinator):
        await number_entity.async_set_native_value(60)
        mock_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_240_minutes(self, number_entity, mock_coordinator):
        await number_entity.async_set_native_value(240)
        mock_coordinator.async_set_hold_time.assert_called_once_with(14400)
