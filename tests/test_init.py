"""Tests for setup, entities, and unload of the Sensofy integration."""

import aiohttp

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sensofy.const import CONF_API_KEY, CONF_HOST, DOMAIN

from .const import ICCID, SAMPLE_PAYLOAD, STATE_URL, TEST_HOST


async def _setup(hass, aioclient_mock):
    aioclient_mock.get(STATE_URL, json=SAMPLE_PAYLOAD)
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="account_1",
        data={CONF_HOST: TEST_HOST, CONF_API_KEY: "k"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_setup_creates_entities(hass, aioclient_mock):
    """Entities are created with correct unit and device_class."""
    await _setup(hass, aioclient_mock)
    reg = er.async_get(hass)

    temp_id = reg.async_get_entity_id("sensor", DOMAIN, f"sensofy_{ICCID}_temp_c")
    assert temp_id is not None
    state = hass.states.get(temp_id)
    assert state is not None
    assert state.state == "24.13"
    assert state.attributes["unit_of_measurement"] == UnitOfTemperature.CELSIUS
    assert state.attributes["device_class"] == SensorDeviceClass.TEMPERATURE


async def test_usb_binary_sensor(hass, aioclient_mock):
    """usb=1.0 becomes a binary sensor in the 'on' state."""
    await _setup(hass, aioclient_mock)
    reg = er.async_get(hass)
    usb_id = reg.async_get_entity_id("binary_sensor", DOMAIN, f"sensofy_{ICCID}_usb")
    assert usb_id is not None
    assert hass.states.get(usb_id).state == "on"


async def test_diagnostic_signal_entity(hass, aioclient_mock):
    """rssi diagnostic sensor is enabled and reports its value."""
    await _setup(hass, aioclient_mock)
    reg = er.async_get(hass)
    rssi_id = reg.async_get_entity_id("sensor", DOMAIN, f"sensofy_{ICCID}_rssi")
    assert rssi_id is not None
    assert hass.states.get(rssi_id).state == "-89"


async def test_noisy_field_disabled_by_default(hass, aioclient_mock):
    """tsl_full is registered but disabled by default (no state)."""
    await _setup(hass, aioclient_mock)
    reg = er.async_get(hass)
    full_id = reg.async_get_entity_id("sensor", DOMAIN, f"sensofy_{ICCID}_tsl_full")
    assert full_id is not None
    assert reg.async_get(full_id).disabled_by is not None
    assert hass.states.get(full_id) is None


async def test_device_groups_entities(hass, aioclient_mock):
    """All of a sensor's entities share one device, keyed by ICCID."""
    await _setup(hass, aioclient_mock)
    reg = er.async_get(hass)
    temp_id = reg.async_get_entity_id("sensor", DOMAIN, f"sensofy_{ICCID}_temp_c")
    co2_id = reg.async_get_entity_id("sensor", DOMAIN, f"sensofy_{ICCID}_co2")
    assert reg.async_get(temp_id).device_id == reg.async_get(co2_id).device_id


async def test_unload(hass, aioclient_mock):
    """The entry unloads cleanly."""
    entry = await _setup(hass, aioclient_mock)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_auth_failure_triggers_reauth(hass, aioclient_mock):
    """A 401 during update puts the entry into the reauth (error) state."""
    aioclient_mock.get(STATE_URL, status=401)
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="account_1",
        data={CONF_HOST: TEST_HOST, CONF_API_KEY: "k"},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR


async def test_connection_error_is_retried(hass, aioclient_mock):
    """A transport error puts the entry into SETUP_RETRY (not error)."""
    aioclient_mock.get(STATE_URL, exc=aiohttp.ClientError())
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="account_1",
        data={CONF_HOST: TEST_HOST, CONF_API_KEY: "k"},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY
