"""Tests for entity."""

from __future__ import annotations

from custom_components.rfplayer.entity import RfDeviceEntity
from custom_components.rfplayer.rfplayerlib.device import RfDeviceId


def test_unique_id_normalization() -> None:
    """Test that unique_id follows Home Assistant 2026.2+ requirements."""
    device = RfDeviceId(protocol="BLYSS", address="4261483730")
    entity = RfDeviceEntity(
        device_id=device,
        profile_name="Motion Detector",
        event_data=None,
        verbose=False,
    )

    unique_id = entity.unique_id

    # Home Assistant 2026.2+ requirements:
    # 1. Must be lowercase
    assert unique_id
    assert unique_id == unique_id.lower(), "unique_id must be lowercase"

    # 2. Must not contain uppercase letters
    assert not any(c.isupper() for c in unique_id), "unique_id must not contain uppercase letters"

    # 3. Should use safe separator (underscore) - no hyphens
    assert "-" not in unique_id, "unique_id must not contain hyphens"

    # 4. Must be a valid string
    assert isinstance(unique_id, str), "unique_id must be a string"
    assert len(unique_id) > 0, "unique_id must not be empty"
