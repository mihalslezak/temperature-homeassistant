"""Flat climate: room thermostats and the flat mode from a building management system's app API."""

from __future__ import annotations

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import FlatClient
from .const import CONF_API_URL, CONF_FLAT_ID, CONF_SESSION_ID, DOMAIN
from .coordinator import FlatCoordinator



def _http(hass: HomeAssistant):
    # No cookie jar: the API also sets a sessionId cookie, which would mask an expired X-Session-Id.
    return async_create_clientsession(hass, cookie_jar=aiohttp.DummyCookieJar())


PLATFORMS = [Platform.CLIMATE, Platform.SELECT]

type FlatConfigEntry = ConfigEntry[FlatCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: FlatConfigEntry) -> bool:
    client = FlatClient(_http(hass), entry.data[CONF_API_URL], entry.data[CONF_FLAT_ID], entry.data[CONF_SESSION_ID])
    coordinator = FlatCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    # the flat device first: the room devices point to it (via_device)
    flat = entry.data[CONF_FLAT_ID]
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, flat)},
        name="Flat " + flat.rsplit("'", 1)[-1].removeprefix("Flat"), manufacturer="Building BMS", model="Flat",
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FlatConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
