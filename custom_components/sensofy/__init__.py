"""The Sensofy integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import SensofyCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

# Typed config entry: runtime_data holds the live coordinator.
type SensofyConfigEntry = ConfigEntry[SensofyCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: SensofyConfigEntry) -> bool:
    """Set up Sensofy from a config entry."""
    coordinator = SensofyCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SensofyConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload(hass: HomeAssistant, entry: SensofyConfigEntry) -> None:
    """Reload when options (poll interval, stale window) change."""
    await hass.config_entries.async_reload(entry.entry_id)
