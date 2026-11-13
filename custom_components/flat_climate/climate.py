"""One thermostat per room: actual and set temperature, room mode (on/off/eco), heating/cooling status."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    PRESET_ECO, PRESET_NONE, ClimateEntity, ClimateEntityFeature, HVACAction, HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import FlatConfigEntry
from .api import FlatError
from .const import (
    MAX_TEMP, MIN_TEMP, MODE_ECO, MODE_OFF, MODE_ON, STATUS_COOLING, STATUS_HEATING, STATUS_IDLE, TEMP_STEP,
)
from .coordinator import FlatCoordinator
from .entity import FlatEntity

ROOM_MODE_NOTE = ("The building API rejected the room mode change. Per-room on/off/eco is not supported by the "
                  "building API (yet); use the flat mode instead.")


async def async_setup_entry(hass: HomeAssistant, entry: FlatConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities(FlatRoomClimate(entry.runtime_data, room) for room in entry.runtime_data.rooms())


class FlatRoomClimate(FlatEntity, ClimateEntity):
    _attr_name = None  # the device name ("Room R1", rename it in HA) is the entity name
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS  # native_* API: HA 2026.11+
    _attr_hvac_modes = [HVACMode.AUTO, HVACMode.OFF]  # AUTO = on: the building heats or cools to the set point
    _attr_preset_modes = [PRESET_NONE, PRESET_ECO]
    _attr_min_temp, _attr_max_temp, _attr_target_temperature_step = MIN_TEMP, MAX_TEMP, TEMP_STEP
    _attr_supported_features = (ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
                                | ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF)

    def __init__(self, coordinator: FlatCoordinator, room: str) -> None:
        super().__init__(coordinator, room)
        self.room = room
        self._attr_unique_id = f"{coordinator.client.flat_id}'{room}'climate"
        self._attr_entity_registry_enabled_default = bool(coordinator.value(room, "roomActualTemperature"))  # 0 °C = no sensor

    def _v(self, point: str) -> Any:
        return self.coordinator.value(self.room, point)

    @property
    def available(self) -> bool:
        return super().available and self._v("roomActualTemperature") is not None

    @property
    def native_current_temperature(self) -> float | None:
        return self._v("roomActualTemperature")

    @property
    def native_target_temperature(self) -> float | None:
        return self._v("roomSetTemperature")

    @property
    def hvac_mode(self) -> HVACMode | None:
        mode = self._v("roomMode")
        return HVACMode.OFF if mode == MODE_OFF else HVACMode.AUTO if mode in (MODE_ON, MODE_ECO) else None

    @property
    def preset_mode(self) -> str | None:
        return PRESET_ECO if self._v("roomMode") == MODE_ECO else PRESET_NONE

    @property
    def hvac_action(self) -> HVACAction | None:
        if self._v("roomMode") == MODE_OFF:
            return HVACAction.OFF
        return {STATUS_IDLE: HVACAction.IDLE, STATUS_HEATING: HVACAction.HEATING,
                STATUS_COOLING: HVACAction.COOLING}.get(self._v("roomStatus"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "room": self.room,
            "room_status_raw": self._v("roomStatus"),
            "room_mode_raw": self._v("roomMode"),
            "eco_heating_temperature": self._v("lowLevelHeatingTemperature"),
            "eco_cooling_temperature": self._v("lowLevelCoolingTemperature"),
            "dew_point": self._v("roomDewPoint"),
            "last_write": self.coordinator.last_write.get(self.room),
        }

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        temp = round(float(temp) / TEMP_STEP) * TEMP_STEP
        if not MIN_TEMP <= temp <= MAX_TEMP:
            raise HomeAssistantError(f"{temp:g} °C is outside {MIN_TEMP:g}–{MAX_TEMP:g} °C")
        try:
            await self.coordinator.write((self.room, "roomSetTemperatureWrite"), temp)
        except FlatError as err:
            raise HomeAssistantError(str(err)) from err

    async def _write_mode(self, mode: int) -> None:
        # The app's key is "<flat>'R1'roomMode"; the building API has rejected it so far.
        # Kept so it starts working if the API ever accepts it.
        try:
            await self.coordinator.write((self.room, "roomMode"), mode)
        except FlatError as err:
            raise HomeAssistantError(f"{ROOM_MODE_NOTE} ({err})") from err

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        await self._write_mode(MODE_OFF if hvac_mode == HVACMode.OFF else MODE_ON)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        await self._write_mode(MODE_ECO if preset_mode == PRESET_ECO else MODE_ON)

    async def async_turn_on(self) -> None:
        await self._write_mode(MODE_ON)

    async def async_turn_off(self) -> None:
        await self._write_mode(MODE_OFF)
