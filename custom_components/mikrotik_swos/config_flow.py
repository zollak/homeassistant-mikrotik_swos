"""Config flow for MikroTik SwOS."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_ENABLE_ERRORS,
    CONF_ENABLE_POE,
    CONF_ENABLE_SFP,
    CONF_ENABLE_STATS,
    CONF_PORTS,
    CONF_VERIFY_SSL,
    DEFAULT_PORT,
    DOMAIN,
    NUM_PORTS,
)
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

_ALL_PORTS = [str(i) for i in range(1, NUM_PORTS + 1)]
_PORT_OPTIONS = [SelectOptionDict(value=str(i), label=f"Port {i}") for i in range(1, NUM_PORTS + 1)]


def _groups_schema(defaults: Mapping[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(CONF_ENABLE_SFP, default=defaults.get(CONF_ENABLE_SFP, True)): bool,
            vol.Optional(CONF_ENABLE_POE, default=defaults.get(CONF_ENABLE_POE, True)): bool,
            vol.Optional(CONF_ENABLE_STATS, default=defaults.get(CONF_ENABLE_STATS, False)): bool,
            vol.Optional(CONF_ENABLE_ERRORS, default=defaults.get(CONF_ENABLE_ERRORS, False)): bool,
        }
    )


def _ports_schema(defaults: Mapping[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(
                CONF_PORTS,
                default=[str(p) for p in defaults.get(CONF_PORTS, _ALL_PORTS)],
            ): SelectSelector(
                SelectSelectorConfig(
                    options=_PORT_OPTIONS,
                    multiple=True,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
        }
    )


class MikrotikSwosConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MikroTik SwOS."""

    VERSION = 1

    def __init__(self) -> None:
        self._conn: dict[str, Any] = {}
        self._title: str = ""
        self._groups: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> "MikrotikSwosOptionsFlow":
        return MikrotikSwosOptionsFlow()

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
                self._conn = user_input
                self._title = info.hostname or user_input[CONF_HOST]
                return await self.async_step_groups()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_groups(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._groups = user_input
            if user_input.get(CONF_ENABLE_STATS) or user_input.get(CONF_ENABLE_ERRORS):
                return await self.async_step_ports()
            return self._create_entry()

        return self.async_show_form(step_id="groups", data_schema=_groups_schema({}))

    async def async_step_ports(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self._create_entry(user_input)
        return self.async_show_form(step_id="ports", data_schema=_ports_schema({}))

    def _create_entry(self, ports_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        data = {**self._conn, **self._groups}
        if ports_input:
            data.update(ports_input)
        return self.async_create_entry(title=self._title, data=data)

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


class MikrotikSwosOptionsFlow(OptionsFlow):
    """Options flow: pick data groups, then (if stats/errors on) which ports."""

    def __init__(self) -> None:
        self._groups: dict[str, Any] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._groups = user_input
            if user_input.get(CONF_ENABLE_STATS) or user_input.get(CONF_ENABLE_ERRORS):
                return await self.async_step_ports()
            return self.async_create_entry(title="", data=dict(user_input))

        # HA provides self.config_entry (read-only) -- never assign it.
        cur = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=_groups_schema(cur))

    async def async_step_ports(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data={**self._groups, **user_input})

        cur = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="ports", data_schema=_ports_schema(cur))
