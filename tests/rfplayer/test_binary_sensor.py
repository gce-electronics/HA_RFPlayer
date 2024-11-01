import json
from typing import cast
from unittest.mock import Mock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, mock_restore_cache

from custom_components.rfplayer.const import ATTR_EVENT_DATA, DOMAIN, RFPLAYER_CLIENT
from custom_components.rfplayer.rfplayerlib import RfPlayerClient
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceId
from custom_components.rfplayer.rfplayerlib.protocol import RfPlayerEventData
from homeassistant.const import ATTR_FRIENDLY_NAME, STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, State
from tests.rfplayer.conftest import create_rfplayer_test_cfg, setup_rfplayer_test_cfg
from tests.rfplayer.constants import (
    BLYSS_BINARY_SENSOR_MOTION_ENTITY_ID,
    BLYSS_BINARY_SENSOR_MOTION_FRIENDLY_NAME,
    BLYSS_BINARY_SENSOR_SMOKE_ENTITY_ID,
    BLYSS_BINARY_SENSOR_SMOKE_FRIENDLY_NAME,
    BLYSS_MOTION_DEVICE_INFO,
    BLYSS_MOTION_ID_STRING,
    BLYSS_SMOKE_DEVICE_INFO,
    BLYSS_SMOKE_ID_STRING,
    CHACON_ALL_ON_EVENT_DATA,
    CHACON_BINARY_SENSOR_DEVICE_INFO,
    CHACON_BINARY_SENSOR_ENTITY_ID,
    CHACON_BINARY_SENSOR_FRIENDLY_NAME,
    CHACON_GROUP_ADDRESS,
    CHACON_ID_STRING,
    JAMMING_BINARY_SENSOR_ENTITY_ID,
    JAMMING_BINARY_SENSOR_FRIENDLY_NAME,
    OREGON_ADDRESS,
    OREGON_BINARY_SENSOR_ENTITY_ID,
    OREGON_BINARY_SENSOR_FRIENDLY_NAME,
    OREGON_BINARY_SENSOR_STATE,
    OREGON_DEVICE_INFO,
    OREGON_EVENT_DATA,
    OREGON_ID_STRING,
)


@pytest.mark.asyncio
async def test_binary_sensor(serial_connection_mock: Mock, hass: HomeAssistant):
    entry_data = create_rfplayer_test_cfg(
        devices={
            OREGON_ID_STRING: OREGON_DEVICE_INFO,
            BLYSS_MOTION_ID_STRING: BLYSS_MOTION_DEVICE_INFO,
            BLYSS_SMOKE_ID_STRING: BLYSS_SMOKE_DEVICE_INFO,
        }
    )

    mock_entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data=entry_data)

    mock_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()
    await hass.async_start()

    state = hass.states.get(JAMMING_BINARY_SENSOR_ENTITY_ID)
    assert state
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == JAMMING_BINARY_SENSOR_FRIENDLY_NAME

    state = hass.states.get(OREGON_BINARY_SENSOR_ENTITY_ID)
    assert state
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == OREGON_BINARY_SENSOR_FRIENDLY_NAME

    state = hass.states.get(BLYSS_BINARY_SENSOR_MOTION_ENTITY_ID)
    assert state
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == BLYSS_BINARY_SENSOR_MOTION_FRIENDLY_NAME

    state = hass.states.get(BLYSS_BINARY_SENSOR_SMOKE_ENTITY_ID)
    assert state
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == BLYSS_BINARY_SENSOR_SMOKE_FRIENDLY_NAME


@pytest.mark.asyncio
async def test_automatic_add(serial_connection_mock: Mock, hass: HomeAssistant):
    await setup_rfplayer_test_cfg(hass, device="/dev/serial/by-id/usb-rfplayer-port0", automatic_add=True)

    client = cast(RfPlayerClient, hass.data[DOMAIN][RFPLAYER_CLIENT])
    client.event_callback(
        RfDeviceEvent(
            device=RfDeviceId(protocol="OREGON", address=OREGON_ADDRESS),
            data=RfPlayerEventData(OREGON_EVENT_DATA),
        )
    )

    await hass.async_block_till_done()

    state = hass.states.get(OREGON_BINARY_SENSOR_ENTITY_ID)
    assert state
    assert state.state == STATE_OFF
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == OREGON_BINARY_SENSOR_FRIENDLY_NAME


@pytest.mark.asyncio
async def test_group_command(serial_connection_mock: Mock, hass: HomeAssistant):
    entry_data = create_rfplayer_test_cfg(
        devices={
            CHACON_ID_STRING: CHACON_BINARY_SENSOR_DEVICE_INFO,
        }
    )

    mock_entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data=entry_data)

    mock_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()
    await hass.async_start()

    state = hass.states.get(CHACON_BINARY_SENSOR_ENTITY_ID)
    assert state
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == CHACON_BINARY_SENSOR_FRIENDLY_NAME

    client = cast(RfPlayerClient, hass.data[DOMAIN][RFPLAYER_CLIENT])
    client.event_callback(
        RfDeviceEvent(
            device=RfDeviceId(protocol="CHACON", address=CHACON_GROUP_ADDRESS),
            data=RfPlayerEventData(CHACON_ALL_ON_EVENT_DATA),
        )
    )

    await hass.async_block_till_done()

    state = hass.states.get(CHACON_BINARY_SENSOR_ENTITY_ID)
    assert state
    assert state.state == STATE_ON


@pytest.mark.asyncio
async def test_state_restore(serial_connection_mock: Mock, hass: HomeAssistant) -> None:
    """State restoration."""

    mock_restore_cache(
        hass,
        [
            State(
                OREGON_BINARY_SENSOR_ENTITY_ID,
                OREGON_BINARY_SENSOR_STATE,
                attributes={ATTR_EVENT_DATA: json.dumps(OREGON_EVENT_DATA)},
            )
        ],
    )

    entry_data = create_rfplayer_test_cfg(
        devices={
            OREGON_ID_STRING: OREGON_DEVICE_INFO,
        }
    )
    mock_entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data=entry_data)

    mock_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(OREGON_BINARY_SENSOR_ENTITY_ID)
    assert state
    assert state.state == OREGON_BINARY_SENSOR_STATE
