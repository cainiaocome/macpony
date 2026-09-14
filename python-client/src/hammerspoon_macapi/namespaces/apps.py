"""Typed application observation and control methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from ..models import ApplicationInfo

if TYPE_CHECKING:
    from ..client import MacAPI


class AppsClient:
    """Namespace wrapper for the ``apps.*`` RPC methods."""

    def __init__(self, api: MacAPI) -> None:
        self._api = api

    async def list(self) -> list[ApplicationInfo]:
        """Return all currently running applications."""
        return await self._api.call("apps.list", result_type=list[ApplicationInfo])

    async def frontmost(self) -> ApplicationInfo | None:
        """Return the frontmost application, if one is available."""
        return cast(
            ApplicationInfo | None,
            await self._api.call("apps.frontmost", result_type=ApplicationInfo | None),
        )

    async def open(self, bundle_id: str) -> ApplicationInfo:
        """Launch or focus an application by bundle identifier."""
        return await self._api.call(
            "apps.open", {"bundle_id": bundle_id}, result_type=ApplicationInfo
        )

    async def focus(self, bundle_id: str) -> None:
        """Activate a running application."""
        await self._api.call("apps.focus", {"bundle_id": bundle_id}, result_type=type(None))

    async def hide(self, bundle_id: str) -> None:
        """Hide a running application."""
        await self._api.call("apps.hide", {"bundle_id": bundle_id}, result_type=type(None))

    async def unhide(self, bundle_id: str) -> None:
        """Unhide a running application."""
        await self._api.call("apps.unhide", {"bundle_id": bundle_id}, result_type=type(None))

    async def quit(self, bundle_id: str) -> None:
        """Quit an application unless controls were disabled by configuration."""
        await self._api.call("apps.quit", {"bundle_id": bundle_id}, result_type=type(None))
