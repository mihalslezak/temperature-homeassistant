"""Minimal client for the app API: read points, write points, read the schedule."""

from __future__ import annotations

from typing import Any

import aiohttp



class FlatError(Exception):
    """API call failed."""


class FlatAuthError(FlatError):
    """The session id is not (or no longer) valid."""


class FlatClient:
    def __init__(self, session: aiohttp.ClientSession, api_url: str, flat_id: str, session_id: str) -> None:
        self._http = session
        self.api_url = api_url.rstrip("/")
        self.flat_id = flat_id
        self._session_id = session_id

    def point(self, *parts: str) -> str:
        """Full BACnet point name, e.g. point("R1", "roomMode") -> "<flat id>'R1'roomMode"."""
        return "'".join((self.flat_id, *parts))

    async def _call(self, method: str, path: str, payload: Any = None) -> Any:
        url = f"{self.api_url}/{self.flat_id}/bacnet/{path}"
        headers = {
            "Accept": "application/json, text/plain, */*",
            "X-Session-Id": self._session_id,
            "Origin": "capacitor://localhost",  # as the app sends it
        }
        try:
            async with self._http.request(method, url, json=payload, headers=headers,
                                          timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status in (401, 403):
                    raise FlatAuthError(f"session rejected (HTTP {resp.status})")
                if resp.status >= 400:
                    text = (await resp.text())[:200]
                    raise FlatError(f"HTTP {resp.status}: {text}")
                return await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise FlatError(f"cannot reach the API: {err}") from err

    async def read(self, points: list[str]) -> dict[str, Any]:
        data = await self._call("POST", "read", {"endpoints": points})
        if not isinstance(data, dict):
            raise FlatError("unexpected read response")
        return data

    async def write(self, point: str, value: float | int) -> Any:
        """Write one point (the app sends values as strings: "24", "23.5"); returns the building's reply.
        Success is exactly {point: true}; anything else raises."""
        data = await self._call("POST", "write", {point: f"{value:g}"})
        if not isinstance(data, dict) or data.get(point) is not True:
            raise FlatError(f"the building refused writing {point.split(chr(39), 4)[-1]} = {value:g} ({data})", data)
        return data

    async def schedule(self) -> list[dict[str, Any]]:
        data = await self._call("GET", "read/scheduler")
        return data if isinstance(data, list) else []
