import json
import logging
import os
from pathlib import Path

from pydantic import BaseModel, parse_obj_as

from homeassistant.const import Platform

_LOGGER = logging.getLogger(__name__)

FRAMES_PATH = Path(os.path.abspath(__file__)).parent / "frames"


class SensorTest(BaseModel):
    value: str
    unit: str | None = None


class ClimateTest(BaseModel):
    event_type: str
    state: str | None = None
    preset_mode: str | None = None


class StateTest(BaseModel):
    state: str


class GivenContext(BaseModel):
    event: dict
    profile_name: str | None = None


AnyTest = ClimateTest | SensorTest | StateTest


class PlatformTestMap(BaseModel):
    binary_sensor: dict[str, SensorTest] | None = None
    climate: dict[str, ClimateTest] | None = None
    cover: dict[str, StateTest] | None = None
    light: dict[str, StateTest] | None = None
    sensor: dict[str, SensorTest] | None = None
    switch: dict[str, StateTest] | None = None

    def get(self, platform: Platform) -> dict[str, AnyTest]:
        """Return a dictionary of tests for the given platform."""
        return vars(self).get(platform, {})


class FrameExpectation(BaseModel):
    given: GivenContext
    then: PlatformTestMap


def _load_expectations(platform: Platform) -> list[tuple[str, FrameExpectation]]:
    result = []
    for filename in FRAMES_PATH.glob("*.json"):
        with open(filename, encoding="utf-8") as f:
            obj = json.load(f)
            try:
                expectations = parse_obj_as(list[FrameExpectation], obj)
            except Exception:
                _LOGGER.exception("Failed to load frame file %s", filename)
                raise
            result.extend([(filename.name, e) for e in expectations if e.then.get(platform)])
    return result


def pytest_generate_tests(metafunc):
    if "profile" in metafunc.fixturenames:
        if "binary_sensor_expectation" in metafunc.fixturenames:
            metafunc.parametrize(
                "profile,binary_sensor_expectation",
                _load_expectations(Platform.BINARY_SENSOR),
            )
        if "sensor_expectation" in metafunc.fixturenames:
            metafunc.parametrize("profile,sensor_expectation", _load_expectations(Platform.SENSOR))
        if "light_expectation" in metafunc.fixturenames:
            metafunc.parametrize("profile,light_expectation", _load_expectations(Platform.LIGHT))
        if "climate_expectation" in metafunc.fixturenames:
            metafunc.parametrize("profile,climate_expectation", _load_expectations(Platform.CLIMATE))
        if "cover_expectation" in metafunc.fixturenames:
            metafunc.parametrize("profile,cover_expectation", _load_expectations(Platform.COVER))
        if "switch_expectation" in metafunc.fixturenames:
            metafunc.parametrize("profile,switch_expectation", _load_expectations(Platform.SWITCH))
