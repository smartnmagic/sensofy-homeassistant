"""Sensor platform for Sensofy with dynamic entity discovery."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SensofyConfigEntry
from .const import field_def
from .coordinator import SensofyCoordinator
from .entity import SensofyEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SensofyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors and keep watching for newly reported fields."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _discover() -> None:
        new: list[SensofySensor] = []
        for iccid, sensor in coordinator.data.items():
            for key in sensor.fields:
                if field_def(key).binary:
                    continue
                uid = f"{iccid}_{key}"
                if uid in known:
                    continue
                known.add(uid)
                new.append(SensofySensor(coordinator, iccid, key))
        if new:
            async_add_entities(new)

    _discover()
    entry.async_on_unload(coordinator.async_add_listener(_discover))


class SensofySensor(SensofyEntity, SensorEntity):
    """A single numeric/text field of a Sensofy sensor."""

    def __init__(self, coordinator: SensofyCoordinator, iccid: str, key: str) -> None:
        """Apply static entity description from the field map."""
        super().__init__(coordinator, iccid, key)
        fd = field_def(key)
        self._attr_translation_key = key if key in _TRANSLATED else None
        self._attr_name = fd.name
        self._attr_device_class = fd.device_class
        self._attr_native_unit_of_measurement = fd.unit
        self._attr_state_class = fd.state_class
        self._attr_entity_category = fd.entity_category
        self._attr_icon = fd.icon
        self._attr_entity_registry_enabled_default = fd.enabled_default

        # Server-provided overrides (kept in sync with the dashboard).
        sensor = self._sensor
        if sensor and (fv := sensor.fields.get(key)):
            if fv.unit:
                self._attr_native_unit_of_measurement = fv.unit
            if fv.name:
                self._attr_name = fv.name

    @property
    def native_value(self) -> Any:
        """Return the current value, converting timestamps to datetime."""
        sensor = self._sensor
        if sensor is None:
            return None
        fv = sensor.fields.get(self._key)
        if fv is None:
            return None
        if self._attr_device_class == SensorDeviceClass.TIMESTAMP:
            try:
                return datetime.fromtimestamp(int(fv.value), tz=timezone.utc)
            except (TypeError, ValueError, OSError):
                return None
        return fv.value


# Reserved for future translated field names; empty means use _attr_name.
_TRANSLATED: frozenset[str] = frozenset()
