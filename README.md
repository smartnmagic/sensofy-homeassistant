# Sensofy for Home Assistant

Bring your [Sensofy](https://sensofy.io) NB-IoT sensors into Home Assistant.

This is a **cloud-polling** integration: your Home Assistant instance makes
outbound HTTPS requests to your Sensofy account and exposes each sensor as a
Home Assistant **device** with one **entity per measured field** (temperature,
humidity, CO₂, signal strength, battery, USB power, …). No inbound ports, no
MQTT exposure — it works behind any home router with normal internet access.

## Installation (HACS)

1. Make sure [HACS](https://hacs.xyz) is installed.
2. HACS → **Integrations** → ⋮ → **Custom repositories**.
3. Add `https://github.com/smartnmagic/sensofy-homeassistant`, category **Integration**.
4. Search for **Sensofy**, download it, and **restart Home Assistant**.

> Once the repository is accepted into the HACS default store, steps 2–3 are
> replaced by simply searching for "Sensofy" in HACS.

## Configuration

1. In the **Sensofy web app**: *Settings → Integrations → Home Assistant →
   Create API key*. Copy the key — it is shown only once.
2. In **Home Assistant**: *Settings → Devices & Services → Add Integration →
   Sensofy*.
3. Enter:
   - **Server URL** — `https://sensofy.io` (or your self-hosted instance)
   - **API key** — the key from step 1

Each Sensofy sensor appears as a device. Diagnostic entities (signal quality,
firmware counters) are created but **disabled by default** — enable the ones
you want from the device page.

### Options

*Settings → Devices & Services → Sensofy → Configure*:

- **Polling interval** (default `60s`, minimum `30s`)
- **Mark unavailable after** (default `0` = never; useful for battery devices
  that sleep for long periods)

## How it works

```
Sensofy device → MQTT → sensofy.io  (your multi-tenant server)
                                │
        Home Assistant ── HTTPS GET /api/integration/state (X-API-Key)
                                │
                 one Device per sensor, one entity per field
```

The API key is scoped to a single Sensofy account; the integration only ever
sees sensors owned by that account.

## API contract

`GET /api/integration/state` with header `X-API-Key: <key>` returns:

```json
{
  "server_time": 1718280000,
  "poll_interval": 60,
  "account": { "id": 1, "email": "user@example.com" },
  "sensors": [
    {
      "iccid": "8988280000000000000",
      "name": "AHT10 Outdoor",
      "last_seen": 1718279950,
      "latitude": 50.08,
      "longitude": 8.24,
      "telemetry": {
        "ts": 1718279950,
        "values": { "temperature": 22.5, "humidity": 48.1, "usb": 1 }
      },
      "attributes": {
        "ts": 1718279000,
        "values": { "rssi": -89, "operator": "26201", "band": 8, "fw": "1.4.2" }
      },
      "meta": {
        "temperature": { "unit": "°C", "name": "Outdoor Temperature" }
      }
    }
  ]
}
```

- `telemetry.values` → measurement entities; `attributes.values` → diagnostic
  entities.
- `fw` is consumed as the device firmware version (not an entity).
- `meta` is optional per-field metadata (unit / display name) that keeps Home
  Assistant in sync with the web dashboard's `fieldConfig.js`.
- All values must be in **display units** (e.g. RSRP/RSRQ already divided by 10).
- `401`/`403` triggers Home Assistant's reauth flow.

## License

MIT
