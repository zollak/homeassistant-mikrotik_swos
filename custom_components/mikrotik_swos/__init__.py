"""MikroTik SwOS integration for Home Assistant."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant

from .const import CONF_ENABLE_ERRORS, CONF_ENABLE_STATS, CONF_VERIFY_SSL, DEFAULT_PORT, DOMAIN
from .coordinator import SwosCoordinator
from .swos_api import SwosApi

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    api = SwosApi(
        host=entry.data[CONF_HOST],
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        port=entry.data.get(CONF_PORT, DEFAULT_PORT),
        verify_ssl=entry.data.get(CONF_VERIFY_SSL, False),
        enable_stats=entry.options.get(CONF_ENABLE_STATS, entry.data.get(CONF_ENABLE_STATS, False)),
        enable_errors=entry.options.get(CONF_ENABLE_ERRORS, entry.data.get(CONF_ENABLE_ERRORS, False)),
    )

    coordinator = SwosCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when options change so stats/error sensors are added/removed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
