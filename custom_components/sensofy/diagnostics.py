"""Diagnostics support for Sensofy."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import SensofyConfigEntry
from .const import CONF_API_KEY

TO_REDACT = {CONF_API_KEY, "iccid", "serial_number", "latitude", "longitude"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SensofyConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    sensors = {
        iccid: asdict(state) for iccid, state in coordinator.data.items()
    }
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "last_update_success": coordinator.last_update_success,
        "sensor_count": len(sensors),
        "sensors": async_redact_data(sensors, TO_REDACT),
    }
