"""Typed system metadata, state, capability, and power-control methods."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import Capabilities, SystemInfo, SystemStatus

if TYPE_CHECKING:
    from ..client import MacAPI


class SystemClient:
    """Namespace wrapper for the ``system.*`` RPC methods."""

    def __init__(self, api: MacAPI) -> None:
        self._api = api

    async def info(self) -> SystemInfo:
        """Return hostname, macOS version, and host addresses."""
        return await self._api.call("system.info", result_type=SystemInfo)

    async def status(self) -> SystemStatus:
        """Return tracked lock/sleep state and current power information."""
        return await self._api.call("system.status", result_type=SystemStatus)

    async def capabilities(self) -> Capabilities:
        """Return the server's protocol, method, event, and feature catalog."""
        return await self._api.call("system.capabilities", result_type=Capabilities)

    async def user_activity(self) -> None:
        """Declare user activity to Hammerspoon."""
        await self._api.call("system.userActivity", result_type=type(None))

    async def lock(self) -> None:
        """Lock the screen unless controls were disabled by configuration."""
        await self._api.call("system.lock", result_type=type(None))

    async def start_screensaver(self) -> None:
        """Start the screensaver unless controls were disabled by configuration."""
        await self._api.call("system.screensaver", result_type=type(None))
