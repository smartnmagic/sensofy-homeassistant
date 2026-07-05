"""Tests for SensofyCoordinator payload parsing (pure, no HA runtime needed)."""

from custom_components.sensofy.coordinator import SensofyCoordinator

from .const import ICCID, SAMPLE_PAYLOAD


def test_parse_basic_fields():
    """Real payload parses into a sensor with all expected fields."""
    data = SensofyCoordinator._parse(SAMPLE_PAYLOAD)
    assert set(data) == {ICCID}

    s = data[ICCID]
    assert s.name == "Outdoor Combo"
    assert s.last_seen == 1781328421
    assert s.latitude == 50.08
    assert s.longitude == 8.24

    # fw is consumed as firmware version, not turned into a field.
    assert s.sw_version == "1.4.2"
    assert "fw" not in s.fields

    # Telemetry measurements present with correct values.
    assert s.fields["temp_c"].value == 24.13
    assert s.fields["rh"].value == 53.78
    assert s.fields["co2"].value == 739.0
    assert s.fields["usb"].value == 1.0
    assert s.fields["tsl_lux"].value == 6.698

    # Attributes (diagnostics) merged in.
    assert s.fields["rssi"].value == -89
    assert s.fields["operator"].value == "26201"

    # Synthetic last_seen field injected.
    assert "last_seen" in s.fields
    assert s.fields["last_seen"].value == 1781328421

    # Identity fields never become entities.
    assert "iccid" not in s.fields
    assert "imei" not in s.fields


def test_parse_field_timestamps():
    """Telemetry and attribute fields carry their source timestamp."""
    s = SensofyCoordinator._parse(SAMPLE_PAYLOAD)[ICCID]
    assert s.fields["temp_c"].ts == 1781328421
    assert s.fields["rssi"].ts == 1781328421


def test_parse_skips_sensor_without_iccid():
    """A sensor entry with no ICCID is ignored."""
    payload = {"sensors": [{"name": "ghost"}]}
    assert SensofyCoordinator._parse(payload) == {}


def test_parse_last_seen_falls_back_to_telemetry_ts():
    """Without explicit last_seen, the newest telemetry/attr ts is used."""
    payload = {
        "sensors": [
            {"iccid": "X", "telemetry": {"ts": 100, "values": {"temp_c": 1.0}}}
        ]
    }
    s = SensofyCoordinator._parse(payload)["X"]
    assert s.last_seen == 100
    assert s.fields["last_seen"].value == 100


def test_parse_sensor_with_only_attributes():
    """A sensor that has only attributes still parses cleanly."""
    payload = {
        "sensors": [
            {
                "iccid": "Y",
                "last_seen": 50,
                "attributes": {"ts": 50, "values": {"rssi": -77}},
            }
        ]
    }
    s = SensofyCoordinator._parse(payload)["Y"]
    assert s.fields["rssi"].value == -77
    assert "last_seen" in s.fields


def test_parse_server_meta_overrides_unit_and_name():
    """Optional per-field server meta is captured for entity overrides."""
    payload = {
        "sensors": [
            {
                "iccid": "Z",
                "telemetry": {"ts": 1, "values": {"temp_c": 9.9}},
                "meta": {"temp_c": {"unit": "K", "name": "Custom"}},
            }
        ]
    }
    fv = SensofyCoordinator._parse(payload)["Z"].fields["temp_c"]
    assert fv.unit == "K"
    assert fv.name == "Custom"
