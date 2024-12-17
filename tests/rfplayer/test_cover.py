import json
from typing import cast
from unittest.mock import Mock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, mock_restore_cache
from pytest_mock import MockerFixture

from custom_components.rfplayer.const import ATTR_EVENT_DATA, DOMAIN, RFPLAYER_CLIENT
from custom_components.rfplayer.rfplayerlib import RfPlayerClient
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceId
from custom_components.rfplayer.rfplayerlib.protocol import RfPlayerEventData, RfplayerProtocol
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_FRIENDLY_NAME,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    SERVICE_STOP_COVER,
    STATE_CLOSED,
    STATE_OPEN,
    Platform,
)
from homeassistant.core import HomeAssistant, State
from tests.rfplayer.conftest import create_rfplayer_test_cfg, setup_rfplayer_test_cfg
from tests.rfplayer.constants import (
    RTS_DEVICE_INFO,
    RTS_DOWN_EVENT_DATA,
    RTS_ENTITY_ID,
    RTS_FRIENDLY_NAME,
    RTS_ID_STRING,
    RTS_UNIT_CODE,
    RTS_X10_ADDRESS,
)


@pytest.mark.asyncio
async def test_cover(serial_connection_mock: Mock, hass: HomeAssistant, test_protocol: RfplayerProtocol):
    tr = cast(Mock, test_protocol.transport)

    entry_data = create_rfplayer_test_cfg(
        devices={
            RTS_ID_STRING: RTS_DEVICE_INFO,
        }
    )

    mock_entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data=entry_data)

    mock_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()
    await hass.async_start()

    state = hass.states.get(RTS_ENTITY_ID)
    assert state
    assert state.state == STATE_OPEN
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == RTS_FRIENDLY_NAME

    await hass.services.async_call(
        Platform.COVER,
        SERVICE_CLOSE_COVER,
        {ATTR_ENTITY_ID: RTS_ENTITY_ID},
        blocking=True,
    )

    state = hass.states.get(RTS_ENTITY_ID)
    assert state
    assert state.state == STATE_CLOSED
    tr.write.assert_called_once_with(f"ZIA++OFF RTS ID {RTS_UNIT_CODE} QUALIFIER 0\n\r".encode())
    tr.write.reset_mock()

    await hass.services.async_call(
        Platform.COVER,
        SERVICE_OPEN_COVER,
        {ATTR_ENTITY_ID: RTS_ENTITY_ID},
        blocking=True,
    )

    state = hass.states.get(RTS_ENTITY_ID)
    assert state
    assert state.state == STATE_OPEN
    tr.write.assert_called_once_with(f"ZIA++ON RTS ID {RTS_UNIT_CODE} QUALIFIER 0\n\r".encode())
    tr.write.reset_mock()

    await hass.services.async_call(
        Platform.COVER,
        SERVICE_STOP_COVER,
        {ATTR_ENTITY_ID: RTS_ENTITY_ID},
        blocking=True,
    )

    state = hass.states.get(RTS_ENTITY_ID)
    assert state
    assert state.state == STATE_OPEN
    tr.write.assert_called_once_with(f"ZIA++DIM RTS ID {RTS_UNIT_CODE} %4\n\r".encode())


@pytest.mark.asyncio
async def test_automatic_add(serial_connection_mock: Mock, hass: HomeAssistant, mocker: MockerFixture):
    await setup_rfplayer_test_cfg(hass, device="/dev/serial/by-id/usb-rfplayer-port0", automatic_add=True)

    client = cast(RfPlayerClient, hass.data[DOMAIN][RFPLAYER_CLIENT])
    client.event_callback(
        RfDeviceEvent(
            device=RfDeviceId(protocol="RTS", address=RTS_X10_ADDRESS),
            data=RfPlayerEventData(RTS_DOWN_EVENT_DATA),
        )
    )

    await hass.async_block_till_done()

    state = hass.states.get(RTS_ENTITY_ID)
    assert state
    assert state.state == STATE_CLOSED
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == RTS_FRIENDLY_NAME


@pytest.mark.asyncio
async def test_state_restore(serial_connection_mock: Mock, hass: HomeAssistant) -> None:
    """State restoration."""
    mock_restore_cache(
        hass,
        [
            State(
                RTS_ENTITY_ID,
                STATE_CLOSED,
                attributes={ATTR_EVENT_DATA: json.dumps(RTS_DOWN_EVENT_DATA)},
            )
        ],
    )

    entry_data = create_rfplayer_test_cfg(
        devices={
            RTS_ID_STRING: RTS_DEVICE_INFO,
        }
    )
    mock_entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data=entry_data)

    mock_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(RTS_ENTITY_ID)
    assert state
    assert state.state == STATE_CLOSED
