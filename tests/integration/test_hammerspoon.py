from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import cast
from uuid import uuid4

import pytest
from hammerspoon_macapi import (
    AppNotFoundError,
    AudioInfo,
    ClipboardChangedEvent,
    ConnectionError,
    FileScreenshot,
    InlineScreenshot,
    InvalidParamsError,
    MacAPI,
    MethodNotFoundError,
    ScreenNotFoundError,
    SystemInfo,
    WindowNotFoundError,
)

pytestmark = [
    pytest.mark.hammerspoon,
    pytest.mark.asyncio,
    pytest.mark.skipif(
        sys.platform != "darwin" or os.getenv("RUN_HAMMERSPOON_INTEGRATION") != "1",
        reason="requires macOS, Hammerspoon, and RUN_HAMMERSPOON_INTEGRATION=1",
    ),
]


EXPECTED_METHODS = {
    "protocol.ping",
    "system.capabilities",
    "system.info",
    "system.status",
    "system.userActivity",
    "system.lock",
    "system.screensaver",
    "apps.list",
    "apps.frontmost",
    "apps.open",
    "apps.focus",
    "apps.hide",
    "apps.unhide",
    "apps.quit",
    "windows.list",
    "windows.focused",
    "windows.get",
    "windows.focus",
    "windows.minimize",
    "windows.unminimize",
    "windows.maximize",
    "windows.setFullscreen",
    "windows.setFrame",
    "windows.move",
    "screens.list",
    "screens.get",
    "screens.setBrightness",
    "screens.screenshot",
    "audio.get",
    "audio.setVolume",
    "audio.setMuted",
    "clipboard.get",
    "clipboard.set",
    "network.get",
    "input.keystroke",
    "input.type",
    "input.mouseMove",
    "input.mouseClick",
    "events.subscribe",
    "events.unsubscribe",
    "events.unsubscribeAll",
    "events.getSubscriptions",
}


async def _connect() -> MacAPI:
    client = MacAPI(auto_reconnect=False)
    await client.connect()
    return client


async def test_hammerspoon_round_trip() -> None:
    async with await _connect() as mac:
        result = cast(
            dict[str, object],
            await mac.call("protocol.ping", result_type=dict[str, object]),
        )
        assert result["pong"] is True
        assert mac.capabilities is not None
        info = await mac.system.info()
        assert info.hostname


async def test_hammerspoon_full_observation_surface() -> None:
    """Exercise every read-only namespace against the real Hammerspoon server."""
    async with await _connect() as mac:
        capabilities = await mac.system.capabilities()
        assert EXPECTED_METHODS <= set(capabilities.methods)
        assert capabilities.features.get("dangerous_actions") is True
        assert capabilities.features.get("input") is True

        info = await mac.system.info()
        assert isinstance(info, SystemInfo)
        status = await mac.system.status()
        assert status.power_source is None or isinstance(status.power_source, str)

        applications = await mac.apps.list()
        assert isinstance(applications, list)
        frontmost = await mac.apps.frontmost()
        if frontmost is not None:
            assert frontmost.name
            if frontmost.bundle_id:
                await mac.apps.open(frontmost.bundle_id)
                await mac.apps.focus(frontmost.bundle_id)

        windows = await mac.windows.list()
        focused = await mac.windows.focused()
        if focused is not None:
            assert focused in windows or focused.id > 0
            await mac.windows.focus(focused.id)
            await mac.windows.set_frame(focused.id, focused.frame)
            await mac.windows.set_fullscreen(focused.id, enabled=focused.fullscreen)

        screens = await mac.screens.list()
        assert screens
        screen = await mac.screens.get(screens[0].id)
        assert screen.id == screens[0].id
        if screen.brightness is not None:
            await mac.screens.set_brightness(screen.id, screen.brightness)

        inline = await mac.screens.screenshot(screen.id, mode="inline")
        assert isinstance(inline, InlineScreenshot)
        assert inline.decode().startswith(b"\x89PNG\r\n\x1a\n")

        file_capture = await mac.screens.screenshot(screen.id, mode="file")
        assert isinstance(file_capture, FileScreenshot)
        file_path = Path(file_capture.path)
        assert file_path.is_file()
        file_path.unlink(missing_ok=True)

        audio = await mac.audio.get()
        assert isinstance(audio, AudioInfo)
        if audio.output is not None:
            if audio.output.volume is not None:
                await mac.audio.set_volume(audio.output.volume)
            if audio.output.muted is not None:
                await mac.audio.set_muted(audio.output.muted)

        clipboard = await mac.clipboard.get()
        assert clipboard.text is None or isinstance(clipboard.text, str)
        network = await mac.network.get()
        assert isinstance(network.interfaces, list)
        await mac.system.user_activity()


async def test_hammerspoon_errors_subscriptions_and_reversible_controls() -> None:
    """Exercise typed errors, subscription RPCs, and no-op-safe controls."""
    async with await _connect() as mac:
        await mac.events.unsubscribe_all()
        with pytest.raises(MethodNotFoundError):
            await mac.call("does.not.exist", result_type=type(None))
        with pytest.raises(AppNotFoundError):
            await mac.apps.focus("com.macapi.no.such.application")
        with pytest.raises(WindowNotFoundError):
            await mac.windows.get(-1)
        with pytest.raises(ScreenNotFoundError):
            await mac.screens.get("macapi-no-such-screen")
        with pytest.raises(InvalidParamsError):
            await mac.call(
                "input.mouseMove",
                {"x": "not-a-number", "y": 0},
                result_type=type(None),
            )

        assert await mac.events.get_subscriptions() == []
        subscriptions = await mac.events.subscribe(
            ["application.*", "window.*", "clipboard.changed"]
        )
        assert {item.event for item in subscriptions} == {
            "application.*",
            "clipboard.changed",
            "window.*",
        }
        await mac.events.unsubscribe(["application.*"])
        await mac.events.unsubscribe_all()
        assert await mac.events.get_subscriptions() == []


async def test_hammerspoon_clipboard_event_round_trip() -> None:
    """Trigger a real pasteboard watcher event and restore the prior text."""
    async with await _connect() as mac:
        original = await mac.clipboard.get()
        restore_text = original.text or "macapi-e2e-clipboard-restored"
        sentinel = f"macapi-e2e-{uuid4().hex}"
        await mac.events.subscribe(["clipboard.changed"])
        pending_event = asyncio.create_task(mac.events.__anext__())
        try:
            await mac.clipboard.set(sentinel)
            event = await asyncio.wait_for(pending_event, 8)
            assert isinstance(event, ClipboardChangedEvent)
            assert event.data.text == sentinel
        finally:
            await mac.clipboard.set(restore_text)
            await mac.events.unsubscribe_all()


async def test_hammerspoon_event_iterator_closes_with_client() -> None:
    """Verify the real SDK lifecycle wakes a blocked event consumer."""
    client = await _connect()
    pending_event = asyncio.create_task(client.events.__anext__())
    await client.close()
    with pytest.raises(StopAsyncIteration):
        await pending_event


async def test_hammerspoon_raw_protocol_recovers_after_malformed_record() -> None:
    """Verify Lua protocol errors do not terminate the real socket listener."""
    socket_path = MacAPI().socket_path
    reader, writer = await asyncio.open_unix_connection(str(socket_path))
    try:
        writer.write(b"not-json\n")
        writer.write(
            json.dumps(
                {
                    "v": 1,
                    "id": "raw-e2e",
                    "type": "request",
                    "method": "protocol.ping",
                    "params": {},
                },
                separators=(",", ":"),
            ).encode()
            + b"\n"
        )
        await writer.drain()
        protocol_error = json.loads(await asyncio.wait_for(reader.readline(), 5))
        response = json.loads(await asyncio.wait_for(reader.readline(), 5))
        assert protocol_error["type"] == "protocol_error"
        assert protocol_error["code"] == "PROTOCOL_ERROR"
        assert response["id"] == "raw-e2e"
        assert response["ok"] is True
        assert response["result"]["pong"] is True
    finally:
        writer.close()
        await writer.wait_closed()


async def test_hammerspoon_missing_socket_reports_sdk_error(tmp_path: Path) -> None:
    """Keep initial connection failures typed even in the real macOS job."""
    client = MacAPI(tmp_path / "macapi-no-such-socket", auto_reconnect=False)
    with pytest.raises(ConnectionError):
        await client.connect()
