"""Diagnostics support for Cosori Kettle BLE."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_REGISTRATION_KEY
from .coordinator import CosoriKettleCoordinator

_TO_REDACT = {CONF_REGISTRATION_KEY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: CosoriKettleCoordinator = entry.runtime_data

    return {
        "entry": async_redact_data(dict(entry.data), _TO_REDACT),
        "device": {
            "address": coordinator._ble_device.address,
            "protocol_version": coordinator.protocol_version,
            "hardware_version": coordinator.hardware_version,
            "software_version": coordinator.software_version,
            "model_number": coordinator.model_number,
            "manufacturer": coordinator.manufacturer,
            "connected": coordinator._client.is_connected if coordinator._client else False,
        },
        "state": coordinator.data,
    }
