"""Switch platform for MikroTik SwOS — per-port enable/disable."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ENABLE_PORT_CONTROL, CONF_PORTS, DOMAIN, NUM_PORTS
from .coordinator import SwosCoordinator
from .swos_api import SwitchData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SwosCoordinator = hass.data[DOMAIN][entry.entry_id]

    def _opt(key: str, default: Any) -> Any:
        return entry.options.get(key, entry.data.get(key, default))

    enable_port_control = _opt(CONF_ENABLE_PORT_CONTROL, False)
    selected_ports = {int(p) for p in _opt(CONF_PORTS, list(range(1, NUM_PORTS + 1)))}

    entities: list[SwitchEntity] = []
    if enable_port_control:
        sys = coordinator.data.system if coordinator.data else None
        device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": sys.hostname if sys else entry.title,
            "manufacturer": "MikroTik",
            "model": sys.model if sys else "CSS326-24G-2S+",
            "serial_number": sys.serial_number if sys else None,
            "sw_version": sys.firmware if sys else None,
        }
        for port_idx in range(NUM_PORTS):
            if port_idx + 1 in selected_ports:
                entities.append(SwosPortSwitch(coordinator, entry, port_idx, device_info))

    # Remove switch entities no longer wanted (port control disabled / ports deselected).
    wanted = {e.unique_id for e in entities}
    registry = er.async_get(hass)
    for reg in er.async_entries_for_config_entry(registry, entry.entry_id):
        if reg.domain == "switch" and reg.unique_id not in wanted:
            registry.async_remove(reg.entity_id)

    async_add_entities(entities)


class SwosPortSwitch(CoordinatorEntity[SwosCoordinator], SwitchEntity):
    """Enable/disable a switch port (writes the SwOS link `en` mask)."""

    _attr_has_entity_name = True
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator, entry, port_idx, device_info):
        super().__init__(coordinator)
        self._entry = entry
        self._port_idx = port_idx
        self._port_num = port_idx + 1
        self._attr_unique_id = f"{entry.entry_id}_port{self._port_num}_enabled"
        self._attr_device_info = device_info

    @property
    def name(self) -> str:
        data: SwitchData | None = self.coordinator.data
        label = ""
        if data and self._port_idx < len(data.port_names):
            label = data.port_names[self._port_idx]
        return label or f"Port {self._port_num}"

    @property
    def is_on(self) -> bool | None:
        data: SwitchData | None = self.coordinator.data
        if data is None or self._port_idx >= len(data.port_enabled):
            return None
        return data.port_enabled[self._port_idx]

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.api.async_set_port_enabled(self._port_num, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.api.async_set_port_enabled(self._port_num, False)
        await self.coordinator.async_request_refresh()
