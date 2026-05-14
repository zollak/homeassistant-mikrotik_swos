"""Sensor platform for MikroTik SwOS."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricPotential, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NUM_SFP, SFP_PORT_OFFSET
from .coordinator import SwosCoordinator
from .swos_api import SfpSlot, SwitchData


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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SwosCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []
    for slot_idx in range(NUM_SFP):
        port_num = SFP_PORT_OFFSET + slot_idx + 1
        for desc in SFP_SENSORS:
            entities.append(SwosSfpSensor(coordinator, entry, desc, slot_idx, port_num))

    async_add_entities(entities)


class SwosSfpSensor(CoordinatorEntity[SwosCoordinator], SensorEntity):
    """An SFP diagnostic sensor."""

    entity_description: SwosSfpSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SwosCoordinator,
        entry: ConfigEntry,
        description: SwosSfpSensorDescription,
        slot_idx: int,
        port_num: int,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._slot_idx = slot_idx
        self._port_num = port_num
        self._attr_unique_id = f"{entry.entry_id}_sfp{port_num}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": coordinator.data.system.hostname if coordinator.data else entry.title,
            "manufacturer": "MikroTik",
            "model": "CSS326-24G-2S+",
        }

    @property
    def name(self) -> str:
        return f"SFP{self._port_num} {self.entity_description.key.replace('_', ' ').title()}"

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
