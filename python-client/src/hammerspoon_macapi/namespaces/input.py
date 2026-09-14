from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from ..models import Modifier, MouseButton

if TYPE_CHECKING:
    from ..client import MacAPI


class InputClient:
    def __init__(self, api: MacAPI) -> None:
        self._api = api

    async def keystroke(self, key: str, modifiers: Sequence[Modifier] = ()) -> None:
        await self._api.call(
            "input.keystroke",
            {"key": key, "modifiers": list(modifiers)},
            result_type=type(None),
        )

    async def type_text(self, text: str) -> None:
        await self._api.call("input.type", {"text": text}, result_type=type(None))

    async def mouse_move(self, x: float, y: float) -> None:
        await self._api.call("input.mouseMove", {"x": x, "y": y}, result_type=type(None))

    async def mouse_click(self, *, button: MouseButton = "left", x: float, y: float) -> None:
        await self._api.call(
            "input.mouseClick",
            {"button": button, "x": x, "y": y},
            result_type=type(None),
        )
