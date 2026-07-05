"""DataUpdateCoordinator for Sensofy: one coordinated poll for all sensors."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SensofyAuthError, SensofyClient, SensofyConnectionError
from .const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    FIELD_LAST_SEEN,
    SKIP_FIELDS,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class FieldValue:
    """A single measured/diagnostic value and when it was produced."""

    value: Any
    ts: int | None = None
    # Optional per-field server overrides (unit, display name)
    unit: str | None = None
    name: str | None = None


@dataclass
class SensorState:
    """Normalized state for one physical sensor (one ICCID)."""

    iccid: str
    name: str
    last_seen: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    sw_version: str | None = None
    fields: dict[str, FieldValue] = field(default_factory=dict)


# coordinator.data type: keyed by ICCID
type SensofyData = dict[str, SensorState]


class SensofyCoordinator(DataUpdateCoordinator[SensofyData]):
    """Polls GET /api/integration/state and exposes normalized sensor state."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator from a config entry."""
        self.client = SensofyClient(
            hass, entry.data[CONF_HOST], entry.data[CONF_API_KEY]
        )
        interval = entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )

    async def _async_update_data(self) -> SensofyData:
        """Fetch and normalize fleet state."""
        try:
            payload = await self.client.async_get_state()
        except SensofyAuthError as err:
            # Triggers the reauth flow so the user can re-enter the API key.
            raise ConfigEntryAuthFailed(str(err)) from err
        except SensofyConnectionError as err:
            raise UpdateFailed(str(err)) from err

        return self._parse(payload)

    @staticmethod
    def _parse(payload: dict[str, Any]) -> SensofyData:
        """Turn the raw JSON contract into a {iccid: SensorState} map."""
        result: SensofyData = {}
        for raw in payload.get("sensors", []):
            iccid = str(raw.get("iccid") or "").strip()
            if not iccid:
                continue

            telemetry = raw.get("telemetry") or {}
            attributes = raw.get("attributes") or {}
            meta = raw.get("meta") or {}

            t_ts = _as_int(telemetry.get("ts"))
            a_ts = _as_int(attributes.get("ts"))

            state = SensorState(
                iccid=iccid,
                name=str(raw.get("name") or iccid),
                latitude=_as_float(raw.get("latitude")),
                longitude=_as_float(raw.get("longitude")),
            )

            # Telemetry first (measurements), then attributes (diagnostics).
            for src_values, src_ts in ((telemetry.get("values"), t_ts),
                                       (attributes.get("values"), a_ts)):
                if not isinstance(src_values, dict):
                    continue
                for key, value in src_values.items():
                    if key in SKIP_FIELDS:
                        if key == "fw":
                            state.sw_version = str(value)
                        continue
                    if value is None:
                        continue
                    fmeta = meta.get(key) or {}
                    state.fields[key] = FieldValue(
                        value=value,
                        ts=src_ts,
                        unit=fmeta.get("unit"),
                        name=fmeta.get("name"),
                    )

            # last_seen: explicit field wins, else newest of the two timestamps.
            last_seen = _as_int(raw.get("last_seen"))
            if last_seen is None:
                candidates = [ts for ts in (t_ts, a_ts) if ts is not None]
                last_seen = max(candidates) if candidates else None
            state.last_seen = last_seen

            if last_seen is not None:
                state.fields[FIELD_LAST_SEEN] = FieldValue(
                    value=last_seen, ts=last_seen
                )

            result[iccid] = state
        return result


def _as_int(value: Any) -> int | None:
    """Best-effort int conversion."""
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    """Best-effort float conversion."""
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
