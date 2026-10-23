"""Tests for the number platform module."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from custom_components.cosori_kettle_ble.const import DOMAIN, MAX_TEMP_F, MIN_TEMP_F
from custom_components.cosori_kettle_ble.number import (
    CosoriKettleKeepWarmDuration,
    CosoriKettleMyBrewTemperature,
    async_setup_entry,
)


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = AsyncMock()
    coordinator.data = {
        "configured_hold_time": 1800,  # 30 minutes in seconds
        "my_temp": 175,
    }
    coordinator.formatted_address = "AA:BB:CC:DD:EE:FF"
    coordinator.device_info = {
        "identifiers": {(DOMAIN, "AA:BB:CC:DD:EE:FF")},
        "name": "Cosori Kettle",
        "manufacturer": "Cosori",
        "model": "Smart Kettle",
    }
    coordinator.async_set_hold_time = AsyncMock()
    coordinator.async_set_my_temp = AsyncMock()
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


@pytest.fixture
def mybrew_number_entity(mock_coordinator):
    """Create a MyBrew temperature number entity."""
    return CosoriKettleMyBrewTemperature(mock_coordinator)


class TestCosoriKettleMyBrewTemperatureInit:
    def test_unique_id(self, mybrew_number_entity, mock_coordinator):
        assert mybrew_number_entity.unique_id == "AA:BB:CC:DD:EE:FF_my_temp"

    def test_has_entity_name(self, mybrew_number_entity):
        assert mybrew_number_entity.has_entity_name is True

    def test_name(self, mybrew_number_entity):
        assert mybrew_number_entity.name == "MyBrew Temperature"

    def test_min_value(self, mybrew_number_entity):
        assert mybrew_number_entity.native_min_value == MIN_TEMP_F

    def test_max_value(self, mybrew_number_entity):
        assert mybrew_number_entity.native_max_value == MAX_TEMP_F

    def test_step(self, mybrew_number_entity):
        assert mybrew_number_entity.native_step == 1


class TestCosoriKettleMyBrewTemperatureValue:
    def test_returns_temperature(self, mybrew_number_entity):
        assert mybrew_number_entity.native_value == 175.0

    def test_returns_none_when_no_data(self, mybrew_number_entity, mock_coordinator):
        mock_coordinator.data = None
        assert mybrew_number_entity.native_value is None

    def test_returns_none_when_zero(self, mybrew_number_entity, mock_coordinator):
        mock_coordinator.data["my_temp"] = 0
        assert mybrew_number_entity.native_value is None

    def test_returns_none_when_out_of_range(self, mybrew_number_entity, mock_coordinator):
        mock_coordinator.data["my_temp"] = 50
        assert mybrew_number_entity.native_value is None


class TestCosoriKettleMyBrewTemperatureSetValue:
    @pytest.mark.asyncio
    async def test_set_value(self, mybrew_number_entity, mock_coordinator):
        await mybrew_number_entity.async_set_native_value(185)
        mock_coordinator.async_set_my_temp.assert_called_once_with(185)
        mock_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_float_value_converts_to_int(self, mybrew_number_entity, mock_coordinator):
        await mybrew_number_entity.async_set_native_value(185.7)
        mock_coordinator.async_set_my_temp.assert_called_once_with(185)


class TestNumberSetupEntry:
    @pytest.mark.asyncio
    async def test_async_setup_entry(self, mock_coordinator):
        hass = MagicMock()
        entry = MagicMock()
        entry.runtime_data = mock_coordinator
        async_add_entities = MagicMock()

        await async_setup_entry(hass, entry, async_add_entities)

        async_add_entities.assert_called_once()
        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 2
        assert isinstance(entities[0], CosoriKettleKeepWarmDuration)
        assert isinstance(entities[1], CosoriKettleMyBrewTemperature)

