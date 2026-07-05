"""Constants and the canonical field map for the Sensofy integration.

The field map is kept 1:1 with the Sensofy web dashboard's
src/config/fieldConfig.js (labels/units), plus the real firmware keys observed
in live telemetry (temp_c, rh, tsl_*) and a few forward-looking aliases.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
)

DOMAIN = "sensofy"

# Configuration / option keys
CONF_HOST = "host"
CONF_API_KEY = "api_key"
CONF_POLL_INTERVAL = "poll_interval"
CONF_STALE_AFTER = "stale_after_minutes"

DEFAULT_HOST = "https://sensofy.io"
DEFAULT_POLL_INTERVAL = 60          # seconds
MIN_POLL_INTERVAL = 30              # seconds
DEFAULT_STALE_AFTER = 0             # minutes; 0 = never mark unavailable by age

# REST contract
API_STATE_PATH = "/api/integration/state"
API_KEY_HEADER = "X-API-Key"
REQUEST_TIMEOUT = 30                # seconds

MANUFACTURER = "Sensofy"
DEVICE_MODEL = "NB-IoT Sensor Gateway"

# Synthetic field injected by the coordinator from sensor.last_seen
FIELD_LAST_SEEN = "last_seen"

_DIAG = EntityCategory.DIAGNOSTIC
_TEMP = UnitOfTemperature.CELSIUS
_MEAS = SensorStateClass.MEASUREMENT
_TOTAL = SensorStateClass.TOTAL_INCREASING
_UGM3 = CONCENTRATION_MICROGRAMS_PER_CUBIC_METER


@dataclass(frozen=True)
class FieldDef:
    """How one telemetry/attribute key maps to a Home Assistant entity."""

    name: str
    binary: bool = False
    device_class: SensorDeviceClass | BinarySensorDeviceClass | None = None
    unit: str | None = None
    state_class: SensorStateClass | None = _MEAS
    entity_category: EntityCategory | None = None
    icon: str | None = None
    enabled_default: bool = True
    on_value: float = 1.0  # binary sensors: value treated as "on"


def _temp(name: str, default: bool = True) -> FieldDef:
    return FieldDef(name, device_class=SensorDeviceClass.TEMPERATURE,
                    unit=_TEMP, enabled_default=default)


def _rh(name: str) -> FieldDef:
    return FieldDef(name, device_class=SensorDeviceClass.HUMIDITY, unit=PERCENTAGE)


def _press(name: str) -> FieldDef:
    return FieldDef(name, device_class=SensorDeviceClass.PRESSURE,
                    unit=UnitOfPressure.HPA)


# Canonical map. Keys mirror fieldConfig.js + verified firmware keys.
FIELD_MAP: dict[str, FieldDef] = {
    # ---- Power & connectivity ----
    # NOTE: fieldConfig.js labels vbat as 'mV', but live values are volts
    # (e.g. 4.685). HA uses V so the displayed value is correct.
    "vbat": FieldDef(
        "Battery Voltage", device_class=SensorDeviceClass.VOLTAGE,
        unit=UnitOfElectricPotential.VOLT, entity_category=_DIAG,
    ),
    "usb": FieldDef(
        "USB Power", binary=True, device_class=BinarySensorDeviceClass.PLUG,
        state_class=None, entity_category=_DIAG,
    ),
    "batt_pct": FieldDef(
        "Battery Level", device_class=SensorDeviceClass.BATTERY, unit=PERCENTAGE,
        entity_category=_DIAG,
    ),
    "modem_mv": FieldDef(
        "Modem Voltage", device_class=SensorDeviceClass.VOLTAGE,
        unit=UnitOfElectricPotential.MILLIVOLT, entity_category=_DIAG,
        enabled_default=False,
    ),
    "mcu_temp": _temp("MCU Temperature", default=False),

    # ---- Environmental — generic keys (fieldConfig.js) ----
    "temperature": _temp("Temperature"),
    "humidity": _rh("Humidity"),
    "pressure": _press("Pressure"),
    "co2": FieldDef(
        "CO2", device_class=SensorDeviceClass.CO2,
        unit=CONCENTRATION_PARTS_PER_MILLION,
    ),
    "pm25": FieldDef("PM2.5", device_class=SensorDeviceClass.PM25, unit=_UGM3),
    "pm10": FieldDef("PM10", device_class=SensorDeviceClass.PM10, unit=_UGM3),
    "lux": FieldDef(
        "Illuminance", device_class=SensorDeviceClass.ILLUMINANCE, unit="lx",
    ),
    "voc": FieldDef("VOC Index", icon="mdi:air-filter"),

    # ---- Sensor-specific aliases (fieldConfig.js) ----
    "aht_t": _temp("AHT Temp"),
    "aht_rh": _rh("AHT Humidity"),
    "bme_t": _temp("BME Temp"),
    "bme_rh": _rh("BME Humidity"),
    "bme_p": _press("BME Pressure"),
    "sht_t": _temp("SHT Temp"),
    "sht_rh": _rh("SHT Humidity"),

    # ---- Verified live firmware keys (NOT yet in fieldConfig.js) ----
    "temp_c": _temp("Temperature"),
    "rh": _rh("Humidity"),
    "tsl_lux": FieldDef(
        "Illuminance", device_class=SensorDeviceClass.ILLUMINANCE, unit="lx",
    ),
    "tsl_full": FieldDef(
        "Light (full spectrum)", icon="mdi:brightness-5",
        entity_category=_DIAG, enabled_default=False,
    ),
    "tsl_ir": FieldDef(
        "Light (infrared)", icon="mdi:brightness-5",
        entity_category=_DIAG, enabled_default=False,
    ),

    # ---- Forward-looking aliases (harmless if unused) ----
    "illuminance": FieldDef(
        "Illuminance", device_class=SensorDeviceClass.ILLUMINANCE, unit="lx",
    ),
    "pm1": FieldDef("PM1", device_class=SensorDeviceClass.PM1, unit=_UGM3),
    "pm2_5": FieldDef("PM2.5", device_class=SensorDeviceClass.PM25, unit=_UGM3),
    "pm4": FieldDef("PM4", unit=_UGM3, icon="mdi:air-filter"),
    "voc_index": FieldDef("VOC Index", icon="mdi:air-filter"),
    "nox_index": FieldDef("NOx Index", icon="mdi:air-filter"),
    "iaq": FieldDef("IAQ", icon="mdi:air-filter"),
    "current": FieldDef(
        "Current", device_class=SensorDeviceClass.CURRENT,
        unit=UnitOfElectricCurrent.AMPERE,
    ),
    "voltage": FieldDef(
        "Voltage", device_class=SensorDeviceClass.VOLTAGE,
        unit=UnitOfElectricPotential.VOLT,
    ),
    "power": FieldDef(
        "Power", device_class=SensorDeviceClass.POWER, unit=UnitOfPower.WATT,
    ),

    # ---- Signal / radio (fieldConfig.js + backend attributes) ----
    "rssi": FieldDef(
        "RSSI", device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        unit=SIGNAL_STRENGTH_DECIBELS_MILLIWATT, entity_category=_DIAG,
    ),
    "rsrp": FieldDef(
        "RSRP", device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        unit=SIGNAL_STRENGTH_DECIBELS_MILLIWATT, entity_category=_DIAG,
        enabled_default=False,
    ),
    "rsrq": FieldDef("RSRQ", unit="dB", entity_category=_DIAG, enabled_default=False),
    "snr": FieldDef("SNR", unit="dB", entity_category=_DIAG, enabled_default=False),
    "earfcn": FieldDef("EARFCN", state_class=None, entity_category=_DIAG, enabled_default=False),
    "pci": FieldDef("PCI", state_class=None, entity_category=_DIAG, enabled_default=False),
    "band": FieldDef("Band", state_class=None, entity_category=_DIAG, enabled_default=False),
    "ecl": FieldDef("Coverage Level (ECL)", state_class=None, entity_category=_DIAG, enabled_default=False),
    "operator": FieldDef("Operator", state_class=None, entity_category=_DIAG),
    "cell_id": FieldDef("Cell ID", state_class=None, entity_category=_DIAG, enabled_default=False),
    "cell": FieldDef("Cell ID", state_class=None, entity_category=_DIAG, enabled_default=False),
    "tac": FieldDef("TAC", state_class=None, entity_category=_DIAG, enabled_default=False),

    # ---- Firmware diagnostics (fieldConfig.js) ----
    "uptime_s": FieldDef(
        "Uptime", device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS, state_class=_TOTAL,
        entity_category=_DIAG, enabled_default=False,
    ),
    "cycles": FieldDef("Cycles", state_class=_TOTAL, entity_category=_DIAG, enabled_default=False),
    "flush_ok": FieldDef("Flush OK", state_class=_TOTAL, entity_category=_DIAG, enabled_default=False),
    "flush_fail": FieldDef("Flush Fail", state_class=_TOTAL, entity_category=_DIAG, enabled_default=False),
    "net_bo": FieldDef("Net Backoff", entity_category=_DIAG, enabled_default=False),
    "srv_bo": FieldDef("Srv Backoff", entity_category=_DIAG, enabled_default=False),
    "buf_count": FieldDef("Buffer Count", entity_category=_DIAG, enabled_default=False),
    "last_err": FieldDef("Last Error", state_class=None, entity_category=_DIAG, enabled_default=False),
    "modem_state": FieldDef("Modem State", state_class=None, entity_category=_DIAG, enabled_default=False),

    # ---- Synthetic ----
    FIELD_LAST_SEEN: FieldDef(
        "Last Seen", device_class=SensorDeviceClass.TIMESTAMP, state_class=None,
        entity_category=_DIAG,
    ),
}

# Keys that should never become entities (identity handled elsewhere)
SKIP_FIELDS = frozenset({"iccid", "imei", "fw"})


def field_def(key: str) -> FieldDef:
    """Return the FieldDef for a key, or a safe generic fallback."""
    if key in FIELD_MAP:
        return FIELD_MAP[key]
    pretty = key.replace("_", " ").strip().title()
    # Unknown fields may be strings; no measurement state_class so HA never
    # rejects a non-numeric state.
    return FieldDef(name=pretty or key, state_class=None)
