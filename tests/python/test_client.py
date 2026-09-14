from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from hammerspoon_macapi import (
    ConnectionError,
    ConnectionLostError,
    MacAPI,
    MacEvent,
    RPCTimeoutError,
    WindowFocusedEvent,
)
from hammerspoon_macapi.exceptions import ProtocolError
from hammerspoon_macapi.models import ApplicationInfo, SystemInfo, WindowInfo

from .fake_server import FakeMacAPIServer


@pytest_asyncio.fixture
async def fake_server():
    runtime_dir = Path(tempfile.mkdtemp(prefix="mapi-"))
    server = FakeMacAPIServer(runtime_dir / "macapi.sock")
    await server.start()
    try:
        yield server
    finally:
        await server.close()
        shutil.rmtree(runtime_dir)


async def connected_client(server: FakeMacAPIServer) -> MacAPI:
    client = MacAPI(server.path, auto_reconnect=False)
    await client.connect()
    return client


@pytest.mark.asyncio
async def test_concurrent_out_of_order_rpc_responses(
    fake_server: FakeMacAPIServer,
) -> None:
    client = await connected_client(fake_server)
    try:
        system_task = asyncio.create_task(client.system.info())
        apps_task = asyncio.create_task(client.apps.list())
        windows_task = asyncio.create_task(client.windows.list())

        requests = [
            await fake_server.wait_for_method("system.info"),
            await fake_server.wait_for_method("apps.list"),
            await fake_server.wait_for_method("windows.list"),
        ]
        by_method = {str(request["method"]): request for request in requests}
        await fake_server.send_response(
            str(by_method["windows.list"]["id"]),
            [
                {
                    "id": 3,
                    "title": "Terminal",
                    "app": "Terminal",
                    "frame": {"x": 0, "y": 0, "w": 100, "h": 100},
                }
            ],
        )
        await fake_server.send_response(
            str(by_method["system.info"]["id"]),
            {
                "hostname": "test",
                "os": {"name": "macOS", "version": "1"},
                "addresses": [],
            },
        )
        await fake_server.send_response(
            str(by_method["apps.list"]["id"]),
            [{"name": "Safari", "bundle_id": "com.apple.Safari", "pid": 1}],
        )

        info, apps, windows = await asyncio.gather(system_task, apps_task, windows_task)
        assert isinstance(info, SystemInfo)
        assert isinstance(apps[0], ApplicationInfo)
        assert isinstance(windows[0], WindowInfo)
        assert windows[0].title == "Terminal"
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_missing_socket_is_reported_as_sdk_connection_error(
    tmp_path: Path,
) -> None:
    client = MacAPI(tmp_path / "missing.sock", auto_reconnect=False)
    with pytest.raises(ConnectionError):
        await client.connect()


@pytest.mark.asyncio
async def test_event_interleaves_with_rpc(fake_server: FakeMacAPIServer) -> None:
    client = await connected_client(fake_server)
    try:
        task = asyncio.create_task(client.system.info())
        request = await fake_server.wait_for_method("system.info")
        await fake_server.send_response(
            str(request["id"]),
            {
                "hostname": "test",
                "os": {"name": "macOS", "version": "1"},
                "addresses": [],
            },
        )
        await fake_server.send_event(
            "window.focused",
            {"window_id": 42, "title": "GitHub", "bundle_id": "com.apple.Safari"},
        )
        info = await task
        event = await asyncio.wait_for(client.events.__anext__(), 1)
        assert info.hostname == "test"
        assert isinstance(event, WindowFocusedEvent)
        assert event.data.window_id == 42
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_event_callback_handler_receives_typed_event(
    fake_server: FakeMacAPIServer,
) -> None:
    client = await connected_client(fake_server)
    received = asyncio.Event()
    events: list[WindowFocusedEvent] = []

    async def handler(event: MacEvent) -> None:
        if isinstance(event, WindowFocusedEvent):
            events.append(event)
            received.set()

    client.events.add_handler(handler)
    try:
        await fake_server.send_event(
            "window.focused",
            {"window_id": 42, "title": "GitHub", "bundle_id": "com.apple.Safari"},
        )
        await asyncio.wait_for(received.wait(), 1)
        assert events[0].data.window_id == 42
    finally:
        client.events.remove_handler(handler)
        await client.close()


@pytest.mark.asyncio
async def test_event_queue_drops_oldest_item_when_full(
    fake_server: FakeMacAPIServer,
) -> None:
    client = MacAPI(fake_server.path, auto_reconnect=False, event_queue_size=1)
    await client.connect()
    try:
        await fake_server.send_event("window.focused", {"window_id": 1}, seq=1)
        await fake_server.send_event("window.focused", {"window_id": 2}, seq=2)
        event = await asyncio.wait_for(client.events.__anext__(), 1)
        assert isinstance(event, WindowFocusedEvent)
        assert event.data.window_id == 2
        assert client.events.dropped_events == 1
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_subscription_is_restored_after_reconnect(
    fake_server: FakeMacAPIServer,
) -> None:
    client = MacAPI(
        fake_server.path,
        auto_reconnect=True,
        reconnect_min_delay=0.01,
        reconnect_max_delay=0.02,
    )
    await client.connect()
    try:
        subscribe_task = asyncio.create_task(client.events.subscribe(["window.*"]))
        request = await fake_server.wait_for_method("events.subscribe")
        await fake_server.send_response(
            str(request["id"]), [{"event": "window.*", "include_data": True}]
        )
        await subscribe_task

        await fake_server.close_client()
        reconnect_capabilities = await fake_server.wait_for_method(
            "system.capabilities", timeout=2
        )
        await fake_server.send_response(
            str(reconnect_capabilities["id"]),
            {
                "protocol_version": 1,
                "server_version": "test",
                "transport": "unix-domain-socket",
                "framing": "ndjson",
                "authentication": "none",
                "security": "filesystem-permissions",
                "single_client": True,
                "methods": [],
                "events": [],
                "features": {},
            },
        )
        restored = await fake_server.wait_for_method("events.subscribe", timeout=2)
        await fake_server.send_response(
            str(restored["id"]), [{"event": "window.*", "include_data": True}]
        )
        await asyncio.wait_for(client.wait_until_connected(), 2)
        assert client.connected
        assert client.events.subscriptions[0].event == "window.*"

        info_task = asyncio.create_task(client.system.info())
        info_request = await fake_server.wait_for_method("system.info", timeout=2)
        await fake_server.send_response(
            str(info_request["id"]),
            {
                "hostname": "reconnected",
                "os": {"name": "macOS", "version": "1"},
                "addresses": [],
            },
        )
        assert (await info_task).hostname == "reconnected"
        await fake_server.send_event(
            "window.focused", {"window_id": 7, "title": "after reconnect"}, seq=2
        )
        event = await asyncio.wait_for(client.events.__anext__(), 2)
        assert isinstance(event, WindowFocusedEvent)
        assert event.data.window_id == 7
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_disconnect_fails_pending_rpc(fake_server: FakeMacAPIServer) -> None:
    client = await connected_client(fake_server)
    try:
        task = asyncio.create_task(client.system.info())
        await fake_server.wait_for_method("system.info")
        await fake_server.close_client()
        with pytest.raises(ConnectionLostError):
            await asyncio.wait_for(task, 1)
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_timeout_removes_pending_rpc(fake_server: FakeMacAPIServer) -> None:
    client = await connected_client(fake_server)
    try:
        with pytest.raises(RPCTimeoutError):
            await client.call("system.info", result_type=SystemInfo, timeout=0.02)
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_malformed_line_does_not_disconnect_reader(
    fake_server: FakeMacAPIServer,
) -> None:
    client = await connected_client(fake_server)
    try:
        await fake_server.send_raw(b"not-json\n")
        task = asyncio.create_task(client.system.info())
        request = await fake_server.wait_for_method("system.info")
        await fake_server.send_response(
            str(request["id"]),
            {
                "hostname": "test",
                "os": {"name": "macOS", "version": "1"},
                "addresses": [],
            },
        )
        assert (await task).hostname == "test"
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_protocol_error_only_fails_correlated_rpc(
    fake_server: FakeMacAPIServer,
) -> None:
    client = await connected_client(fake_server)
    try:
        task = asyncio.create_task(client.system.info())
        request = await fake_server.wait_for_method("system.info")
        await fake_server.send_raw(
            (
                '{"v":1,"type":"protocol_error","id":"'
                + str(request["id"])
                + '","code":"PROTOCOL_ERROR","message":"bad request"}\n'
            ).encode()
        )
        with pytest.raises(ProtocolError):
            await task
        follow_up = asyncio.create_task(client.system.info())
        request = await fake_server.wait_for_method("system.info")
        await fake_server.send_response(
            str(request["id"]),
            {
                "hostname": "test",
                "os": {"name": "macOS", "version": "1"},
                "addresses": [],
            },
        )
        assert (await follow_up).hostname == "test"
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_event_iterator_terminates_when_auto_reconnect_is_disabled(
    fake_server: FakeMacAPIServer,
) -> None:
    client = await connected_client(fake_server)
    try:
        next_event = asyncio.create_task(client.events.__anext__())
        await asyncio.sleep(0)
        await fake_server.close_client()
        with pytest.raises(StopAsyncIteration):
            await asyncio.wait_for(next_event, 1)
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_cancelled_rpc_is_removed_from_pending_requests(
    fake_server: FakeMacAPIServer,
) -> None:
    client = await connected_client(fake_server)
    try:
        task = asyncio.create_task(client.system.info())
        await fake_server.wait_for_method("system.info")
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert client.pending_requests == 0
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_event_mutations_use_void_results(fake_server: FakeMacAPIServer) -> None:
    client = await connected_client(fake_server)
    try:
        unsubscribe_task = asyncio.create_task(client.events.unsubscribe(["window.*"]))
        request = await fake_server.wait_for_method("events.unsubscribe")
        await fake_server.send_response(str(request["id"]), None)
        await unsubscribe_task

        clear_task = asyncio.create_task(client.events.unsubscribe_all())
        request = await fake_server.wait_for_method("events.unsubscribeAll")
        await fake_server.send_response(str(request["id"]), None)
        await clear_task
    finally:
        await client.close()
