"""Typed keyboard and mouse injection methods."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from ..models import Modifier, MouseButton

if TYPE_CHECKING:
    from ..client import MacAPI


class InputClient:
    """Namespace wrapper for dangerous ``input.*`` methods."""

    def __init__(self, api: MacAPI) -> None:
        self._api = api

    async def keystroke(self, key: str, modifiers: Sequence[Modifier] = ()) -> None:
        """Send one key with optional supported modifiers."""
        await self._api.call(
            "input.keystroke",
            {"key": key, "modifiers": list(modifiers)},
            result_type=type(None),
        )

    async def type_text(self, text: str) -> None:
        """Type text through Hammerspoon's event tap."""
        await self._api.call("input.type", {"text": text}, result_type=type(None))

    async def mouse_move(self, x: float, y: float) -> None:
        """Move the pointer to absolute screen coordinates."""
        await self._api.call("input.mouseMove", {"x": x, "y": y}, result_type=type(None))

    async def mouse_click(self, *, button: MouseButton = "left", x: float, y: float) -> None:
        """Move and click a supported mouse button at absolute coordinates."""
        await self._api.call(
            "input.mouseClick",
            {"button": button, "x": x, "y": y},
            result_type=type(None),
        )
