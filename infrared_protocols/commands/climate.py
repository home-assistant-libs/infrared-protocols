"""Decoded climate vocabulary; state temperatures are degrees Celsius.

Constructor units are protocol-specific and documented by each command. Native
This is an opt-in projection for the new state-packet families, not a replacement
for existing per-module IntEnum APIs. Integrations must select a remote model
and map its supported capabilities; protocols with toggles cannot be treated as
absolute state setters. Existing native APIs retain their wire-valued enums.
Native fan enums preserve levels that have no unambiguous common-speed equivalent.
"""

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
