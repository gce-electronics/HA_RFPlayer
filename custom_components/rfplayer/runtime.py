"""Runtime data for an RFPlayer config entry."""

from dataclasses import dataclass

from custom_components.rfplayer.gateway import Gateway
from homeassistant.config_entries import ConfigEntry

type RfPlayerConfigEntry = ConfigEntry[RfPlayerRuntimeData]


@dataclass(slots=True)
class RfPlayerRuntimeData:
    """Runtime data for an RFPlayer config entry."""

    gateway: Gateway
