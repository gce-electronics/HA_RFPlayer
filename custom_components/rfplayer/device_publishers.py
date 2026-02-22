"""List of device publishers for RFPlayer events."""

import functools

from custom_components.rfplayer.bus_publisher import BusPublisher, DeviceHandler
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent


class EdisioHandler(DeviceHandler):
    """Handler for Edisio devices."""

    def match(self, event: RfDeviceEvent) -> bool:
        """Determine if the handler can process the given event."""
        return event.device.protocol == "EDISIO" and event.data["frame"]["header"]["infoType"] == "15"

    def get_event_type(self) -> str:
        """Return the HA event type to fire."""
        return "rfplayer_edisio_event"

    def get_event_data(self, event: RfDeviceEvent) -> dict:
        """Return the event data to include in the HA event."""
        (model, battery) = event.data["frame"]["infos"]["infoMeaning"].split(",")
        return {
            "device_id": event.device.address,
            "channel": event.data["frame"]["infos"]["qualifier"],
            "command": event.data["frame"]["infos"]["subTypeMeaning"],
            "model": model.strip(),
            "battery": battery.strip(),
            "add0": event.data["frame"]["infos"]["add0"],
            "add1": event.data["frame"]["infos"]["add1"],
        }


@functools.lru_cache(maxsize=1)
def get_bus_publisher() -> BusPublisher:
    """Get the singleton instance of the BusPublisher."""
    publisher = BusPublisher()
    publisher.register_handler(EdisioHandler())
    return publisher
