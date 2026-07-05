"""Test constants and a realistic sample payload."""

TEST_HOST = "https://test.sensofy"
STATE_URL = f"{TEST_HOST}/api/integration/state"
ICCID = "8988228066621653742"

# Mirrors a real Sensofy /api/integration/state response (SCD4x + AHT10 + TSL2591),
# plus cell attributes. Timestamps are epoch seconds (the backend converts ms→s).
SAMPLE_PAYLOAD = {
    "server_time": 1781328500,
    "account": {"id": 1, "email": "user@example.com"},
    "sensors": [
        {
            "iccid": ICCID,
            "name": "Outdoor Combo",
            "last_seen": 1781328421,
            "latitude": 50.08,
            "longitude": 8.24,
            "telemetry": {
                "ts": 1781328421,
                "values": {
                    "vbat": 4.685,
                    "usb": 1.0,
                    "mcu_temp": 29.85,
                    "modem_mv": 3322,
                    "co2": 739.0,
                    "temp_c": 24.13,
                    "rh": 53.78,
                    "aht_t": 23.73,
                    "aht_rh": 56.01,
                    "tsl_lux": 6.698,
                    "tsl_full": 471.0,
                    "tsl_ir": 216.0,
                    "fw": "1.4.2",
                },
            },
            "attributes": {
                "ts": 1781328421,
                "values": {
                    "rssi": -89,
                    "operator": "26201",
                    "band": 8,
                    "rsrp": -95.0,
                },
            },
        }
    ],
}
