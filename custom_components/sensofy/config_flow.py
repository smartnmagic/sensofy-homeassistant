"""Config and options flow for the Sensofy integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback

from .api import SensofyAuthError, SensofyClient, SensofyConnectionError
from .const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_POLL_INTERVAL,
    CONF_STALE_AFTER,
    DEFAULT_HOST,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_STALE_AFTER,
    DOMAIN,
    MIN_POLL_INTERVAL,
)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_API_KEY): str,
    }
)


async def _validate(hass, host: str, api_key: str) -> dict[str, Any]:
    """Validate credentials by calling the state endpoint once.

    Returns the parsed payload on success; raises SensofyAuthError or
    SensofyConnectionError on failure.
    """
    client = SensofyClient(hass, host, api_key)
    return await client.async_get_state()


class SensofyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup and reauthentication."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect host + API key from the user."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].rstrip("/")
            api_key = user_input[CONF_API_KEY].strip()
            try:
                payload = await _validate(self.hass, host, api_key)
            except SensofyAuthError:
                errors["base"] = "invalid_auth"
            except SensofyConnectionError:
                errors["base"] = "cannot_connect"
            else:
                unique_id, title = _identity(payload, host)
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=title,
                    data={CONF_HOST: host, CONF_API_KEY: api_key},
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauth when the stored API key stops working."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a fresh API key, keeping the existing host."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            host = entry.data[CONF_HOST]
            api_key = user_input[CONF_API_KEY].strip()
            try:
                await _validate(self.hass, host, api_key)
            except SensofyAuthError:
                errors["base"] = "invalid_auth"
            except SensofyConnectionError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    entry, data={**entry.data, CONF_API_KEY: api_key}
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return SensofyOptionsFlow()


class SensofyOptionsFlow(OptionsFlow):
    """Poll interval and stale-after options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage integration options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        opts = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_POLL_INTERVAL,
                    default=opts.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Clamp(min=MIN_POLL_INTERVAL)),
                vol.Required(
                    CONF_STALE_AFTER,
                    default=opts.get(CONF_STALE_AFTER, DEFAULT_STALE_AFTER),
                ): vol.All(vol.Coerce(int), vol.Clamp(min=0)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)


def _identity(payload: dict[str, Any], host: str) -> tuple[str, str]:
    """Derive a stable unique_id and a human title from the payload."""
    account = payload.get("account") or {}
    acc_id = account.get("id")
    email = account.get("email")
    if acc_id is not None:
        return f"account_{acc_id}", (email or f"Sensofy account {acc_id}")
    if email:
        return f"account_{email}", email
    # Fallback: host-scoped. Prevents the same server being added twice.
    return host, f"Sensofy ({host})"
