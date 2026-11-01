"""Shared vocabulary for climate commands; temperatures are degrees Celsius."""

from dataclasses import dataclass
from enum import StrEnum


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


@dataclass(frozen=True, kw_only=True)
class ClimateState:
    """State actually carried by a command; absent fields remain None."""

    power: bool | None = None
    mode: ClimateMode | None = None
    temperature: float | None = None
    fan: ClimateFan | None = None
    swing_v: bool | None = None
    swing_h: bool | None = None


def temperature_value(
    value: float, minimum: float, maximum: float, step: float = 1
) -> int:
    """Validate a temperature and return its offset in steps."""
    if not minimum <= value <= maximum or (value - minimum) % step:
        raise ValueError(f"temperature must be {minimum}..{maximum} in steps of {step}")
    return round((value - minimum) / step)


def selection[T](value: T, choices: dict[T, int]) -> int:
    """Look up a supported setting with a descriptive public error."""
    try:
        return choices[value]
    except KeyError:
        raise ValueError(f"unsupported setting: {value}") from None


def decoded[T](value: int, choices: dict[T, int]) -> T:
    """Look up a wire value, rejecting unknown encodings."""
    for key, candidate in choices.items():
        if candidate == value:
            return key
    raise ValueError(f"unknown wire value: {value}")
