"""DataUpdateCoordinator for MikroTik SwOS."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .swos_api import SwosApi, SwosApiError, SwosAuthError, SwitchData

_LOGGER = logging.getLogger(__name__)


class SwosCoordinator(DataUpdateCoordinator[SwitchData]):
    """Fetch data from a MikroTik SwOS switch."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, api: SwosApi, scan_interval: int = DEFAULT_SCAN_INTERVAL) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api

    async def _async_update_data(self) -> SwitchData:
        try:
            return await self.api.fetch_data()
        except SwosAuthError as err:
            raise ConfigEntryAuthFailed("Authentication failed") from err
        except SwosApiError as err:
            raise UpdateFailed(f"Error communicating with switch: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err
