"""Polls all points of the flat once a minute (one request), the schedule every 30 minutes."""

from __future__ import annotations

import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import FlatAuthError, FlatClient, FlatError
from .const import FLAT_POINTS, LOGGER, ROOM_IDS, ROOM_POINTS, SCHEDULE_EVERY, UPDATE_INTERVAL


class FlatCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: FlatClient) -> None:
        super().__init__(hass, LOGGER, config_entry=entry, name="flat_climate", update_interval=UPDATE_INTERVAL)
        self.client = client
        self.points = [client.point(p) for p in FLAT_POINTS] + [
            client.point(room, p) for room in ROOM_IDS for p in ROOM_POINTS
        ]
        self.schedule: list[dict[str, Any]] = []
        self.last_write: dict[str, dict[str, Any]] = {}  # per room / "flat": what was sent and the building's reply
        self._schedule_at = 0.0

    def rooms(self) -> list[str]:
        """Rooms the API answered for (it simply omits points that don't exist)."""
        return [r for r in ROOM_IDS if self.value(r, "roomActualTemperature") is not None]

    def value(self, *parts: str) -> Any:
        return (self.data or {}).get(self.client.point(*parts))

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self.client.read(self.points)
            if time.monotonic() - self._schedule_at > SCHEDULE_EVERY.total_seconds():
                try:
                    self.schedule = await self.client.schedule()
                    self._schedule_at = time.monotonic()
                except FlatError as err:  # the schedule is extra information only
                    LOGGER.debug("schedule read failed: %s", err)
        except FlatAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except FlatError as err:
            raise UpdateFailed(str(err)) from err
        return data

    async def write(self, point_parts: tuple[str, ...], value: float | int) -> None:
        key = point_parts[0] if len(point_parts) > 1 else "flat"
        point = self.client.point(*point_parts)
        record = {"at": dt_util.now().isoformat(timespec="seconds"), "point": point_parts[-1], "value": f"{value:g}"}
        try:
            reply = await self.client.write(point, value)
        except FlatAuthError as err:
            self.last_write[key] = {**record, "reply": "session rejected"}
            self.config_entry.async_start_reauth(self.hass)
            raise FlatError(str(err)) from err
        except FlatError as err:
            self.last_write[key] = {**record, "reply": str(err.args[1] if len(err.args) > 1 else err)}
            LOGGER.warning("write %s = %s failed: %s", point_parts[-1], record["value"], err)
            raise
        self.last_write[key] = {**record, "reply": reply.get(point)}
        LOGGER.info("write %s %s = %s -> %s", key, point_parts[-1], record["value"], reply.get(point))
        await self.async_request_refresh()
