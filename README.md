# MikroTik SwOS integration for Home Assistant

[![HACS Validation](https://github.com/zollak/homeassistant-mikrotik-swos/actions/workflows/validate.yaml/badge.svg)](https://github.com/zollak/homeassistant-mikrotik-swos/actions/workflows/validate.yaml)

Home Assistant custom integration for **MikroTik CSS/CRS switches** running **SwOS** firmware.

Provides real-time SFP+ diagnostics sensors: temperature, voltage, TX/RX optical power, and module information.

## Supported hardware

- MikroTik CSS326-24G-2S+ (tested)
- Other CSS/CRS series running SwOS 2.x (should work, untested)

## Features

- **SFP+ diagnostics** (per slot):
  - Temperature (°C)
  - Supply voltage (V)
  - TX/RX optical power (dBm)
  - Bias current (mA)
  - Module info as attributes (vendor, part number, serial, type)
- Config flow UI setup with connection validation
- HTTP Digest authentication (SwOS native)
- Automatic polling (default: 30 seconds)

## Installation via HACS

1. Open HACS in Home Assistant
2. Click the three dots menu (top right) and select **Custom repositories**
3. Add `https://github.com/zollak/homeassistant-mikrotik-swos` with category **Integration**
4. Search for "MikroTik SwOS" and install
5. Restart Home Assistant
6. Go to **Settings > Devices & Services > Add Integration** and search for "MikroTik SwOS"

## Configuration

| Field | Default | Description |
|---|---|---|
| Host | — | Switch hostname or IP address (e.g. `10.10.10.4` or `sw1`) |
| Username | `admin` | SwOS admin username |
| Password | — | Admin password |
| Port | `80` | HTTP port |
| Verify SSL | `false` | SSL certificate verification (only for HTTPS) |

## Sensors

For each SFP+ slot (ports 25-26 on CSS326):

| Sensor | Unit | Device class |
|---|---|---|
| SFP Temperature | °C | `temperature` |
| SFP Voltage | V | `voltage` |
| SFP TX Power | dBm | — |
| SFP RX Power | dBm | — |
| SFP Bias Current | mA | — |

Sensors are only available when an SFP module is physically inserted in the slot.

The temperature sensor includes extra attributes: vendor, part number, serial, revision, and module type.

## How it works

The integration communicates with the SwOS web interface using HTTP Digest authentication. It fetches:
- System info from the `.swb` backup endpoint (hostname, IP)
- Live SFP diagnostics from the `/sfp.b` data endpoint

No SSH, SNMP, or RouterOS API is used — SwOS does not support them.

## Example use cases

### Alert on high SFP temperature

```yaml
automation:
  - alias: "SFP overheating alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.sw1_sfp26_temperature
        above: 95
    action:
      - service: notify.mobile_app
        data:
          title: "SFP Overheating"
          message: "SFP port 26 temperature is {{ states('sensor.sw1_sfp26_temperature') }}°C"
```

### Dashboard card

```yaml
type: entities
title: SW1 SFP+ Status
entities:
  - entity: sensor.sw1_sfp26_temperature
  - entity: sensor.sw1_sfp26_voltage
  - entity: sensor.sw1_sfp26_tx_power
  - entity: sensor.sw1_sfp26_rx_power
```

## Logging

Enable debug logging for troubleshooting:

```yaml
logger:
  logs:
    custom_components.mikrotik_swos: debug
```

## License

MIT License. See [LICENSE](LICENSE).
