# MikroTik SwOS integration for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/zollak/homeassistant-mikrotik_swos?style=for-the-badge)](https://github.com/zollak/homeassistant-mikrotik_swos/releases)
[![GitHub Downloads](https://img.shields.io/github/downloads/zollak/homeassistant-mikrotik_swos/total?style=for-the-badge)](https://github.com/zollak/homeassistant-mikrotik_swos/releases)
[![GitHub Issues](https://img.shields.io/github/issues/zollak/homeassistant-mikrotik_swos?style=for-the-badge)](https://github.com/zollak/homeassistant-mikrotik_swos/issues)
[![HACS Validation](https://img.shields.io/github/actions/workflow/status/zollak/homeassistant-mikrotik_swos/validate.yaml?style=for-the-badge&label=HACS)](https://github.com/zollak/homeassistant-mikrotik_swos/actions/workflows/validate.yaml)

Home Assistant custom integration for **MikroTik CSS/CRS switches** running **SwOS** firmware.

Provides system monitoring, SFP+ diagnostics, per-port traffic statistics, per-port error counters, and PoE monitoring.

## Supported hardware

| Model | Tested | PoE |
|---|---|---|
| CSS326-24G-2S+ | Yes | No |
| CRS328-24P-4S+RM | No | Yes |
| CRS112-8P-4S-IN | No | Yes |
| Other CSS/CRS with SwOS 2.x | No | Varies |

## Features

- **System monitoring**:
  - Board temperature (°C)
  - Uptime (seconds)
  - Device info: model, serial number, firmware version, MAC, IP
- **SFP+ diagnostics** (per slot):
  - Temperature (°C)
  - Supply voltage (V)
  - TX/RX optical power (dBm)
  - Bias current (mA)
  - Module info as attributes (vendor, part number, serial, type)
- **Per-port traffic statistics** (optional, 26 ports):
  - RX/TX bytes (64-bit counters)
  - RX/TX packets
- **Per-port error counters** (optional, 26 ports):
  - RX FCS errors
  - RX alignment errors
  - RX runts (undersized frames)
  - RX oversized frames
  - TX collisions
- **PoE monitoring** (auto-detected on PoE-capable switches):
  - PSU1/PSU2: voltage (V), current (mA), power (W)
  - Total power consumption (W)
  - Per-port: power (W), current (mA), voltage (V), state
  - PoE states: powered_on, disabled, waiting_for_load, overload, short_circuit, etc.
- Config flow UI with connection validation
- Re-authentication flow (password change without removing the integration)
- HTTP Digest authentication (SwOS native)
- Automatic polling (default: 30 seconds)

## Installation via HACS

[![Open HACS repository in Home Assistant](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=zollak&repository=homeassistant-mikrotik_swos&category=integration)

Or manually:

1. Open HACS in Home Assistant
2. Click the three dots menu (top right) and select **Custom repositories**
3. Add `https://github.com/zollak/homeassistant-mikrotik_swos` with category **Integration**
4. Search for "MikroTik SwOS" and install
5. Restart Home Assistant

## Configuration

[![Add integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=mikrotik_swos)

Or manually: **Settings > Devices & Services > Add Integration** and search for "MikroTik SwOS".

| Field | Default | Description |
|---|---|---|
| Host | — | Switch hostname or IP address (e.g. `10.10.10.4` or `sw1`) |
| Username | `admin` | SwOS admin username |
| Password | — | Admin password |
| Port | `80` | HTTP port |
| Verify SSL | `false` | SSL certificate verification (only for HTTPS) |
| Enable per-port traffic statistics | `false` | Creates RX/TX bytes and packet sensors for all 26 ports |
| Enable per-port error counters | `false` | Creates error counter sensors for all 26 ports |

> **Note:** Enabling stats creates 4 sensors per port (104 total), errors creates 5 sensors per port (130 total). PoE sensors are auto-detected and always created on PoE-capable switches. Only enable stats/errors if you need them.

## Sensors

### System

| Sensor | Unit | Device class |
|---|---|---|
| Board Temperature | °C | `temperature` |
| Uptime | s | `duration` |

The device info panel shows model, serial number, and firmware version.

### SFP+ (per slot, ports 25-26 on CSS326)

| Sensor | Unit | Device class |
|---|---|---|
| SFP Temperature | °C | `temperature` |
| SFP Voltage | V | `voltage` |
| SFP TX Power | dBm | — |
| SFP RX Power | dBm | — |
| SFP Bias Current | mA | — |

Sensors are only available when an SFP module is physically inserted in the slot.

The temperature sensor includes extra attributes: vendor, part number, serial, revision, and module type.

### Per-port traffic statistics (optional)

| Sensor | Unit | State class |
|---|---|---|
| RX Bytes | B | `total_increasing` |
| TX Bytes | B | `total_increasing` |
| RX Packets | — | `total_increasing` |
| TX Packets | — | `total_increasing` |

### Per-port error counters (optional)

| Sensor | Unit | State class |
|---|---|---|
| RX FCS Errors | — | `total_increasing` |
| RX Alignment Errors | — | `total_increasing` |
| RX Runts | — | `total_increasing` |
| RX Oversized | — | `total_increasing` |
| TX Collisions | — | `total_increasing` |

### PoE (auto-detected, PoE switches only)

**System-level:**

| Sensor | Unit | Device class |
|---|---|---|
| PSU1 Voltage | V | `voltage` |
| PSU1 Current | mA | `current` |
| PSU1 Power | W | `power` |
| PSU2 Voltage | V | `voltage` |
| PSU2 Current | mA | `current` |
| PSU2 Power | W | `power` |
| Power Consumption | W | `power` |

**Per-port:**

| Sensor | Unit | Device class |
|---|---|---|
| PoE Power | W | `power` |
| PoE Current | mA | `current` |
| PoE Voltage | V | `voltage` |
| PoE State | — | `enum` |

PoE state values: `disabled`, `waiting_for_load`, `powered_on`, `overload`, `short_circuit`, `voltage_too_low`, `current_too_low`, `power_cycle`, `voltage_too_high`, `controller_error`.

## How it works

The integration communicates with the SwOS web interface using HTTP Digest authentication. It fetches live data from:
- `/sys.b` — system info (hostname, model, serial, firmware, uptime, board temperature, PSU metrics)
- `/sfp.b` — SFP+ diagnostics (DDM values, module identification)
- `/link.b` — port names and link status
- `/stats.b` — per-port traffic statistics and error counters
- `/poe.b` — per-port PoE status and power metrics (PoE switches only)

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

### Alert on FCS errors

```yaml
automation:
  - alias: "Port FCS error spike"
    trigger:
      - platform: state
        entity_id: sensor.sw1_port18_rx_fcs_errors
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.state | int > trigger.from_state.state | int }}"
    action:
      - service: notify.mobile_app
        data:
          title: "FCS Errors Detected"
          message: "Port 18 FCS error count: {{ states('sensor.sw1_port18_rx_fcs_errors') }}"
```

### PoE power budget alert

```yaml
automation:
  - alias: "PoE power budget warning"
    trigger:
      - platform: numeric_state
        entity_id: sensor.sw1_power_consumption
        above: 200
    action:
      - service: notify.mobile_app
        data:
          title: "PoE Power Warning"
          message: "Total PoE power consumption: {{ states('sensor.sw1_power_consumption') }}W"
```

### Dashboard card

```yaml
type: entities
title: SW1 Overview
entities:
  - entity: sensor.sw1_board_temperature
  - entity: sensor.sw1_uptime
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
