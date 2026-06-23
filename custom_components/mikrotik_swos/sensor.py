"""Sensor platform for MikroTik SwOS."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfInformation,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ENABLE_ERRORS,
    CONF_ENABLE_POE,
    CONF_ENABLE_SFP,
    CONF_ENABLE_STATS,
    CONF_PORTS,
    DOMAIN,
    NUM_PORTS,
    NUM_SFP,
    SFP_PORT_OFFSET,
)


def _boot_time(uptime_seconds: int | None) -> datetime | None:
    """Convert uptime seconds to a stable boot timestamp (rounded to the minute)."""
    if not uptime_seconds:
        return None
    boot = dt_util.utcnow() - timedelta(seconds=uptime_seconds)
    return boot.replace(second=0, microsecond=0)
from .coordinator import SwosCoordinator
from .swos_api import POE_STATE_OPTIONS, PoePort, PortErrors, PortStats, SfpSlot, SwitchData


# ── System sensor descriptions ────────────────────────────────────────────────


@dataclass(frozen=True, kw_only=True)
class SwosSystemSensorDescription(SensorEntityDescription):
    value_fn: Callable[[SwitchData], Any]


SYSTEM_SENSORS: tuple[SwosSystemSensorDescription, ...] = (
    SwosSystemSensorDescription(
        key="board_temperature",
        translation_key="board_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.system.board_temp_c,
    ),
    SwosSystemSensorDescription(
        key="uptime",
        translation_key="uptime",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda d: _boot_time(d.system.uptime_seconds),
    ),
)

PSU_SENSORS: tuple[SwosSystemSensorDescription, ...] = (
    SwosSystemSensorDescription(
        key="psu1_voltage",
        translation_key="psu1_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.system.psu1_voltage_v or None,
    ),
    SwosSystemSensorDescription(
        key="psu1_current",
        translation_key="psu1_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.system.psu1_current_ma or None,
    ),
    SwosSystemSensorDescription(
        key="psu1_power",
        translation_key="psu1_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.system.psu1_power_w or None,
    ),
    SwosSystemSensorDescription(
        key="psu2_voltage",
        translation_key="psu2_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.system.psu2_voltage_v or None,
    ),
    SwosSystemSensorDescription(
        key="psu2_current",
        translation_key="psu2_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.system.psu2_current_ma or None,
    ),
    SwosSystemSensorDescription(
        key="psu2_power",
        translation_key="psu2_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.system.psu2_power_w or None,
    ),
    SwosSystemSensorDescription(
        key="power_consumption",
        translation_key="power_consumption",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.system.power_consumption_w or None,
    ),
)


# ── SFP sensor descriptions ──────────────────────────────────────────────────


@dataclass(frozen=True, kw_only=True)
class SwosSfpSensorDescription(SensorEntityDescription):
    value_fn: Callable[[SfpSlot], Any]


SFP_SENSORS: tuple[SwosSfpSensorDescription, ...] = (
    SwosSfpSensorDescription(
        key="temperature",
        translation_key="sfp_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.temperature_c,
    ),
    SwosSfpSensorDescription(
        key="voltage",
        translation_key="sfp_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.voltage_v,
    ),
    SwosSfpSensorDescription(
        key="tx_power",
        translation_key="sfp_tx_power",
        native_unit_of_measurement="dBm",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:signal",
        value_fn=lambda s: s.tx_power_dbm,
    ),
    SwosSfpSensorDescription(
        key="rx_power",
        translation_key="sfp_rx_power",
        native_unit_of_measurement="dBm",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:signal",
        value_fn=lambda s: s.rx_power_dbm,
    ),
    SwosSfpSensorDescription(
        key="bias_current",
        translation_key="sfp_bias_current",
        native_unit_of_measurement="mA",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:current-dc",
        value_fn=lambda s: s.bias_current_ma,
    ),
)


# ── Port stats sensor descriptions ───────────────────────────────────────────


@dataclass(frozen=True, kw_only=True)
class SwosPortStatsSensorDescription(SensorEntityDescription):
    value_fn: Callable[[PortStats], Any]


PORT_STATS_SENSORS: tuple[SwosPortStatsSensorDescription, ...] = (
    SwosPortStatsSensorDescription(
        key="rx_bytes",
        translation_key="port_rx_bytes",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:download-network",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda p: p.rx_bytes,
    ),
    SwosPortStatsSensorDescription(
        key="tx_bytes",
        translation_key="port_tx_bytes",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:upload-network",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda p: p.tx_bytes,
    ),
    SwosPortStatsSensorDescription(
        key="rx_packets",
        translation_key="port_rx_packets",
        native_unit_of_measurement="packets",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:package-down",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda p: p.rx_packets,
    ),
    SwosPortStatsSensorDescription(
        key="tx_packets",
        translation_key="port_tx_packets",
        native_unit_of_measurement="packets",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:package-up",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda p: p.tx_packets,
    ),
)


# ── Port error sensor descriptions ───────────────────────────────────────────


@dataclass(frozen=True, kw_only=True)
class SwosPortErrorSensorDescription(SensorEntityDescription):
    value_fn: Callable[[PortErrors], Any]


PORT_ERROR_SENSORS: tuple[SwosPortErrorSensorDescription, ...] = (
    SwosPortErrorSensorDescription(
        key="rx_fcs_errors",
        translation_key="port_rx_fcs_errors",
        native_unit_of_measurement="errors",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:alert-circle",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda p: p.rx_fcs,
    ),
    SwosPortErrorSensorDescription(
        key="rx_align_errors",
        translation_key="port_rx_align_errors",
        native_unit_of_measurement="errors",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:alert-circle",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda p: p.rx_align,
    ),
    SwosPortErrorSensorDescription(
        key="rx_runts",
        translation_key="port_rx_runts",
        native_unit_of_measurement="frames",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:alert-circle",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda p: p.rx_runts,
    ),
    SwosPortErrorSensorDescription(
        key="rx_oversized",
        translation_key="port_rx_oversized",
        native_unit_of_measurement="frames",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:alert-circle",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda p: p.rx_oversized,
    ),
    SwosPortErrorSensorDescription(
        key="tx_collisions",
        translation_key="port_tx_collisions",
        native_unit_of_measurement="collisions",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:alert-circle",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda p: p.tx_collisions,
    ),
)


# ── PoE sensor descriptions ────────────────────────────────────────────────


@dataclass(frozen=True, kw_only=True)
class SwosPoeSensorDescription(SensorEntityDescription):
    value_fn: Callable[[PoePort], Any]


POE_PORT_SENSORS: tuple[SwosPoeSensorDescription, ...] = (
    SwosPoeSensorDescription(
        key="poe_power",
        translation_key="poe_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda p: p.power_w or None,
    ),
    SwosPoeSensorDescription(
        key="poe_current",
        translation_key="poe_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda p: p.current_ma or None,
    ),
    SwosPoeSensorDescription(
        key="poe_voltage",
        translation_key="poe_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda p: p.voltage_v or None,
    ),
    SwosPoeSensorDescription(
        key="poe_state",
        translation_key="poe_state",
        device_class=SensorDeviceClass.ENUM,
        options=POE_STATE_OPTIONS,
        icon="mdi:lightning-bolt",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda p: p.state,
    ),
)


# ── Setup ─────────────────────────────────────────────────────────────────────


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SwosCoordinator = hass.data[DOMAIN][entry.entry_id]
    device_info = _build_device_info(coordinator, entry)

    # Group toggles + port selection. Options (set later via the options flow)
    # take precedence over the values captured at initial setup. board temperature
    # and uptime are always present (the base group).
    def _opt(key: str, default: Any) -> Any:
        return entry.options.get(key, entry.data.get(key, default))

    enable_sfp = _opt(CONF_ENABLE_SFP, True)
    enable_stats = _opt(CONF_ENABLE_STATS, False)
    enable_errors = _opt(CONF_ENABLE_ERRORS, False)
    enable_poe = _opt(CONF_ENABLE_POE, True)
    selected_ports = {int(p) for p in _opt(CONF_PORTS, list(range(1, NUM_PORTS + 1)))}

    entities: list[SensorEntity] = []

    for desc in SYSTEM_SENSORS:
        entities.append(SwosSystemSensor(coordinator, entry, desc, device_info))

    if enable_sfp:
        for slot_idx in range(NUM_SFP):
            port_num = SFP_PORT_OFFSET + slot_idx + 1
            for desc in SFP_SENSORS:
                entities.append(SwosSfpSensor(coordinator, entry, desc, slot_idx, port_num, device_info))

    if enable_stats:
        for port_idx in range(NUM_PORTS):
            if port_idx + 1 not in selected_ports:
                continue
            for desc in PORT_STATS_SENSORS:
                entities.append(SwosPortStatsSensor(coordinator, entry, desc, port_idx, device_info))

    if enable_errors:
        for port_idx in range(NUM_PORTS):
            if port_idx + 1 not in selected_ports:
                continue
            for desc in PORT_ERROR_SENSORS:
                entities.append(SwosPortErrorSensor(coordinator, entry, desc, port_idx, device_info))

    # PoE sensors (auto-detected; only if the switch has PoE AND the group is enabled)
    if enable_poe and coordinator.data and coordinator.data.poe_available:
        for desc in PSU_SENSORS:
            entities.append(SwosSystemSensor(coordinator, entry, desc, device_info))
        for poe_port in coordinator.data.poe_ports:
            for desc in POE_PORT_SENSORS:
                entities.append(SwosPoeSensor(coordinator, entry, desc, poe_port.port - 1, device_info))

    # Remove registry entries for entities we are no longer creating (e.g. a group
    # was disabled or ports deselected via the options flow). HA does not purge these
    # on its own -- without this they linger as "unavailable".
    wanted_uids = {e.unique_id for e in entities}
    registry = er.async_get(hass)
    for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if reg_entry.unique_id not in wanted_uids:
            registry.async_remove(reg_entry.entity_id)

    async_add_entities(entities)


def _build_device_info(coordinator: SwosCoordinator, entry: ConfigEntry) -> dict:
    sys = coordinator.data.system if coordinator.data else None
    return {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": sys.hostname if sys else entry.title,
        "manufacturer": "MikroTik",
        "model": sys.model if sys else "CSS326-24G-2S+",
        "serial_number": sys.serial_number if sys else None,
        "sw_version": sys.firmware if sys else None,
    }


# ── System sensor entity ─────────────────────────────────────────────────────


class SwosSystemSensor(CoordinatorEntity[SwosCoordinator], SensorEntity):
    entity_description: SwosSystemSensorDescription
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, description, device_info):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = device_info

    @property
    def native_value(self) -> Any:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)


# ── SFP sensor entity ────────────────────────────────────────────────────────


class SwosSfpSensor(CoordinatorEntity[SwosCoordinator], SensorEntity):
    entity_description: SwosSfpSensorDescription
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry, description, slot_idx, port_num, device_info):
        super().__init__(coordinator)
        self.entity_description = description
        self._slot_idx = slot_idx
        self._port_num = port_num
        self._attr_unique_id = f"{entry.entry_id}_sfp{port_num}_{description.key}"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return f"SFP+ {self._slot_idx + 1} {self.entity_description.key.replace('_', ' ').title()}"

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        slot = self._get_slot()
        return slot is not None and slot.present

    @property
    def native_value(self) -> Any:
        slot = self._get_slot()
        if slot is None or not slot.present:
            return None
        return self.entity_description.value_fn(slot)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        slot = self._get_slot()
        if slot is None or not slot.present:
            return None
        if self.entity_description.key != "temperature":
            return None
        return {
            "vendor": slot.vendor,
            "part_number": slot.part_number,
            "serial": slot.serial,
            "revision": slot.revision,
            "type": slot.sfp_type,
        }

    def _get_slot(self) -> SfpSlot | None:
        data: SwitchData | None = self.coordinator.data
        if data is None or self._slot_idx >= len(data.sfp_slots):
            return None
        return data.sfp_slots[self._slot_idx]


# ── Port stats sensor entity ─────────────────────────────────────────────────


class SwosPortStatsSensor(CoordinatorEntity[SwosCoordinator], SensorEntity):
    entity_description: SwosPortStatsSensorDescription
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, description, port_idx, device_info):
        super().__init__(coordinator)
        self.entity_description = description
        self._port_idx = port_idx
        self._port_num = port_idx + 1
        self._attr_unique_id = f"{entry.entry_id}_port{self._port_num}_{description.key}"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        ps = self._get_stats()
        label = ps.name if ps and ps.name else f"Port {self._port_num}"
        return f"{label} {self.entity_description.key.replace('_', ' ').title()}"

    @property
    def native_value(self) -> Any:
        ps = self._get_stats()
        if ps is None:
            return None
        return self.entity_description.value_fn(ps)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        ps = self._get_stats()
        if ps is None:
            return None
        if self.entity_description.key == "rx_bytes":
            return {"link_up": ps.link_up}
        return None

    def _get_stats(self) -> PortStats | None:
        data: SwitchData | None = self.coordinator.data
        if data is None or self._port_idx >= len(data.port_stats):
            return None
        return data.port_stats[self._port_idx]


# ── Port error sensor entity ─────────────────────────────────────────────────


class SwosPortErrorSensor(CoordinatorEntity[SwosCoordinator], SensorEntity):
    entity_description: SwosPortErrorSensorDescription
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, description, port_idx, device_info):
        super().__init__(coordinator)
        self.entity_description = description
        self._port_idx = port_idx
        self._port_num = port_idx + 1
        self._attr_unique_id = f"{entry.entry_id}_port{self._port_num}_{description.key}"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return f"Port {self._port_num} {self.entity_description.key.replace('_', ' ').title()}"

    @property
    def native_value(self) -> Any:
        pe = self._get_errors()
        if pe is None:
            return None
        return self.entity_description.value_fn(pe)

    def _get_errors(self) -> PortErrors | None:
        data: SwitchData | None = self.coordinator.data
        if data is None or self._port_idx >= len(data.port_errors):
            return None
        return data.port_errors[self._port_idx]


# ── PoE sensor entity ────────────────────────────────────────────────────────


class SwosPoeSensor(CoordinatorEntity[SwosCoordinator], SensorEntity):
    entity_description: SwosPoeSensorDescription
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, description, port_idx, device_info):
        super().__init__(coordinator)
        self.entity_description = description
        self._port_idx = port_idx
        self._port_num = port_idx + 1
        self._attr_unique_id = f"{entry.entry_id}_port{self._port_num}_{description.key}"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        return f"Port {self._port_num} {self.entity_description.key.replace('_', ' ').replace('poe ', 'PoE ').title()}"

    @property
    def native_value(self) -> Any:
        poe = self._get_poe()
        if poe is None:
            return None
        return self.entity_description.value_fn(poe)

    def _get_poe(self) -> PoePort | None:
        data: SwitchData | None = self.coordinator.data
        if data is None or self._port_idx >= len(data.poe_ports):
            return None
        return data.poe_ports[self._port_idx]
