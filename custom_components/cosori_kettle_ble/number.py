"""Number platform for Cosori Kettle BLE."""
from __future__ import annotations

import logging

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import MAX_TEMP_F, MIN_TEMP_F
from .coordinator import CosoriKettleCoordinator

_LOGGER = logging.getLogger(__name__)

KEEP_WARM_DURATION = NumberEntityDescription(
    key="keep_warm_duration",
    name="Keep Warm Duration",
    device_class=NumberDeviceClass.DURATION,
    native_unit_of_measurement=UnitOfTime.MINUTES,
    native_min_value=0,
    native_max_value=240,
    native_step=1,
    mode=NumberMode.BOX,
)

MY_BREW_TEMPERATURE = NumberEntityDescription(
    key="my_temp",
    name="MyBrew Temperature",
    device_class=NumberDeviceClass.TEMPERATURE,
    native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
    native_min_value=MIN_TEMP_F,
    native_max_value=MAX_TEMP_F,
    native_step=1,
    mode=NumberMode.BOX,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number platform."""
    coordinator: CosoriKettleCoordinator = entry.runtime_data
    async_add_entities([
        CosoriKettleKeepWarmDuration(coordinator),
        CosoriKettleMyBrewTemperature(coordinator),
    ])


class CosoriKettleKeepWarmDuration(CoordinatorEntity[CosoriKettleCoordinator], NumberEntity):
    """Number entity for keep warm duration."""

    entity_description = KEEP_WARM_DURATION
    _attr_has_entity_name = True

    def __init__(self, coordinator: CosoriKettleCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.formatted_address}_keep_warm_duration"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> float | None:
        """Return the current keep warm duration in minutes."""
        if not self.coordinator.data:
            return None
        seconds = self.coordinator.data.get("configured_hold_time", 0)
        return round(seconds / 60)

    async def async_set_native_value(self, value: float) -> None:
        """Set the keep warm duration."""
        seconds = int(value * 60)
        await self.coordinator.async_set_hold_time(seconds)
        await self.coordinator.async_request_refresh()


class CosoriKettleMyBrewTemperature(CoordinatorEntity[CosoriKettleCoordinator], NumberEntity):
    """Number entity for MyBrew custom temperature setting."""

    entity_description = MY_BREW_TEMPERATURE
    _attr_has_entity_name = True

    def __init__(self, coordinator: CosoriKettleCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.formatted_address}_my_temp"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> float | None:
        """Return the current MyBrew temperature setting."""
        if not self.coordinator.data:
            return None
        my_temp = self.coordinator.data.get("my_temp")
        if not my_temp or my_temp < MIN_TEMP_F or my_temp > MAX_TEMP_F:
            return None
        return float(my_temp)

    async def async_set_native_value(self, value: float) -> None:
        """Set the MyBrew temperature setting."""
        temp_f = int(value)
        await self.coordinator.async_set_my_temp(temp_f)
        await self.coordinator.async_request_refresh()
