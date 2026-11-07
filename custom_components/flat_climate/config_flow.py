"""Setup: API URL, flat id and the app's session id (X-Session-Id). Reauth asks for a new session id when it expires."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from . import _http
from .api import FlatAuthError, FlatClient, FlatError
from .const import CONF_API_URL, CONF_FLAT_ID, CONF_SESSION_ID, DOMAIN, LOGGER


class FlatClimateConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _validate(self, api_url: str, flat_id: str, session_id: str) -> str | None:
        client = FlatClient(_http(self.hass), api_url, flat_id, session_id)
        try:
            data = await client.read([client.point("flatMode")])
        except FlatAuthError:
            return "invalid_auth"
        except FlatError as err:
            LOGGER.debug("validation failed: %s", err)
            return "cannot_connect"
        return None if client.point("flatMode") in data else "unknown_flat"

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input:
            url = user_input[CONF_API_URL].strip().rstrip("/")
            flat, sid = user_input[CONF_FLAT_ID].strip(), user_input[CONF_SESSION_ID].strip()
            await self.async_set_unique_id(f"{url}/{flat}")
            self._abort_if_unique_id_configured()
            if not url.startswith("https://"):
                errors[CONF_API_URL] = "not_https"
            elif not (err := await self._validate(url, flat, sid)):
                return self.async_create_entry(title=flat.rsplit("'", 1)[-1],
                                               data={CONF_API_URL: url, CONF_FLAT_ID: flat, CONF_SESSION_ID: sid})
            else:
                errors["base"] = err
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_API_URL): str,
                vol.Required(CONF_FLAT_ID): str,
                vol.Required(CONF_SESSION_ID): str,
            }),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input:
            sid = user_input[CONF_SESSION_ID].strip()
            if not (err := await self._validate(entry.data[CONF_API_URL], entry.data[CONF_FLAT_ID], sid)):
                return self.async_update_reload_and_abort(entry, data_updates={CONF_SESSION_ID: sid})
            errors["base"] = err
        return self.async_show_form(step_id="reauth_confirm",
                                    data_schema=vol.Schema({vol.Required(CONF_SESSION_ID): str}), errors=errors)
