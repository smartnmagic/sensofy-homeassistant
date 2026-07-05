"""Base entity for Sensofy: device registry wiring + availability."""

from __future__ import annotations

from time import time

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_STALE_AFTER,
    DEFAULT_STALE_AFTER,
    DEVICE_MODEL,
    DOMAIN,
    MANUFACTURER,
)
from .coordinator import SensofyCoordinator, SensorState


class SensofyEntity(CoordinatorEntity[SensofyCoordinator]):
    """Common base for all Sensofy entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SensofyCoordinator, iccid: str, key: str) -> None:
        """Bind the entity to a sensor (ICCID) and a field key."""
        super().__init__(coordinator)
        self._iccid = iccid
        self._key = key
        self._attr_unique_id = f"{DOMAIN}_{iccid}_{key}"

    @property
    def _sensor(self) -> SensorState | None:
        """Return the current SensorState for this ICCID, if present."""
        return self.coordinator.data.get(self._iccid)

    @property
    def device_info(self) -> DeviceInfo:
        """Group all of a sensor's entities under one HA device."""
        sensor = self._sensor
        name = sensor.name if sensor else self._iccid
        sw = sensor.sw_version if sensor else None
        info = DeviceInfo(
            identifiers={(DOMAIN, self._iccid)},
            name=name,
            manufacturer=MANUFACTURER,
            model=DEVICE_MODEL,
            serial_number=self._iccid,
        )
        if sw:
            info["sw_version"] = sw
        return info

    @property
    def available(self) -> bool:
        """Available when the last poll succeeded and the field has a value.

        If the user sets a positive ``stale_after_minutes`` option, the entity
        also goes unavailable once the sensor's last_seen is older than that.
        Default (0) never marks stale by age — battery devices sleep for hours.
        """
        if not self.coordinator.last_update_success:
            return False
        sensor = self._sensor
        if sensor is None or self._key not in sensor.fields:
            return False

        stale_after = self.coordinator.config_entry.options.get(
            CONF_STALE_AFTER, DEFAULT_STALE_AFTER
        )
        if stale_after and sensor.last_seen:
            if time() - sensor.last_seen > stale_after * 60:
                return False
        return True
