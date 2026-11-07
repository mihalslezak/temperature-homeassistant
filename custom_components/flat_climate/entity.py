from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FlatCoordinator


class FlatEntity(CoordinatorEntity[FlatCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: FlatCoordinator, room: str | None) -> None:
        super().__init__(coordinator)
        flat = coordinator.client.flat_id
        flat_name = "Flat " + flat.rsplit("'", 1)[-1].removeprefix("Flat")
        if room is None:
            self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, flat)}, name=flat_name,
                                                manufacturer="Building BMS", model="Flat")
        else:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{flat}'{room}")}, name=f"Room {room}",
                manufacturer="Building BMS", model=f"Room {room}",
            )
