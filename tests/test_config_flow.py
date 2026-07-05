"""Tests for the Sensofy config and options flow."""

from unittest.mock import patch

import aiohttp

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sensofy.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_POLL_INTERVAL,
    CONF_STALE_AFTER,
    DOMAIN,
)

from .const import SAMPLE_PAYLOAD, STATE_URL, TEST_HOST


async def test_user_flow_success(hass, aioclient_mock):
    """A valid host + key creates an entry titled by the account email."""
    aioclient_mock.get(STATE_URL, json=SAMPLE_PAYLOAD)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch("custom_components.sensofy.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: TEST_HOST, CONF_API_KEY: "sfy_abc"},
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "user@example.com"
    assert result["data"] == {CONF_HOST: TEST_HOST, CONF_API_KEY: "sfy_abc"}
    assert result["result"].unique_id == "account_1"


async def test_user_flow_invalid_auth(hass, aioclient_mock):
    """A 401 from the server surfaces invalid_auth."""
    aioclient_mock.get(STATE_URL, status=401)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: TEST_HOST, CONF_API_KEY: "bad"},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_cannot_connect(hass, aioclient_mock):
    """A transport error surfaces cannot_connect."""
    aioclient_mock.get(STATE_URL, exc=aiohttp.ClientError())

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: TEST_HOST, CONF_API_KEY: "k"},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_duplicate_account_aborts(hass, aioclient_mock):
    """Adding the same account twice is rejected."""
    aioclient_mock.get(STATE_URL, json=SAMPLE_PAYLOAD)
    MockConfigEntry(
        domain=DOMAIN,
        unique_id="account_1",
        data={CONF_HOST: TEST_HOST, CONF_API_KEY: "k"},
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: TEST_HOST, CONF_API_KEY: "k2"},
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_flow(hass, aioclient_mock):
    """Reauth updates the stored API key."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="account_1",
        data={CONF_HOST: TEST_HOST, CONF_API_KEY: "old"},
    )
    entry.add_to_hass(hass)
    aioclient_mock.get(STATE_URL, json=SAMPLE_PAYLOAD)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_REAUTH, "entry_id": entry.entry_id},
        data=entry.data,
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with patch("custom_components.sensofy.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_API_KEY: "sfy_new"}
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_API_KEY] == "sfy_new"


async def test_options_flow(hass, aioclient_mock):
    """Options flow stores poll interval and stale window."""
    aioclient_mock.get(STATE_URL, json=SAMPLE_PAYLOAD)
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="account_1",
        data={CONF_HOST: TEST_HOST, CONF_API_KEY: "k"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_POLL_INTERVAL: 120, CONF_STALE_AFTER: 30},
    )
    await hass.async_block_till_done()
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options == {CONF_POLL_INTERVAL: 120, CONF_STALE_AFTER: 30}
