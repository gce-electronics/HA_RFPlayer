from unittest.mock import Mock

import pytest

from custom_components.rfplayer.bus_publisher import BusPublisher, DeviceHandler
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceId
from homeassistant.core import EventBus, HomeAssistant


@pytest.mark.asyncio
async def test_bus_publisher():
    """Test the BusPublisher."""

    hass = Mock(spec=HomeAssistant)
    hass.bus = Mock(spec=EventBus)
    matching_handler = Mock(spec=DeviceHandler)
    non_matching_handler = Mock(spec=DeviceHandler)

    publisher = BusPublisher()
    publisher.register_handler(matching_handler)
    publisher.register_handler(non_matching_handler)

    # Create a mock event
    event = RfDeviceEvent(device=RfDeviceId("protocol", "1"), data={"foo": "bar"})

    # Set up the handlers
    non_matching_handler.match.return_value = False
    matching_handler.match.return_value = True
    matching_handler.get_event_type.return_value = "test_event"
    matching_handler.get_event_data.return_value = {"data": "test"}

    # Publish the event
    await publisher.async_fire(hass, event)

    # Verify the correct handler was called and the event was fired
    non_matching_handler.match.assert_called_once_with(event)
    non_matching_handler.get_event_type.assert_not_called()
    non_matching_handler.get_event_data.assert_not_called()

    matching_handler.match.assert_called_once_with(event)
    matching_handler.get_event_type.assert_called_once()
    matching_handler.get_event_data.assert_called_once_with(event)

    hass.bus.async_fire.assert_called_once_with("test_event", {"data": "test"})
