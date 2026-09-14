# Events

## Subscribe

Subscriptions are server-side filters. A string uses the default
`include_data: true`:

```python
await mac.events.subscribe(["application.*", "window.*"])
```

For a privacy- or bandwidth-sensitive notification, suppress event data:

```python
await mac.events.subscribe([
    EventSubscription(event="clipboard.changed", include_data=False),
])
```

Patterns ending with `*` match their literal prefix. `include_data` is applied
to the first matching registry entry; avoid overlapping exact and wildcard
subscriptions when their policies differ. `EventsClient` remembers
successful subscriptions and restores them after reconnect.

## Event delivery policy

The Lua event bus:

1. checks whether any subscription matches;
2. replaces suppressed or empty object data with a valid JSON object;
3. coalesces high-frequency window/audio changes for 75 ms;
4. assigns a sequence number when the event is placed on the wire queue;
5. drops the oldest queued event when the bounded server queue is full.

The Python SDK has a separate bounded queue, default size 256. It also drops
the oldest item when full and increments `mac.events.dropped_events`. Event
callbacks run in independent asyncio tasks; an exception in one callback is
logged and does not stop the reader.

## Event catalog

All events have `v`, `type: "event"`, `seq`, `event`, `timestamp`, and `data`.
Known payload fields are listed below. A future event or an incompatible known
payload arrives as `UnknownEvent` in the Python SDK.

| Event | Data |
| --- | --- |
| `application.launched`, `application.terminated`, `application.activated`, `application.hidden`, `application.unhidden` | `name`, optional `bundle_id`, optional `pid` |
| `window.created`, `window.destroyed`, `window.focused`, `window.moved`, `window.resized` | `window_id`, optional `title`, `bundle_id`, `frame` |
| `window.minimized`, `window.unminimized`, `window.fullscreenChanged` | Window data plus `enabled` |
| `screen.connected`, `screen.disconnected` | `screen_id`, optional `uuid`, `name` |
| `screen.changed` | `screens` summary list |
| `system.willSleep`, `system.didWake`, `system.screensDidSleep`, `system.screensDidWake`, `system.sessionLocked`, `system.sessionUnlocked` | optional `reason` |
| `wifi.changed` | optional `interface`, `ssid` |
| `audio.outputChanged`, `audio.inputChanged`, `audio.volumeChanged`, `audio.muteChanged` | optional `event` |
| `audio.deviceChanged` | `event` |
| `clipboard.changed` | optional `text` |
| `power.sourceChanged` | optional `source` |
| `power.batteryChanged` | optional `percentage`, `source` |

## Async iteration and shutdown

```python
async for event in mac.events:
    handle(event)
```

`MacAPI.close()` wakes a blocked iterator with `StopAsyncIteration` after
canceling callback tasks. If automatic reconnect is disabled, an unexpected
peer disconnect has the same terminal behavior. With automatic reconnect
enabled, the iterator remains open while the connection retries.

## Callback consumption

```python
async def on_event(event: MacEvent) -> None:
    print(event.event)


mac.events.add_handler(on_event)
```

Remove handlers with `remove_handler`. Callback tasks are canceled during
client shutdown.
