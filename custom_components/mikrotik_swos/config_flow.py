"""Config flow for MikroTik SwOS."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME

from .const import CONF_ENABLE_ERRORS, CONF_ENABLE_STATS, CONF_VERIFY_SSL, DEFAULT_PORT, DOMAIN
from .swos_api import SwosApi, SwosAuthError, SwosConnectionError

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME, default="admin"): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_VERIFY_SSL, default=False): bool,
        vol.Optional(CONF_ENABLE_STATS, default=False): bool,
        vol.Optional(CONF_ENABLE_ERRORS, default=False): bool,
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

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication when credentials become invalid."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            api = SwosApi(
                host=reauth_entry.data[CONF_HOST],
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
                port=reauth_entry.data.get(CONF_PORT, DEFAULT_PORT),
                verify_ssl=reauth_entry.data.get(CONF_VERIFY_SSL, False),
            )
            try:
                await api.test_connection()
            except SwosAuthError:
                errors["base"] = "invalid_auth"
            except SwosConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during reauth")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data={**reauth_entry.data, **user_input},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME, default=reauth_entry.data.get(CONF_USERNAME, "admin")): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )
