import json
from typing import cast
from unittest.mock import Mock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, mock_restore_cache
from pytest_mock import MockerFixture

from custom_components.rfplayer.const import ATTR_EVENT_DATA, DOMAIN, RFPLAYER_CLIENT
from custom_components.rfplayer.device_profiles import _get_profile_registry
from custom_components.rfplayer.rfplayerlib import RfPlayerClient
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceId
from custom_components.rfplayer.rfplayerlib.protocol import RfPlayerEventData, RfplayerProtocol
from homeassistant.components.switch import STATE_ON
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_FRIENDLY_NAME,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_UNKNOWN,
    Platform,
)
from homeassistant.core import HomeAssistant, State
from tests.rfplayer.conftest import create_rfplayer_test_cfg, setup_rfplayer_test_cfg
from tests.rfplayer.constants import (
    CHACON_ADDRESS,
    CHACON_ID_STRING,
    CHACON_ON_EVENT_DATA,
    CHACON_SWITCH_DEVICE_INFO,
    CHACON_SWITCH_ENTITY_ID,
    CHACON_SWITCH_FRIENDLY_NAME,
    CHACON_UNIT_CODE,
)


@pytest.mark.asyncio
async def test_switch(serial_connection_mock: Mock, hass: HomeAssistant, test_protocol: RfplayerProtocol):
    tr = cast(Mock, test_protocol.transport)

    entry_data = create_rfplayer_test_cfg(
        devices={
            CHACON_ID_STRING: CHACON_SWITCH_DEVICE_INFO,
        }
    )

    mock_entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data=entry_data)

    mock_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()
    await hass.async_start()

    state = hass.states.get(CHACON_SWITCH_ENTITY_ID)
    assert state
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == CHACON_SWITCH_FRIENDLY_NAME

    await hass.services.async_call(
        Platform.SWITCH,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: CHACON_SWITCH_ENTITY_ID},
        blocking=True,
    )

    state = hass.states.get(CHACON_SWITCH_ENTITY_ID)
    assert state
    assert state.state == STATE_ON
    tr.write.assert_called_once_with(bytearray(f"ZIA++ON CHACON ID {CHACON_UNIT_CODE}\n\r".encode()))
    tr.write.reset_mock()

    await hass.services.async_call(
        Platform.SWITCH,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: CHACON_SWITCH_ENTITY_ID},
        blocking=True,
    )

    state = hass.states.get(CHACON_SWITCH_ENTITY_ID)
    assert state
    assert state.state == STATE_OFF
    tr.write.assert_called_once_with(bytearray(f"ZIA++OFF CHACON ID {CHACON_UNIT_CODE}\n\r".encode()))


@pytest.mark.asyncio
async def test_automatic_add(serial_connection_mock: Mock, hass: HomeAssistant, mocker: MockerFixture):
    await setup_rfplayer_test_cfg(hass, device="/dev/serial/by-id/usb-rfplayer-port0", automatic_add=True)

    # Force profile cause there is no first match for lighting devices for now
    mocker.patch.object(
        _get_profile_registry(True), "get_profile_name_from_event", return_value="X10|CHACON|KD101|BLYSS|FS20 Switch"
    )

    client = cast(RfPlayerClient, hass.data[DOMAIN][RFPLAYER_CLIENT])
    client.event_callback(
        RfDeviceEvent(
            device=RfDeviceId(protocol="CHACON", address=CHACON_ADDRESS),
            data=RfPlayerEventData(CHACON_ON_EVENT_DATA),
        )
    )

    await hass.async_block_till_done()

    state = hass.states.get(CHACON_SWITCH_ENTITY_ID)
    assert state
    assert state.state == STATE_ON
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == CHACON_SWITCH_FRIENDLY_NAME


@pytest.mark.asyncio
async def test_state_restore(serial_connection_mock: Mock, hass: HomeAssistant) -> None:
    mock_restore_cache(
        hass,
        [
            State(
                CHACON_SWITCH_ENTITY_ID,
                STATE_ON,
                attributes={ATTR_EVENT_DATA: json.dumps(CHACON_ON_EVENT_DATA)},
            )
        ],
    )

    entry_data = create_rfplayer_test_cfg(
        devices={
            CHACON_ID_STRING: CHACON_SWITCH_DEVICE_INFO,
        }
    )
    mock_entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data=entry_data)

    mock_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(CHACON_SWITCH_ENTITY_ID)
    assert state
    assert state.state == STATE_ON
