from dataclasses import dataclass
import json
from typing import Any
from unittest.mock import Mock

import pytest
from pytest_homeassistant_custom_component.common import mock_restore_cache
from pytest_mock import MockerFixture

from custom_components.rfplayer.const import ATTR_EVENT_DATA
from custom_components.rfplayer.device_profiles import _get_profile_registry
from custom_components.rfplayer.rfplayerlib.device import RfDeviceEvent, RfDeviceId
from custom_components.rfplayer.rfplayerlib.protocol import RfPlayerEventData
from homeassistant.components.climate.const import HVACMode
from homeassistant.components.light import STATE_ON
from homeassistant.const import STATE_CLOSED, STATE_OFF, STATE_OPEN, STATE_UNKNOWN, Platform
from homeassistant.core import HomeAssistant, State
from tests.rfplayer.conftest import assert_entity_state, rfplayer_config_entry
from tests.rfplayer.constants import (
    BLYSS_BINARY_SENSOR_MOTION_ENTITY_ID,
    BLYSS_BINARY_SENSOR_MOTION_FRIENDLY_NAME,
    BLYSS_BINARY_SENSOR_SMOKE_ENTITY_ID,
    BLYSS_BINARY_SENSOR_SMOKE_FRIENDLY_NAME,
    BLYSS_MOTION_DEVICE_INFO,
    BLYSS_MOTION_ID_STRING,
    BLYSS_SMOKE_DEVICE_INFO,
    BLYSS_SMOKE_ID_STRING,
    CHACON_ADDRESS,
    CHACON_ID_STRING,
    CHACON_LIGHT_DEVICE_INFO,
    CHACON_LIGHT_ENTITY_ID,
    CHACON_LIGHT_FRIENDLY_NAME,
    CHACON_ON_EVENT_DATA,
    CHACON_SWITCH_DEVICE_INFO,
    CHACON_SWITCH_ENTITY_ID,
    CHACON_SWITCH_FRIENDLY_NAME,
    JAMMING_BINARY_SENSOR_ENTITY_ID,
    JAMMING_BINARY_SENSOR_FRIENDLY_NAME,
    OREGON_ADDRESS,
    OREGON_BINARY_SENSOR_ENTITY_ID,
    OREGON_BINARY_SENSOR_FRIENDLY_NAME,
    OREGON_DEVICE_INFO,
    OREGON_EVENT_DATA,
    OREGON_ID_STRING,
    OREGON_RAIN_SENSOR_ENTITY_ID,
    OREGON_RAIN_SENSOR_FRIENDLY_NAME,
    OREGON_RAIN_SENSOR_STATE,
    OREGON_RFLEVEL_SENSOR_ENTITY_ID,
    OREGON_RFLEVEL_SENSOR_FRIENDLY_NAME,
    OREGON_RFLEVEL_SENSOR_STATE,
    RTS_DEVICE_INFO,
    RTS_DOWN_EVENT_DATA,
    RTS_ENTITY_ID,
    RTS_FRIENDLY_NAME,
    RTS_ID_STRING,
    RTS_X10_ADDRESS,
    X2D_ADDRESS,
    X2D_DEVICE_INFO,
    X2D_ENTITY_ID,
    X2D_FRIENDLY_NAME,
    X2D_ID_STRING,
    X2D_ON_EVENT_DATA,
)


@dataclass(frozen=True)
class PlatformEntity:
    entity_id: str
    friendly_name: str
    setup_state: str | HVACMode | None = None
    automatic_state: str | HVACMode | None = None
    restore_state: str | HVACMode | None = None


@dataclass(frozen=True)
class PlatformCase:
    platform: Platform
    devices: dict[str, dict[str, Any]]
    entities: tuple[PlatformEntity, ...]
    event: RfDeviceEvent
    profile_name: str | None = None


def rf_event(protocol: str, address: str, data: dict[str, Any]) -> RfDeviceEvent:
    return RfDeviceEvent(
        device=RfDeviceId(protocol=protocol, address=address),
        data=RfPlayerEventData(data),
    )


def assert_platform_states(hass: HomeAssistant, case: PlatformCase, state_attribute: str) -> None:
    for entity in case.entities:
        expected_state = getattr(entity, state_attribute)
        if expected_state is not None:
            assert_entity_state(hass, entity.entity_id, expected_state, entity.friendly_name)


PLATFORM_CASES = (
    PlatformCase(
        platform=Platform.BINARY_SENSOR,
        devices={
            OREGON_ID_STRING: OREGON_DEVICE_INFO,
            BLYSS_MOTION_ID_STRING: BLYSS_MOTION_DEVICE_INFO,
            BLYSS_SMOKE_ID_STRING: BLYSS_SMOKE_DEVICE_INFO,
        },
        entities=(
            PlatformEntity(
                JAMMING_BINARY_SENSOR_ENTITY_ID, JAMMING_BINARY_SENSOR_FRIENDLY_NAME, setup_state=STATE_UNKNOWN
            ),
            PlatformEntity(
                OREGON_BINARY_SENSOR_ENTITY_ID,
                OREGON_BINARY_SENSOR_FRIENDLY_NAME,
                setup_state=STATE_UNKNOWN,
                automatic_state=STATE_OFF,
                restore_state=STATE_OFF,
            ),
            PlatformEntity(
                BLYSS_BINARY_SENSOR_MOTION_ENTITY_ID,
                BLYSS_BINARY_SENSOR_MOTION_FRIENDLY_NAME,
                setup_state=STATE_UNKNOWN,
            ),
            PlatformEntity(
                BLYSS_BINARY_SENSOR_SMOKE_ENTITY_ID,
                BLYSS_BINARY_SENSOR_SMOKE_FRIENDLY_NAME,
                setup_state=STATE_UNKNOWN,
            ),
        ),
        event=rf_event("OREGON", OREGON_ADDRESS, OREGON_EVENT_DATA),
    ),
    PlatformCase(
        platform=Platform.SENSOR,
        devices={OREGON_ID_STRING: OREGON_DEVICE_INFO},
        entities=(
            PlatformEntity(
                OREGON_RAIN_SENSOR_ENTITY_ID,
                OREGON_RAIN_SENSOR_FRIENDLY_NAME,
                setup_state=STATE_UNKNOWN,
                automatic_state=OREGON_RAIN_SENSOR_STATE,
                restore_state=OREGON_RAIN_SENSOR_STATE,
            ),
            PlatformEntity(
                OREGON_RFLEVEL_SENSOR_ENTITY_ID,
                OREGON_RFLEVEL_SENSOR_FRIENDLY_NAME,
                automatic_state=OREGON_RFLEVEL_SENSOR_STATE,
            ),
        ),
        event=rf_event("OREGON", OREGON_ADDRESS, OREGON_EVENT_DATA),
    ),
    PlatformCase(
        platform=Platform.LIGHT,
        devices={CHACON_ID_STRING: CHACON_LIGHT_DEVICE_INFO},
        entities=(
            PlatformEntity(
                CHACON_LIGHT_ENTITY_ID,
                CHACON_LIGHT_FRIENDLY_NAME,
                setup_state=STATE_UNKNOWN,
                automatic_state=STATE_ON,
                restore_state=STATE_ON,
            ),
        ),
        event=rf_event("CHACON", CHACON_ADDRESS, CHACON_ON_EVENT_DATA),
        profile_name="X10|CHACON|KD101|BLYSS|FS20 Lighting",
    ),
    PlatformCase(
        platform=Platform.SWITCH,
        devices={CHACON_ID_STRING: CHACON_SWITCH_DEVICE_INFO},
        entities=(
            PlatformEntity(
                CHACON_SWITCH_ENTITY_ID,
                CHACON_SWITCH_FRIENDLY_NAME,
                setup_state=STATE_UNKNOWN,
                automatic_state=STATE_ON,
                restore_state=STATE_ON,
            ),
        ),
        event=rf_event("CHACON", CHACON_ADDRESS, CHACON_ON_EVENT_DATA),
        profile_name="X10|CHACON|KD101|BLYSS|FS20 Switch",
    ),
    PlatformCase(
        platform=Platform.COVER,
        devices={RTS_ID_STRING: RTS_DEVICE_INFO},
        entities=(
            PlatformEntity(
                RTS_ENTITY_ID,
                RTS_FRIENDLY_NAME,
                setup_state=STATE_OPEN,
                automatic_state=STATE_CLOSED,
                restore_state=STATE_CLOSED,
            ),
        ),
        event=rf_event("RTS", RTS_X10_ADDRESS, RTS_DOWN_EVENT_DATA),
    ),
    PlatformCase(
        platform=Platform.CLIMATE,
        devices={X2D_ID_STRING: X2D_DEVICE_INFO},
        entities=(
            PlatformEntity(
                X2D_ENTITY_ID,
                X2D_FRIENDLY_NAME,
                setup_state=HVACMode.HEAT,
                automatic_state=HVACMode.HEAT,
                restore_state=HVACMode.HEAT,
            ),
        ),
        event=rf_event("X2D", X2D_ADDRESS, X2D_ON_EVENT_DATA),
    ),
)


pytestmark = pytest.mark.integration


@pytest.mark.integration
@pytest.mark.parametrize("case", PLATFORM_CASES, ids=lambda case: case.platform.value)
async def test_platform_setup(mock_serial_connection: Mock, hass: HomeAssistant, case: PlatformCase):
    await rfplayer_config_entry(hass, devices=case.devices)

    assert_platform_states(hass, case, "setup_state")


@pytest.mark.integration
@pytest.mark.parametrize("case", PLATFORM_CASES, ids=lambda case: case.platform.value)
async def test_platform_automatic_add(
    mock_serial_connection: Mock, hass: HomeAssistant, mocker: MockerFixture, case: PlatformCase
):
    entry = await rfplayer_config_entry(hass, automatic_add=True)

    if case.profile_name:
        mocker.patch.object(_get_profile_registry(True), "get_profile_name_from_event", return_value=case.profile_name)

    entry.runtime_data.gateway.client.event_callback(case.event)
    await hass.async_block_till_done()

    assert_platform_states(hass, case, "automatic_state")


@pytest.mark.integration
@pytest.mark.parametrize("case", PLATFORM_CASES, ids=lambda case: case.platform.value)
async def test_platform_state_restore(mock_serial_connection: Mock, hass: HomeAssistant, case: PlatformCase):
    mock_restore_cache(
        hass,
        [
            State(entity.entity_id, entity.restore_state, attributes={ATTR_EVENT_DATA: json.dumps(case.event.data)})
            for entity in case.entities
            if entity.restore_state is not None
        ],
    )

    await rfplayer_config_entry(hass, devices=case.devices)

    assert_platform_states(hass, case, "restore_state")
