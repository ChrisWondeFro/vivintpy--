"""Tests for enum _missing_ handlers to boost coverage of vivintpy.enums."""
from __future__ import annotations

import pytest

from vivintpy.enums import (
    CapabilityCategoryType,
    CapabilityType,
    DeviceType,
    EquipmentType,
    FeatureType,
    SensorType,
    ZoneBypass,
)


@pytest.mark.parametrize(
    "enum_cls, bad_value, expected_member",
    [
        (DeviceType, "imaginary_device", DeviceType.UNKNOWN),
        (SensorType, 999, SensorType.UNKNOWN),
        (EquipmentType, 9999, EquipmentType.UNKNOWN),
        (CapabilityType, -123, CapabilityType.UNKNOWN),
        # FeatureType has a typo `UKNOWN`; ensure handler still works
        (FeatureType, "nonsense", FeatureType.UKNOWN),
        (CapabilityCategoryType, 42, CapabilityCategoryType.UNKNOWN),
        (ZoneBypass, 99, ZoneBypass.UNKNOWN),
    ],
)
def test_missing_enum_values(enum_cls, bad_value, expected_member):  # noqa: D401 – simple param test
    """All enums should map unknown values to their *_UNKNOWN members."""

    assert enum_cls(bad_value) is expected_member
