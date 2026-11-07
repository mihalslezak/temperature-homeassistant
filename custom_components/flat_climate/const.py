"""Constants for Flat climate: a flat's rooms in a building management system (BACnet points) behind a mobile app API."""

from datetime import timedelta
import logging

DOMAIN = "flat_climate"
LOGGER = logging.getLogger(__package__)

CONF_API_URL = "api_url"  # e.g. "https://<app api host>/api/mobile/flats" (the part before /<flat id>/bacnet/...)
CONF_FLAT_ID = "flat_id"
CONF_SESSION_ID = "session_id"

UPDATE_INTERVAL = timedelta(seconds=60)  # every read also keeps the 30-day rolling session alive
SCHEDULE_EVERY = timedelta(minutes=30)

# Rooms are point prefixes R1..R9; the integration creates a thermostat for each room the API answers for.
# Rooms that report 0 °C (no sensor) start disabled. Rename rooms and assign areas in Home Assistant.
ROOM_IDS = tuple(f"R{i}" for i in range(1, 10))
ROOM_POINTS = (
    "roomSetTemperature", "roomActualTemperature", "roomStatus", "roomMode",
    "lowLevelCoolingTemperature", "lowLevelHeatingTemperature", "roomDewPoint",
)
FLAT_POINTS = (
    "flatMode", "flatModeComfortTemperature", "flatModeHolidayTemperature",
    "flatModeLowLevelCoolingTemperature", "flatModeLowLevelHeatingTemperature",
)

# flatMode / roomMode values. Some apps also write 4, which behaves like "on": read as "on", "on" is written as 1.
MODE_ON, MODE_OFF, MODE_ECO, MODE_4 = 1, 2, 3, 4
FLAT_MODES = {MODE_ON: "on", MODE_OFF: "off", MODE_ECO: "eco"}  # what HA offers and writes
FLAT_MODES_READ = {**FLAT_MODES, MODE_4: "on"}

# roomStatus: 1 idle, 2 heating, 3 cooling (a set point below the room temperature starts cooling).
STATUS_IDLE, STATUS_HEATING, STATUS_COOLING = 1, 2, 3

MIN_TEMP, MAX_TEMP, TEMP_STEP = 18.0, 26.0, 0.5
