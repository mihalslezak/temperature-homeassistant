"""The flat mode (whole flat): on / off / eco (the app's mode 4 reads as on)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import FlatConfigEntry
from .api import FlatError
from .const import FLAT_MODES, FLAT_MODES_READ
from .coordinator import FlatCoordinator
from .entity import FlatEntity


async def async_setup_entry(hass: HomeAssistant, entry: FlatConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities([FlatModeSelect(entry.runtime_data)])


class FlatModeSelect(FlatEntity, SelectEntity):
    _attr_translation_key = "flat_mode"
    _attr_options = list(FLAT_MODES.values())

    def __init__(self, coordinator: FlatCoordinator) -> None:
        super().__init__(coordinator, None)
        self._attr_unique_id = f"{coordinator.client.flat_id}'flatMode"

    @property
    def current_option(self) -> str | None:
        return FLAT_MODES_READ.get(self.coordinator.value("flatMode"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        v = self.coordinator.value
        return {
            "flat_mode_raw": v("flatMode"),
            "last_write": self.coordinator.last_write.get("flat"),
            "comfort_temperature": v("flatModeComfortTemperature"),
            "holiday_temperature": v("flatModeHolidayTemperature"),
            "eco_heating_temperature": v("flatModeLowLevelHeatingTemperature"),
            "eco_cooling_temperature": v("flatModeLowLevelCoolingTemperature"),
            # the app's weekly program: per id, switch times and the mode value (1 on, 2 off)
            "schedule": [{"id": d.get("id"), "times": [f"{t['time']}={t['value']}" for t in d.get("timeValues", [])]}
                         for d in self.coordinator.schedule],
        }

    async def async_select_option(self, option: str) -> None:
        value = next(k for k, name in FLAT_MODES.items() if name == option)
        try:
            await self.coordinator.write(("flatMode",), value)
        except FlatError as err:
            raise HomeAssistantError(str(err)) from err
