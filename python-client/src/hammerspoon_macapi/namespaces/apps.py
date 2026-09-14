from __future__ import annotations

from typing import TYPE_CHECKING, cast

from ..models import ApplicationInfo

if TYPE_CHECKING:
    from ..client import MacAPI


class AppsClient:
    def __init__(self, api: MacAPI) -> None:
        self._api = api

    async def list(self) -> list[ApplicationInfo]:
        return await self._api.call("apps.list", result_type=list[ApplicationInfo])

    async def frontmost(self) -> ApplicationInfo | None:
        return cast(
            ApplicationInfo | None,
            await self._api.call("apps.frontmost", result_type=ApplicationInfo | None),
        )

    async def open(self, bundle_id: str) -> ApplicationInfo:
        return await self._api.call(
            "apps.open", {"bundle_id": bundle_id}, result_type=ApplicationInfo
        )

    async def focus(self, bundle_id: str) -> None:
        await self._api.call("apps.focus", {"bundle_id": bundle_id}, result_type=type(None))

    async def hide(self, bundle_id: str) -> None:
        await self._api.call("apps.hide", {"bundle_id": bundle_id}, result_type=type(None))

    async def unhide(self, bundle_id: str) -> None:
        await self._api.call("apps.unhide", {"bundle_id": bundle_id}, result_type=type(None))

    async def quit(self, bundle_id: str) -> None:
        await self._api.call("apps.quit", {"bundle_id": bundle_id}, result_type=type(None))
