"""Bus publisher to send events to components outside the RFPlayer integration."""

from abc import ABC, abstractmethod

from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent
from homeassistant.core import HomeAssistant


class DeviceHandler(ABC):
    """Class responsible for converting protocol events to HA publishable events."""

    @abstractmethod
    def match(self, event: RfDeviceEvent) -> bool:
        """Determine if the handler can process the given event."""
        raise NotImplementedError

    @abstractmethod
    def get_event_type(self) -> str:
        """Return the HA event type to fire."""
        raise NotImplementedError

    @abstractmethod
    def get_event_data(self, event: RfDeviceEvent) -> dict:
        """Return the event data to include in the HA event."""
        raise NotImplementedError


class BusPublisher:
    """Class responsible for firing events to the HA bus."""

    def __init__(self) -> None:
        """Initialize the EventDispatcher."""
        self._handlers: list[DeviceHandler] = []

    def register_handler(self, handler: DeviceHandler) -> None:
        """Register a handler for a specific event type."""
        self._handlers.append(handler)

    async def async_fire(self, hass: HomeAssistant, event: RfDeviceEvent):
        """Dispatch an event to the appropriate handlers."""
        for handler in self._handlers:
            if handler.match(event):
                hass.bus.async_fire(handler.get_event_type(), handler.get_event_data(event))
