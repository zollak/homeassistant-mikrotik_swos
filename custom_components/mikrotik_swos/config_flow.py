"""Config flow for MikroTik SwOS."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME

from .const import CONF_VERIFY_SSL, DEFAULT_PORT, DOMAIN
from .swos_api import SwosApi, SwosAuthError, SwosConnectionError

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME, default="admin"): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_VERIFY_SSL, default=False): bool,
    }
)


class MikrotikSwosConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MikroTik SwOS."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            api = SwosApi(
                host=user_input[CONF_HOST],
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
                port=user_input[CONF_PORT],
                verify_ssl=user_input.get(CONF_VERIFY_SSL, False),
            )
            try:
                info = await api.test_connection()
            except SwosAuthError:
                errors["base"] = "invalid_auth"
            except SwosConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during config flow")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(f"swos_{user_input[CONF_HOST]}")
                self._abort_if_unique_id_configured()
                title = info.hostname or user_input[CONF_HOST]
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
