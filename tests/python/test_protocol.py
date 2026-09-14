from __future__ import annotations

import json
from pathlib import Path

import pytest
from hammerspoon_macapi.events import (
    ClipboardChangedEvent,
    PowerBatteryChangedEvent,
    UnknownEvent,
    WifiChangedEvent,
    WindowFocusedEvent,
    parse_event,
)
from hammerspoon_macapi.exceptions import (
    ProtocolError,
    WindowNotFoundError,
    rpc_exception,
)
from hammerspoon_macapi.models import InlineScreenshot, SystemInfo
from hammerspoon_macapi.protocol import RawEvent, decode_message

FIXTURES = Path(__file__).parents[2] / "protocol-fixtures"


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_protocol_fixtures_parse_into_typed_models() -> None:
    message = decode_message(fixture("response-system-info.json"))
    assert message.type == "response"
    assert message.ok is True
    assert SystemInfo.model_validate(message.result).hostname == "Mac-Studio"

    event = decode_message(fixture("event-clipboard-changed.json"))
    assert isinstance(event, RawEvent)
    assert isinstance(parse_event(event), ClipboardChangedEvent)

    window_event = decode_message(fixture("event-window-focused.json"))
    assert isinstance(window_event, RawEvent)
    parsed_window_event = parse_event(window_event)
    assert isinstance(parsed_window_event, WindowFocusedEvent)
    assert parsed_window_event.data.window_id == 12345


def test_unknown_event_is_forward_compatible() -> None:
    raw = RawEvent.model_validate(
        {
            "v": 1,
            "type": "event",
            "seq": 99,
            "event": "future.newEvent",
            "timestamp": 123.0,
            "data": {"foo": "bar"},
        }
    )
    event = parse_event(raw)
    assert isinstance(event, UnknownEvent)
    assert event.event == "future.newEvent"
    assert event.data["foo"] == "bar"


def test_implemented_observation_events_are_typed() -> None:
    wifi = RawEvent.model_validate(
        {
            "v": 1,
            "type": "event",
            "seq": 1,
            "event": "wifi.changed",
            "timestamp": 1.0,
            "data": {"interface": "en0", "ssid": "test"},
        }
    )
    battery = RawEvent.model_validate(
        {
            "v": 1,
            "type": "event",
            "seq": 2,
            "event": "power.batteryChanged",
            "timestamp": 1.0,
            "data": {"percentage": 50, "source": "AC Power"},
        }
    )
    assert isinstance(parse_event(wifi), WifiChangedEvent)
    assert isinstance(parse_event(battery), PowerBatteryChangedEvent)


def test_screenshot_decodes_base64() -> None:
    screenshot = InlineScreenshot(
        mode="inline",
        mime="image/png",
        encoding="base64",
        width=1,
        height=1,
        content="aGVsbG8=",
    )
    assert screenshot.decode() == b"hello"


def test_rpc_error_mapping() -> None:
    error = rpc_exception("WINDOW_NOT_FOUND", "gone")
    assert isinstance(error, WindowNotFoundError)
    assert error.code == "WINDOW_NOT_FOUND"


def test_malformed_message_is_rejected() -> None:
    with pytest.raises(ProtocolError):
        decode_message(json.dumps({"type": "unknown"}))


def test_oversized_message_is_rejected() -> None:
    with pytest.raises(ProtocolError, match="maximum line size"):
        decode_message(b"{" + b"a" * (1024 * 1024) + b"}")
