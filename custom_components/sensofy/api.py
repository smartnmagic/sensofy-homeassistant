"""Thin async client for the Sensofy integration REST API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import API_KEY_HEADER, API_STATE_PATH, REQUEST_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class SensofyApiError(Exception):
    """Base error for the Sensofy client."""


class SensofyConnectionError(SensofyApiError):
    """Raised when the server is unreachable or returns a transport error."""


class SensofyAuthError(SensofyApiError):
    """Raised when the API key is rejected (HTTP 401/403)."""


class SensofyClient:
    """Calls GET /api/integration/state with an X-API-Key header."""

    def __init__(self, hass: HomeAssistant, host: str, api_key: str) -> None:
        """Store connection parameters and the shared aiohttp session."""
        self._session = async_get_clientsession(hass)
        self._base = host.rstrip("/")
        self._api_key = api_key

    @property
    def base_url(self) -> str:
        """Return the configured base URL."""
        return self._base

    async def async_get_state(self) -> dict[str, Any]:
        """Fetch current fleet state for the account behind the API key.

        Raises:
            SensofyAuthError: the key was rejected.
            SensofyConnectionError: any transport/timeout/HTTP error.
        """
        url = f"{self._base}{API_STATE_PATH}"
        headers = {API_KEY_HEADER: self._api_key, "Accept": "application/json"}
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                resp = await self._session.get(url, headers=headers)
                if resp.status in (401, 403):
                    raise SensofyAuthError(f"API key rejected (HTTP {resp.status})")
                if resp.status != 200:
                    text = await resp.text()
                    raise SensofyConnectionError(
                        f"Unexpected status {resp.status}: {text[:200]}"
                    )
                return await resp.json()
        except SensofyApiError:
            raise
        except (TimeoutError, aiohttp.ClientError) as err:
            raise SensofyConnectionError(str(err)) from err
        except ValueError as err:  # JSON decode
            raise SensofyConnectionError(f"Invalid JSON from server: {err}") from err
