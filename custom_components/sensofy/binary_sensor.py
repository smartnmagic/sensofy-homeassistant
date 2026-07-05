"""Binary sensor platform for Sensofy (e.g. USB power presence)."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
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
    """Set up binary sensors and watch for new ones on each poll."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _discover() -> None:
        new: list[SensofyBinarySensor] = []
        for iccid, sensor in coordinator.data.items():
            for key in sensor.fields:
                if not field_def(key).binary:
                    continue
                uid = f"{iccid}_{key}"
                if uid in known:
                    continue
                known.add(uid)
                new.append(SensofyBinarySensor(coordinator, iccid, key))
        if new:
            async_add_entities(new)

    _discover()
    entry.async_on_unload(coordinator.async_add_listener(_discover))


class SensofyBinarySensor(SensofyEntity, BinarySensorEntity):
    """A boolean field of a Sensofy sensor (numeric value compared to on_value)."""

    def __init__(self, coordinator: SensofyCoordinator, iccid: str, key: str) -> None:
        """Apply static entity description from the field map."""
        super().__init__(coordinator, iccid, key)
        fd = field_def(key)
        self._attr_name = fd.name
        self._attr_device_class = fd.device_class
        self._attr_entity_category = fd.entity_category
        self._attr_icon = fd.icon
        self._attr_entity_registry_enabled_default = fd.enabled_default
        self._on_value = fd.on_value

    @property
    def is_on(self) -> bool | None:
        """Return True when the field's value equals the configured on_value."""
        sensor = self._sensor
        if sensor is None:
            return None
        fv = sensor.fields.get(self._key)
        if fv is None or fv.value is None:
            return None
        try:
            return float(fv.value) == self._on_value
        except (TypeError, ValueError):
            return bool(fv.value)
