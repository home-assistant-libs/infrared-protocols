"""Private shared fields for Daikin ARC and BRC variants."""

from ._climate_fields import decoded, selection, temperature_value
from .climate import (
    ClimateFan,
    ClimateMode,
    ClimateState,
)

_MODES = {
    ClimateMode.AUTO: 0,
    ClimateMode.DRY: 2,
    ClimateMode.COOL: 3,
    ClimateMode.HEAT: 4,
    ClimateMode.FAN_ONLY: 6,
}
_FANS = {
    ClimateFan.AUTO: 10,
    ClimateFan.QUIET: 11,
    ClimateFan.LOW: 3,
    ClimateFan.MEDIUM: 5,
    ClimateFan.HIGH: 7,
}


def checked(packet: bytes) -> bytes:
    """Append the additive checksum to a Daikin section."""
    return packet + bytes([sum(packet) & 255])


def validate_sections(
    data: bytes, lengths: tuple[int, ...], signature: bytes = b"\x11\xda\x27\x00"
) -> None:
    """Validate each independent section's identity and checksum."""
    if len(data) != sum(lengths):
        raise ValueError("invalid Daikin packet length")
    offset = 0
    for length in lengths:
        section = data[offset : offset + length]
        if not section.startswith(signature) or sum(section[:-1]) & 255 != section[-1]:
            raise ValueError("invalid Daikin section signature or checksum")
        offset += length


def state_packet(
    *,
    mode: ClimateMode,
    temperature: float,
    power: bool,
    fan: ClimateFan,
    swing_v: bool,
    swing_h: bool,
) -> bytearray:
    """Build common state fields, before variant-specific bytes and checksum."""
    selection(mode, _MODES)
    temperature_value(temperature, 10, 30, 0.5)
    effective_temp = (
        0xC0
        if power and mode == ClimateMode.DRY
        else 0x32
        if power and mode == ClimateMode.FAN_ONLY
        else int(temperature * 2)
    )
    return bytearray(
        [
            0x11,
            0xDA,
            0x27,
            0,
            0,
            selection(mode, _MODES) << 4 | 1 if power else 0,
            effective_temp,
            0,
            selection(fan, _FANS) << 4 | (15 if swing_v else 0),
            15 if swing_h else 0,
            0,
            6,
            0x60,
            0,
            0,
            0xC0,
            0,
            0,
        ]
    )


def parse_state(data: bytes) -> ClimateState:
    """Extract common state without reporting sentinel temperatures as set points."""
    power = bool(data[5] & 1)
    mode = decoded(data[5] >> 4, _MODES) if power else None
    temperature = (
        None if data[6] == 0xC0 or mode == ClimateMode.FAN_ONLY else data[6] / 2
    )
    if temperature is not None:
        temperature_value(temperature, 10, 30, 0.5)
    fan_code = {4: 3, 6: 7}.get(data[8] >> 4, data[8] >> 4)
    return ClimateState(
        power=bool(data[5] & 1),
        mode=mode,
        temperature=temperature,
        fan=decoded(fan_code, _FANS),
        swing_v=bool(data[8] & 15),
        swing_h=bool(data[9] & 15),
    )
