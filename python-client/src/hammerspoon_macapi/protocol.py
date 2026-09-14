"""Version-1 NDJSON envelope models and wire validation helpers."""

from __future__ import annotations

import json
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from .constants import MAX_LINE_BYTES, PROTOCOL_VERSION
from .exceptions import ProtocolError

type JSONValue = None | bool | int | float | str | list[JSONValue] | dict[str, JSONValue]
type JSONObject = dict[str, JSONValue]


class ProtocolModel(BaseModel):
    """Base wire model that ignores fields added by newer peers."""

    model_config = ConfigDict(extra="ignore")


class RequestEnvelope(ProtocolModel):
    """Client-to-server RPC request envelope."""

    v: Literal[1] = PROTOCOL_VERSION
    id: str
    type: Literal["request"] = "request"
    method: str
    params: JSONObject = Field(default_factory=dict)


class ErrorInfo(ProtocolModel):
    """Application-level RPC error code and human-readable message."""

    code: str
    message: str


class ResponseEnvelope(ProtocolModel):
    """Server-to-client correlated RPC response envelope."""

    v: Literal[1]
    id: str
    type: Literal["response"]
    ok: bool
    result: JSONValue = None
    error: ErrorInfo | None = None


class RawEvent(ProtocolModel):
    """Unparsed server event envelope before typed event dispatch."""

    v: Literal[1]
    type: Literal["event"]
    seq: int
    event: str
    timestamp: float
    data: JSONObject = Field(default_factory=dict)


class ProtocolErrorEnvelope(ProtocolModel):
    """Non-RPC protocol error reported by the server."""

    v: Literal[1]
    type: Literal["protocol_error"]
    id: str | None = None
    code: str
    message: str


type WireMessage = ResponseEnvelope | RawEvent | ProtocolErrorEnvelope


def encode_line(message: BaseModel) -> bytes:
    """Serialize a Pydantic envelope as compact UTF-8 JSON plus newline."""
    payload = message.model_dump(mode="json", exclude_none=True)
    return json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n"


def decode_message(line: bytes | str) -> WireMessage:
    """Validate one server record without accepting unknown envelope types."""
    line_size = len(line) if isinstance(line, bytes) else len(line.encode("utf-8"))
    if line_size > MAX_LINE_BYTES:
        raise ProtocolError("protocol message exceeds maximum line size")
    try:
        payload: object = json.loads(line)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError(f"invalid JSON message: {exc}") from exc

    if not isinstance(payload, dict):
        raise ProtocolError("protocol message must be a JSON object")
    payload = cast(dict[str, object], payload)
    message_type = payload.get("type")
    try:
        if message_type == "response":
            return ResponseEnvelope.model_validate(payload)
        if message_type == "event":
            if payload.get("data") == []:
                payload["data"] = {}
            return RawEvent.model_validate(payload)
        if message_type == "protocol_error":
            return ProtocolErrorEnvelope.model_validate(payload)
    except ValueError as exc:
        raise ProtocolError(f"invalid {message_type!r} message: {exc}") from exc
    raise ProtocolError(f"unknown protocol message type: {message_type!r}")


def parse_result(raw: JSONValue, result_type: object) -> object:
    """Validate an RPC result against a Python type or Pydantic model."""
    try:
        return cast(object, TypeAdapter(result_type).validate_python(raw))
    except ValueError as exc:
        raise ProtocolError(f"invalid RPC result: {exc}") from exc
