from __future__ import annotations

import asyncio
import contextlib
import json
import os
import statistics
import subprocess
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import cast
from uuid import uuid4

import pytest
import pytest_asyncio
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
    pytest.mark.asyncio(loop_scope="module"),
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


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def hammerspoon_client() -> AsyncIterator[MacAPI]:
    client = MacAPI(auto_reconnect=False)
    await client.connect()
    try:
        yield client
    finally:
        await client.close()


@asynccontextmanager
async def _reuse(client: MacAPI) -> AsyncIterator[MacAPI]:
    """Use the module's one long-lived client without closing it per test."""
    yield client


async def test_hammerspoon_round_trip(hammerspoon_client: MacAPI) -> None:
    async with _reuse(hammerspoon_client) as mac:
        result = cast(
            dict[str, object],
            await mac.call("protocol.ping", result_type=dict[str, object]),
        )
        assert result["pong"] is True
        assert mac.capabilities is not None
        info = await mac.system.info()
        assert info.hostname


async def test_hammerspoon_full_observation_surface(hammerspoon_client: MacAPI) -> None:
    """Exercise every read-only namespace against the real Hammerspoon server."""
    async with _reuse(hammerspoon_client) as mac:
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


async def test_hammerspoon_errors_subscriptions_and_reversible_controls(
    hammerspoon_client: MacAPI,
) -> None:
    """Exercise typed errors, subscription RPCs, and no-op-safe controls."""
    async with _reuse(hammerspoon_client) as mac:
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


async def test_hammerspoon_clipboard_event_round_trip(
    hammerspoon_client: MacAPI,
) -> None:
    """Trigger a real pasteboard watcher event and restore the prior text."""
    async with _reuse(hammerspoon_client) as mac:
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


def _hammerspoon_pid() -> int:
    """Return the real Hammerspoon process monitored by the macOS soak."""
    configured = os.getenv("HAMMERSPOON_PID")
    if configured:
        return int(configured)
    result = subprocess.run(
        ["pgrep", "-n", "-x", "Hammerspoon"],
        check=True,
        capture_output=True,
        text=True,
    )
    return int(result.stdout.strip())


def _hammerspoon_rss_kib(pid: int) -> int:
    """Read the Hammerspoon RSS value from macOS ``ps`` in KiB."""
    result = subprocess.run(
        ["ps", "-o", "rss=", "-p", str(pid)],
        check=True,
        capture_output=True,
        text=True,
    )
    values = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not values:
        raise AssertionError(
            f"Hammerspoon process {pid} disappeared while sampling RSS"
        )
    return int(values[0])


def _write_memory_report(report: dict[str, object]) -> None:
    """Write soak telemetry when the workflow provides an artifact path."""
    report_path = os.getenv("HAMMERSPOON_MEMORY_REPORT")
    if not report_path:
        return
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


async def test_hammerspoon_memory_regression(hammerspoon_client: MacAPI) -> None:
    """Exercise real RPC/watchers repeatedly and enforce a bounded RSS budget."""
    iterations = int(os.getenv("HAMMERSPOON_MEMORY_ITERATIONS", "80"))
    peak_budget_kib = int(os.getenv("HAMMERSPOON_MEMORY_PEAK_BUDGET_MIB", "96")) * 1024
    tail_budget_kib = int(os.getenv("HAMMERSPOON_MEMORY_TAIL_BUDGET_MIB", "48")) * 1024
    pid = _hammerspoon_pid()
    samples: list[dict[str, int]] = []
    report: dict[str, object] = {
        "pid": pid,
        "iterations": iterations,
        "peak_budget_kib": peak_budget_kib,
        "tail_budget_kib": tail_budget_kib,
        "samples": samples,
    }

    async def drain_events() -> None:
        async for _ in hammerspoon_client.events:
            pass

    event_consumer = asyncio.create_task(drain_events())
    try:
        await hammerspoon_client.events.subscribe(["window.*", "screen.*", "audio.*"])
        # Warm up lazy Hammerspoon/Screen Recording allocations before choosing
        # the baseline. Samples below are the steady-state comparison window.
        for iteration in range(iterations + 5):
            await hammerspoon_client.system.info()
            await hammerspoon_client.system.status()
            await hammerspoon_client.apps.list()
            await hammerspoon_client.windows.list()
            focused = await hammerspoon_client.windows.focused()
            if focused is not None:
                await hammerspoon_client.windows.set_frame(focused.id, focused.frame)
            screens = await hammerspoon_client.screens.list()
            if screens and iteration % 4 == 0:
                await hammerspoon_client.screens.screenshot(
                    screens[0].id, mode="inline"
                )
            audio = await hammerspoon_client.audio.get()
            if (
                audio.output is not None
                and audio.output.volume is not None
                and iteration % 10 == 0
            ):
                await hammerspoon_client.audio.set_volume(audio.output.volume)
            await hammerspoon_client.clipboard.get()
            await hammerspoon_client.network.get()
            await hammerspoon_client.system.user_activity()
            await asyncio.sleep(0.1)
            if iteration >= 5:
                samples.append(
                    {"iteration": iteration - 5, "rss_kib": _hammerspoon_rss_kib(pid)}
                )
    finally:
        event_consumer.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await event_consumer
        with contextlib.suppress(Exception):
            await hammerspoon_client.events.unsubscribe_all()
        if samples:
            window = max(5, min(10, len(samples) // 4))
            initial = int(
                statistics.median(sample["rss_kib"] for sample in samples[:window])
            )
            final = int(
                statistics.median(sample["rss_kib"] for sample in samples[-window:])
            )
            peak = max(sample["rss_kib"] for sample in samples)
            report.update(
                {
                    "initial_median_kib": initial,
                    "final_median_kib": final,
                    "peak_kib": peak,
                    "tail_growth_kib": final - initial,
                    "peak_growth_kib": peak - initial,
                    "sample_window": window,
                }
            )
        _write_memory_report(report)

    assert samples, "Hammerspoon memory soak did not produce any RSS samples"
    initial = int(report["initial_median_kib"])
    final = int(report["final_median_kib"])
    peak = int(report["peak_kib"])
    assert peak - initial <= peak_budget_kib, report
    assert final - initial <= tail_budget_kib, report


async def test_hammerspoon_event_iterator_closes_with_client(
    hammerspoon_client: MacAPI,
) -> None:
    """Verify the real SDK lifecycle wakes a blocked event consumer."""
    while True:
        try:
            await asyncio.wait_for(hammerspoon_client.events.__anext__(), 0.05)
        except asyncio.TimeoutError:
            break
        except StopAsyncIteration:
            break
    pending_event = asyncio.create_task(hammerspoon_client.events.__anext__())
    await hammerspoon_client.close()
    with pytest.raises(StopAsyncIteration):
        await pending_event


async def test_hammerspoon_missing_socket_reports_sdk_error(tmp_path: Path) -> None:
    """Keep initial connection failures typed even in the real macOS job."""
    client = MacAPI(tmp_path / "macapi-no-such-socket", auto_reconnect=False)
    with pytest.raises(ConnectionError):
        await client.connect()
