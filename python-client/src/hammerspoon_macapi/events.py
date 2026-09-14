"""Typed event payloads and forward-compatible event dispatch."""

from __future__ import annotations

from typing import Literal, cast

from pydantic import Field, ValidationError

from .models import Frame, Model
from .protocol import JSONObject, RawEvent


class EventBase[EventName: str](Model):
    """Shared envelope fields present on every parsed event."""

    v: Literal[1]
    type: Literal["event"]
    seq: int
    event: EventName
    timestamp: float


class ApplicationData(Model):
    """Common application identity fields carried by application events."""

    bundle_id: str | None = None
    name: str
    pid: int | None = None


class ApplicationTerminatedData(ApplicationData):
    """Application identity for a termination notification."""

    pass


class ApplicationHiddenData(ApplicationData):
    """Application identity for a hidden notification."""

    pass


class ApplicationUnhiddenData(ApplicationData):
    """Application identity for an unhidden notification."""

    pass


class WindowData(Model):
    """Window identity and optional frame data carried by window events."""

    window_id: int
    title: str | None = None
    bundle_id: str | None = None
    frame: Frame | None = None


class WindowStateData(WindowData):
    """Window data with a boolean state-change value."""

    enabled: bool | None = None


class ScreenData(Model):
    """Screen identity used by topology events."""

    screen_id: str
    uuid: str | None = None
    name: str | None = None


def _empty_screen_summaries() -> list[dict[str, object]]:
    return []


class ScreenChangedData(Model):
    """Screen summary list used by topology snapshots."""

    screens: list[dict[str, object]] = Field(default_factory=_empty_screen_summaries)


class SystemEventData(Model):
    """Optional reason associated with a power or session event."""

    reason: str | None = None


class ClipboardChangedData(Model):
    """Optional text snapshot carried by clipboard notifications."""

    text: str | None = None


class WifiChangedData(Model):
    """Interface and SSID values carried by Wi-Fi notifications."""

    interface: str | None = None
    ssid: str | None = None


class AudioChangedData(Model):
    """Optional low-level audio event identifier."""

    event: str | None = None


class PowerSourceChangedData(Model):
    """Power-source name carried by a power-source event."""

    source: str | None = None


class PowerBatteryChangedData(Model):
    """Battery percentage and source carried by a battery event."""

    percentage: float | None = None
    source: str | None = None


class GenericEventData(Model):
    """Generic object payload for callers defining their own event schema."""

    data: JSONObject = Field(default_factory=dict)


class ApplicationActivatedEvent(EventBase[Literal["application.activated"]]):
    """Emitted when an application becomes active."""

    data: ApplicationData


class ApplicationLaunchedEvent(EventBase[Literal["application.launched"]]):
    """Emitted when an application launches."""

    data: ApplicationData


class ApplicationTerminatedEvent(EventBase[Literal["application.terminated"]]):
    """Emitted when an application terminates."""

    data: ApplicationTerminatedData


class ApplicationHiddenEvent(EventBase[Literal["application.hidden"]]):
    """Emitted when an application is hidden."""

    data: ApplicationHiddenData


class ApplicationUnhiddenEvent(EventBase[Literal["application.unhidden"]]):
    """Emitted when an application is unhidden."""

    data: ApplicationUnhiddenData


class WindowCreatedEvent(EventBase[Literal["window.created"]]):
    """Emitted when a window is created."""

    data: WindowData


class WindowDestroyedEvent(EventBase[Literal["window.destroyed"]]):
    """Emitted when a window is destroyed."""

    data: WindowData


class WindowFocusedEvent(EventBase[Literal["window.focused"]]):
    """Emitted when a window receives focus."""

    data: WindowData


class WindowMovedEvent(EventBase[Literal["window.moved"]]):
    """Emitted after a window moves, with short coalescing."""

    data: WindowData


class WindowResizedEvent(EventBase[Literal["window.resized"]]):
    """Emitted after a window's dimensions change."""

    data: WindowData


class WindowMinimizedEvent(EventBase[Literal["window.minimized"]]):
    """Emitted when a window is minimized."""

    data: WindowStateData


class WindowUnminimizedEvent(EventBase[Literal["window.unminimized"]]):
    """Emitted when a window is restored from minimized state."""

    data: WindowStateData


class WindowFullscreenChangedEvent(EventBase[Literal["window.fullscreenChanged"]]):
    """Emitted when a window enters or leaves fullscreen."""

    data: WindowStateData


class ScreenConnectedEvent(EventBase[Literal["screen.connected"]]):
    """Emitted when a display appears."""

    data: ScreenData


class ScreenDisconnectedEvent(EventBase[Literal["screen.disconnected"]]):
    """Emitted when a display disappears."""

    data: ScreenData


class ScreenChangedEvent(EventBase[Literal["screen.changed"]]):
    """Emitted with the complete display topology snapshot."""

    data: ScreenChangedData


class SystemEvent[EventName: str](EventBase[EventName]):
    """Base class for power and session event variants."""

    data: SystemEventData


class SystemWillSleepEvent(SystemEvent[Literal["system.willSleep"]]):
    """Emitted before system sleep."""

    pass


class SystemDidWakeEvent(SystemEvent[Literal["system.didWake"]]):
    """Emitted after system wake."""

    pass


class SystemScreensDidSleepEvent(SystemEvent[Literal["system.screensDidSleep"]]):
    """Emitted when displays sleep."""

    pass


class SystemScreensDidWakeEvent(SystemEvent[Literal["system.screensDidWake"]]):
    """Emitted when displays wake."""

    pass


class SystemSessionLockedEvent(SystemEvent[Literal["system.sessionLocked"]]):
    """Emitted when the session locks."""

    pass


class SystemSessionUnlockedEvent(SystemEvent[Literal["system.sessionUnlocked"]]):
    """Emitted when the session unlocks."""

    pass


class ClipboardChangedEvent(EventBase[Literal["clipboard.changed"]]):
    """Emitted when the text clipboard changes."""

    data: ClipboardChangedData


class WifiChangedEvent(EventBase[Literal["wifi.changed"]]):
    """Emitted when Wi-Fi SSID or link state changes."""

    data: WifiChangedData


class AudioOutputChangedEvent(EventBase[Literal["audio.outputChanged"]]):
    """Emitted when the default output device changes."""

    data: AudioChangedData


class AudioInputChangedEvent(EventBase[Literal["audio.inputChanged"]]):
    """Emitted when the default input device changes."""

    data: AudioChangedData


class AudioDeviceChangedEvent(EventBase[Literal["audio.deviceChanged"]]):
    """Emitted for another audio device-level change."""

    data: AudioChangedData


class AudioVolumeChangedEvent(EventBase[Literal["audio.volumeChanged"]]):
    """Emitted when a watched audio device volume changes."""

    data: AudioChangedData


class AudioMuteChangedEvent(EventBase[Literal["audio.muteChanged"]]):
    """Emitted when a watched audio device mute state changes."""

    data: AudioChangedData


class PowerSourceChangedEvent(EventBase[Literal["power.sourceChanged"]]):
    """Emitted when the active power source changes."""

    data: PowerSourceChangedData


class PowerBatteryChangedEvent(EventBase[Literal["power.batteryChanged"]]):
    """Emitted when battery percentage or source is reported."""

    data: PowerBatteryChangedData


class UnknownEvent(EventBase[str]):
    """Event preserved when the server name or payload is newer than the SDK."""

    data: JSONObject = Field(default_factory=dict)


type MacEvent = (
    ApplicationActivatedEvent
    | ApplicationLaunchedEvent
    | ApplicationTerminatedEvent
    | ApplicationHiddenEvent
    | ApplicationUnhiddenEvent
    | WindowCreatedEvent
    | WindowDestroyedEvent
    | WindowFocusedEvent
    | WindowMovedEvent
    | WindowResizedEvent
    | WindowMinimizedEvent
    | WindowUnminimizedEvent
    | WindowFullscreenChangedEvent
    | ScreenConnectedEvent
    | ScreenDisconnectedEvent
    | ScreenChangedEvent
    | SystemWillSleepEvent
    | SystemDidWakeEvent
    | SystemScreensDidSleepEvent
    | SystemScreensDidWakeEvent
    | SystemSessionLockedEvent
    | SystemSessionUnlockedEvent
    | ClipboardChangedEvent
    | WifiChangedEvent
    | AudioOutputChangedEvent
    | AudioInputChangedEvent
    | AudioDeviceChangedEvent
    | AudioVolumeChangedEvent
    | AudioMuteChangedEvent
    | PowerSourceChangedEvent
    | PowerBatteryChangedEvent
    | UnknownEvent
)


_EVENT_TYPES: dict[str, type[Model]] = {
    "application.activated": ApplicationActivatedEvent,
    "application.launched": ApplicationLaunchedEvent,
    "application.terminated": ApplicationTerminatedEvent,
    "application.hidden": ApplicationHiddenEvent,
    "application.unhidden": ApplicationUnhiddenEvent,
    "window.created": WindowCreatedEvent,
    "window.destroyed": WindowDestroyedEvent,
    "window.focused": WindowFocusedEvent,
    "window.moved": WindowMovedEvent,
    "window.resized": WindowResizedEvent,
    "window.minimized": WindowMinimizedEvent,
    "window.unminimized": WindowUnminimizedEvent,
    "window.fullscreenChanged": WindowFullscreenChangedEvent,
    "screen.connected": ScreenConnectedEvent,
    "screen.disconnected": ScreenDisconnectedEvent,
    "screen.changed": ScreenChangedEvent,
    "system.willSleep": SystemWillSleepEvent,
    "system.didWake": SystemDidWakeEvent,
    "system.screensDidSleep": SystemScreensDidSleepEvent,
    "system.screensDidWake": SystemScreensDidWakeEvent,
    "system.sessionLocked": SystemSessionLockedEvent,
    "system.sessionUnlocked": SystemSessionUnlockedEvent,
    "clipboard.changed": ClipboardChangedEvent,
    "wifi.changed": WifiChangedEvent,
    "audio.outputChanged": AudioOutputChangedEvent,
    "audio.inputChanged": AudioInputChangedEvent,
    "audio.deviceChanged": AudioDeviceChangedEvent,
    "audio.volumeChanged": AudioVolumeChangedEvent,
    "audio.muteChanged": AudioMuteChangedEvent,
    "power.sourceChanged": PowerSourceChangedEvent,
    "power.batteryChanged": PowerBatteryChangedEvent,
}


def parse_event(raw: RawEvent) -> MacEvent:
    """Convert a raw envelope to a typed event, falling back safely if needed."""
    payload = raw.model_dump(mode="json")
    event_type = _EVENT_TYPES.get(raw.event)
    if event_type is None:
        return UnknownEvent.model_validate(payload)
    try:
        return cast(MacEvent, event_type.model_validate(payload))
    except ValidationError:
        # Event schemas may grow independently of the SDK.  Preserve the
        # wire event instead of taking down the long-lived socket reader.
        return UnknownEvent.model_validate(payload)
