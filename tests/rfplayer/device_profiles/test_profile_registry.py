from custom_components.rfplayer.device_profiles import (
    AnyRfpPlatformConfig,
    ClimateEventTypes,
    RfpClimateConfig,
    RfpCoverConfig,
    RfpLightConfig,
    RfpSensorConfig,
    RfpSwitchConfig,
    _get_profile_registry,
)
from custom_components.rfplayer.rfplayerlib.protocol import RfPlayerEventData
from homeassistant.const import Platform
from tests.rfplayer.device_profiles.conftest import AnyTest, ClimateTest, FrameExpectation, SensorTest, StateTest


def _get_config(all_config: list[AnyRfpPlatformConfig], name: str) -> AnyRfpPlatformConfig:
    named_config = next((v for v in all_config if v.name == name), None)
    # Check that named entity exists
    assert named_config
    return named_config


REGISTRY = _get_profile_registry(verbose=True)


def _get_platform_tests(
    expectation: FrameExpectation, platform: Platform
) -> tuple[RfPlayerEventData, list[AnyRfpPlatformConfig], dict[str, AnyTest]]:
    given = expectation.given
    profile_name = given.profile_name or REGISTRY.get_profile_name_from_event(given.event)
    assert profile_name, f"Could not find a matching profile for event {given.event}"

    all_config = REGISTRY.get_platform_config(profile_name, platform)
    assert all_config, f"Could not find platform {platform} for profile {profile_name}"

    tests = expectation.then.get(platform)

    # same number of entities / platform
    assert len(all_config) == len(tests)

    return (given.event, all_config, tests)


def test_binary_sensor(profile: str, binary_sensor_expectation: FrameExpectation):
    """Test the binary sensors in the profile registry."""

    (event, all_config, tests) = _get_platform_tests(binary_sensor_expectation, Platform.BINARY_SENSOR)

    for name, test in tests.items():
        item = _get_config(all_config, name)

        assert isinstance(item, RfpSensorConfig)
        assert isinstance(test, SensorTest)
        assert item.state.get_value(event) == test.value, f"{name} value"


def test_sensor(profile: str, sensor_expectation: FrameExpectation):
    """Test the profile registry with an event."""

    (event, all_config, tests) = _get_platform_tests(sensor_expectation, Platform.SENSOR)

    for name, test in tests.items():
        item = _get_config(all_config, name)

        assert isinstance(item, RfpSensorConfig)
        assert isinstance(test, SensorTest)
        assert item.state.get_value(event) == test.value, f"{name} value"
        if item.state.unit_path:
            assert item.state.get_unit(event) == test.unit, f"{name} event unit"
        else:
            assert item.unit == test.unit, f"{name} default unit"


def test_light(profile: str, light_expectation: FrameExpectation):
    """Test the profile registry with an event."""

    (event, all_config, tests) = _get_platform_tests(light_expectation, Platform.LIGHT)

    for name, test in tests.items():
        item = _get_config(all_config, name)

        assert isinstance(item, RfpLightConfig)
        assert isinstance(test, StateTest)
        assert item.status.get_value(event) == test.state, f"{name} value"


def test_climate(profile: str, climate_expectation: FrameExpectation):
    """Test the profile registry with an event."""

    (event, all_config, tests) = _get_platform_tests(climate_expectation, Platform.CLIMATE)

    for name, test in tests.items():
        item = _get_config(all_config, name)

        assert isinstance(item, RfpClimateConfig)
        assert isinstance(test, ClimateTest)
        event_code = item.event_code.get_value(event) or "<missing>"
        event_type = item.event_types[event_code]
        assert str(event_type) == test.event_type, f"{name} value"
        if event_type in (ClimateEventTypes.STATE, ClimateEventTypes.ALL):
            assert test.state
            assert item.state.get_value(event) == test.state, f"{name} value"
        elif event_type in (ClimateEventTypes.PRESET_MODE, ClimateEventTypes.ALL):
            assert test.preset_mode
            preset_code = item.preset_mode.get_value(event) or "<missing>"
            preset_mode = item.preset_modes[preset_code]
            assert preset_mode == test.preset_mode, f"{name} value"
        else:
            raise ValueError("Invalid climate event type")


def test_cover(profile: str, cover_expectation: FrameExpectation):
    """Test the profile registry with an event."""

    (event, all_config, tests) = _get_platform_tests(cover_expectation, Platform.COVER)

    for name, test in tests.items():
        item = _get_config(all_config, name)

        assert isinstance(item, RfpCoverConfig)
        assert isinstance(test, StateTest)
        assert item.state
        assert item.state.get_value(event) == test.state, f"{name} value"


def test_switch(profile: str, switch_expectation: FrameExpectation):
    """Test the profile registry with an event."""

    (event, all_config, tests) = _get_platform_tests(switch_expectation, Platform.SWITCH)

    for name, test in tests.items():
        item = _get_config(all_config, name)

        assert isinstance(item, RfpSwitchConfig)
        assert isinstance(test, StateTest)
        assert item.status.get_value(event) == test.state, f"{name} value"


def test_is_valid_protocol():
    assert REGISTRY.is_valid_protocol("Oregon Temperature Sensor", "CHACON") is False
    assert REGISTRY.is_valid_protocol("Oregon Temperature Sensor", "OREGON") is True

    assert REGISTRY.is_valid_protocol("X10|CHACON|KD101|BLYSS|FS20 On/Off", "OREGON") is False
    assert REGISTRY.is_valid_protocol("X10|CHACON|KD101|BLYSS|FS20 On/Off", "CHACON") is True
