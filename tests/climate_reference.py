"""Test-only Celsius and named-setting vocabulary used by the external fixtures."""

from dataclasses import dataclass
from enum import IntEnum, StrEnum


class ClimateMode(StrEnum):
    """Operating modes independent of their wire representation."""

    AUTO = "auto"
    COOL = "cool"
    HEAT = "heat"
    DRY = "dry"
    FAN_ONLY = "fan_only"


class ClimateFan(StrEnum):
    """Fan selections shared by climate families."""

    AUTO = "auto"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    QUIET = "quiet"
    MAXIMUM = "maximum"


@dataclass(frozen=True, kw_only=True)
class ClimateState:
    """State actually carried by a command; absent fields remain None."""

    power: bool | None = None
    mode: ClimateMode | None = None
    temperature: float | None = None
    fan: ClimateFan | IntEnum | None = None
    swing_v: bool | None = None
    swing_h: bool | None = None
