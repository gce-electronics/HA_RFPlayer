from unittest.mock import Mock

import pytest

from custom_components.rfplayer.device_publishers import EdisioHandler
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceId
from custom_components.rfplayer.rfplayerlib.protocol import RfPlayerEventData
from homeassistant.core import Event, HomeAssistant
from tests.rfplayer.conftest import rfplayer_config_entry

EMITRBTN = {
    "frame": {
        "header": {
            "frameType": "0",
            "cluster": "0",
            "dataFlag": "1",
            "rfLevel": "-54",
            "floorNoise": "-94",
            "rfQuality": "10",
            "protocol": "16",
            "protocolMeaning": "EDISIO",
            "infoType": "15",
            "frequency": "868350",
        },
        "infos": {
            "subType": "3",
            "subTypeMeaning": "TOGGLE",
            "id": "2691240302",
            "qualifier": "4",
            "info": "7681",
            "infoMeaning": "EMITRBTN, 3.0V",
            "add0": "0",
            "add1": "1",
        },
    }
}


@pytest.mark.unit
def test_edisio_handler():
    """Test the EdisioHandler."""

    handler = EdisioHandler()

    # Create a mock event that matches the handler
    event = RfDeviceEvent(
        device=RfDeviceId(protocol="EDISIO", address="3514999432"),
        data=RfPlayerEventData(EMITRBTN),
    )

    assert handler.match(event) is True
    assert handler.get_event_type() == "rfplayer_edisio_event"
    event_data = handler.get_event_data(event)
    assert event_data["device_id"] == "3514999432"
    assert event_data["channel"] == "4"
    assert event_data["command"] == "TOGGLE"
    assert event_data["model"] == "EMITRBTN"
    assert event_data["battery"] == "3.0V"
    assert event_data["add0"] == "0"
    assert event_data["add1"] == "1"


@pytest.mark.integration
async def test_gateway_publisher(mock_serial_connection: Mock, hass: HomeAssistant):
    entry = await rfplayer_config_entry(
        hass,
    )
    events_received: list[Event] = []
    hass.bus.async_listen("rfplayer_edisio_event", events_received.append)

    client = entry.runtime_data.gateway.client
    client.event_callback(
        RfDeviceEvent(
            device=RfDeviceId(protocol="EDISIO", address="3514999432"),
            data=RfPlayerEventData(EMITRBTN),
        )
    )

    await hass.async_block_till_done()

    assert len(events_received) == 1
    event = events_received[0]
    assert event.data["device_id"] == "3514999432"
    assert event.data["channel"] == "4"
    assert event.data["command"] == "TOGGLE"
    assert event.data["model"] == "EMITRBTN"
    assert event.data["add0"] == "0"
    assert event.data["add1"] == "1"
