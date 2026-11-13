# Flat climate for Home Assistant

A Home Assistant custom integration for apartment buildings whose room heating/cooling is run by a building
management system (BACnet) and controlled through a mobile app. It talks to the same HTTPS API the app uses
and gives Home Assistant:

- a **thermostat per room**: actual and set temperature, heating / cooling / idle; set point 18–26 °C in 0.5 °C steps
- a **Flat mode** select (On / Off / Eco) for the whole flat, with the app's weekly program as an attribute
- the last change sent and the building's reply on each entity (`last_write`), plus an INFO log line per change
- a re-authentication prompt when the session expires

Rooms are discovered automatically (points `R1`…`R9`); rooms that report 0 °C (no sensor) start disabled.
Rename them and assign areas in Home Assistant.

Unofficial and not affiliated with any building operator or app developer. Use it only for your own flat,
with your own account.

## Does it fit my building?

It fits if your app's traffic looks like this:

```
POST https://<host>/api/mobile/flats/<flat id>/bacnet/read
X-Session-Id: <session id>
{"endpoints": ["<flat id>'flatMode", "<flat id>'R1'roomSetTemperature", "<flat id>'R1'roomActualTemperature", ...]}

POST https://<host>/api/mobile/flats/<flat id>/bacnet/write
{"<flat id>'R1'roomSetTemperatureWrite": "21.5"}   ->   {"<flat id>'R1'roomSetTemperatureWrite": true}
```

## Install

Requires **Home Assistant 2026.11 or newer** (since 0.2.0 the thermostats use HA's `native_*` temperature API;
the old names stop working in HA 2027.11). On older HA versions, stay on 0.1.0.

**HACS:** add this repository as a custom repository (type *Integration*), install **Flat climate**, restart.

**Manual:** copy `custom_components/flat_climate` into your Home Assistant config folder, restart.

Then: Settings → Devices & services → Add integration → **Flat climate**.

## Setup values

Capture the app's traffic once (Burp Suite, HTTP Toolkit, Proxyman, mitmproxy…) and open a `…/bacnet/read` request:

| Field | Where it comes from | Example |
|---|---|---|
| API URL | the URL up to and including `/flats` | `https://<host>/api/mobile/flats` |
| Flat id | the path segment after `/flats/` | `AA'BB'Flr01'Flat101` |
| Session id | the `X-Session-Id` request header | a UUID |

Treat the session id like a password. It typically stays valid for a while after its last use; Home Assistant
polls every 60 seconds, which keeps it alive. If it expires, Home Assistant shows a **Re-authenticate** card:
capture a new session id and paste it there.

## Points used

| Point | Meaning |
|---|---|
| `flatMode` | 1 on, 2 off, 3 eco (some apps also write 4, shown as on) |
| `R<n>'roomActualTemperature` / `roomSetTemperature` | room temperature / set point; written via `roomSetTemperatureWrite` |
| `R<n>'roomStatus` | 1 idle, 2 heating, 3 cooling |
| `R<n>'roomMode` | 1 on, 2 off, 3 eco (writing it may be refused by the API) |
| `R<n>'lowLevelHeatingTemperature` / `lowLevelCoolingTemperature`, `roomDewPoint` | shown as attributes |

## Good to know

- A set point **below** the current room temperature makes the building actively **cool** that room, even in winter.
- The set point takes effect in the building at once; wall panels and the room temperature follow with a delay.
- Per-room on/off/eco may be refused by the API; use the Flat mode then.
- Set Home Assistant's unit system to Metric to see °C.

## License

MIT
