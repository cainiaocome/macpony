"""Pydantic response models and constrained literal types for the SDK."""

from __future__ import annotations

import base64
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    """Base response model; unknown fields are ignored for forward compatibility."""

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def _decode_empty_object_compatibility(cls, value: object) -> object:
        """Accept Lua JSON's legacy representation of an empty object.

        Hammerspoon's JSON encoder can emit an empty Lua table as ``[]``.
        Object-shaped API results and event payloads are normalized here so a
        client remains compatible with an older or partially upgraded server.
        """
        return {} if value == [] else value


class Frame(Model):
    """Window or screen rectangle in macOS points."""

    x: float
    y: float
    w: float
    h: float


class ApplicationInfo(Model):
    """Snapshot of a running application."""

    name: str
    bundle_id: str | None = None
    pid: int
    hidden: bool = False
    frontmost: bool = False


class WindowInfo(Model):
    """Snapshot of a macOS window and its owning application."""

    id: int
    title: str = ""
    app: str = ""
    bundle_id: str | None = None
    focused: bool = False
    visible: bool = True
    minimized: bool = False
    fullscreen: bool = False
    frame: Frame


class ScreenInfo(Model):
    """Connected display metadata and usable desktop frame."""

    id: str
    uuid: str | None = None
    name: str = ""
    primary: bool = False
    frame: Frame
    brightness: float | None = None


class AudioOutputInfo(Model):
    """Default output device name, volume, and mute state."""

    name: str
    volume: float | None = None
    muted: bool | None = None


class AudioInputInfo(Model):
    """Default input device name."""

    name: str


class AudioInfo(Model):
    """Combined default input and output device snapshot."""

    output: AudioOutputInfo | None = None
    input: AudioInputInfo | None = None


class OSInfo(Model):
    """Operating-system name and version pair."""

    name: str
    version: str


class SystemInfo(Model):
    """Host identity, operating system, and resolved host addresses."""

    hostname: str
    os: OSInfo
    addresses: list[str] = Field(default_factory=list)


class SystemStatus(Model):
    """Tracked session state and current power-source information."""

    locked: bool = False
    screensaver: bool = False
    sleeping: bool = False
    power_source: str | None = None
    battery_percent: float | None = None


class Capabilities(Model):
    """Server protocol, transport, method, event, and feature catalog."""

    protocol_version: int
    server_version: str
    transport: Literal["unix-domain-socket"]
    framing: Literal["ndjson"]
    authentication: Literal["none"]
    security: Literal["filesystem-permissions"]
    single_client: bool
    methods: list[str] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    features: dict[str, bool] = Field(default_factory=dict)


class ClipboardText(Model):
    """Text clipboard result; text may be absent or unavailable."""

    text: str | None = None


class NetworkInterface(Model):
    """BSD network interface name and its addresses."""

    name: str
    addresses: list[str] = Field(default_factory=list)


def _empty_interfaces() -> list[NetworkInterface]:
    return []


class NetworkInfo(Model):
    """Network interfaces plus current Wi-Fi summary."""

    interfaces: list[NetworkInterface] = Field(default_factory=_empty_interfaces)
    wifi: dict[str, object] | None = None


class InlineScreenshot(Model):
    """A PNG carried inline as base64 in the response envelope."""

    mode: Literal["inline"]
    mime: Literal["image/png"]
    encoding: Literal["base64"]
    width: int
    height: int
    content: str

    def decode(self) -> bytes:
        """Decode and validate the base64 PNG payload."""
        return base64.b64decode(self.content, validate=True)


class FileScreenshot(Model):
    """A PNG written to the Hammerspoon host's runtime directory."""

    mode: Literal["file"]
    mime: Literal["image/png"]
    path: str
    created_at: float


Screenshot = InlineScreenshot | FileScreenshot
ScreenshotMode = Literal["inline", "file"]
WindowPosition = Literal[
    "left-half",
    "right-half",
    "top-half",
    "bottom-half",
    "center",
    "maximize",
    "top-left",
    "top-right",
    "bottom-left",
    "bottom-right",
]
Modifier = Literal["cmd", "ctrl", "alt", "shift", "fn"]
MouseButton = Literal["left", "right", "middle"]
