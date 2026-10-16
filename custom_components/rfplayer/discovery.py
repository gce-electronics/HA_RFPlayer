"""RF device discovery event buffer."""

import time

from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent

DISCOVERY_DURATION = 500


class DiscoverySession:
    """Collect unknown RF events for one discovery window."""

    def __init__(self) -> None:
        """Create an inactive discovery session."""
        self._events: dict[str, RfDeviceEvent] | None = None
        self._deadline: float | None = None

    def start(self) -> None:
        """Begin buffering unknown-device events."""
        self._events = {}
        self._deadline = time.monotonic() + DISCOVERY_DURATION

    def capture(self, event: RfDeviceEvent, *, eligible: bool) -> bool:
        """Capture an eligible event and report whether it was intercepted."""
        if self._deadline is not None and time.monotonic() >= self._deadline:
            self._deadline = None

        if self._events is None or self._deadline is None or not eligible:
            return False

        self._events[event.device.canonical_id] = event
        return True

    def stop(self) -> list[RfDeviceEvent]:
        """Stop buffering and return captured events."""
        events = list((self._events or {}).values())
        self._events = None
        self._deadline = None
        return events
