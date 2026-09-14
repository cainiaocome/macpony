from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import Capabilities, SystemInfo, SystemStatus

if TYPE_CHECKING:
    from ..client import MacAPI


class SystemClient:
    def __init__(self, api: MacAPI) -> None:
        self._api = api

    async def info(self) -> SystemInfo:
        return await self._api.call("system.info", result_type=SystemInfo)

    async def status(self) -> SystemStatus:
        return await self._api.call("system.status", result_type=SystemStatus)

    async def capabilities(self) -> Capabilities:
        return await self._api.call("system.capabilities", result_type=Capabilities)

    async def user_activity(self) -> None:
        await self._api.call("system.userActivity", result_type=type(None))

    async def lock(self) -> None:
        await self._api.call("system.lock", result_type=type(None))

    async def start_screensaver(self) -> None:
        await self._api.call("system.screensaver", result_type=type(None))
