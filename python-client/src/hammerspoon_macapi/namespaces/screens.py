from __future__ import annotations

from typing import TYPE_CHECKING, cast

from ..models import ScreenInfo, Screenshot, ScreenshotMode

if TYPE_CHECKING:
    from ..client import MacAPI


class ScreensClient:
    def __init__(self, api: MacAPI) -> None:
        self._api = api

    async def list(self) -> list[ScreenInfo]:
        return await self._api.call("screens.list", result_type=list[ScreenInfo])

    async def get(self, screen_id: str) -> ScreenInfo:
        return await self._api.call("screens.get", {"screen_id": screen_id}, result_type=ScreenInfo)

    async def set_brightness(self, screen_id: str, brightness: float) -> None:
        if not 0 <= brightness <= 1:
            raise ValueError("brightness must be between 0 and 1")
        await self._api.call(
            "screens.setBrightness",
            {"screen_id": screen_id, "brightness": brightness},
            result_type=type(None),
        )

    async def screenshot(
        self, screen_id: str | None = None, *, mode: ScreenshotMode = "inline"
    ) -> Screenshot:
        params: dict[str, object] = {"mode": mode}
        if screen_id is not None:
            params["screen_id"] = screen_id
        return cast(
            Screenshot,
            await self._api.call(
                "screens.screenshot", params, result_type=Screenshot, timeout=10.0
            ),
        )
