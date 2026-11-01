"""Daikin 280-bit full-state commands, including comfort and preset frames."""

from enum import StrEnum

from ._climate import ClimatePacket, FramePart
from ._timing import PulseTiming
from .climate import (
    ClimateFan,
    ClimateMode,
    ClimateState,
    decoded,
    selection,
    temperature_value,
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


class DaikinPreset(StrEnum):
    """Mutually exclusive remote presets."""

    NONE = "none"
    POWERFUL = "powerful"
    QUIET = "quiet"
    ECONO = "econo"
    SENSOR = "sensor"
    COMFORT = "comfort"


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
    temperature_value(temperature, 10, 30, 0.5)
    effective_temp = (
        0xC0
        if mode == ClimateMode.DRY
        else 0x32
        if mode == ClimateMode.FAN_ONLY
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
    mode = decoded(data[5] >> 4, _MODES)
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


class DaikinCommand(ClimatePacket):
    """Three-section Daikin climate state."""

    HEADER = (3360, -1760)
    TIMING = PulseTiming(520, 360, 1370)
    LENGTH = 35
    PARTS = (
        FramePart(8, HEADER, 32300),
        FramePart(8, HEADER, 32300),
        FramePart(19, HEADER),
    )

    def __init__(
        self,
        *,
        mode: ClimateMode,
        temperature: float,
        power: bool = True,
        fan: ClimateFan = ClimateFan.AUTO,
        swing_v: bool = False,
        swing_h: bool = False,
        preset: DaikinPreset = DaikinPreset.NONE,
    ) -> None:
        """Build a 10..30 °C state in half degrees."""
        preset = DaikinPreset(preset)
        state = state_packet(
            mode=mode,
            temperature=temperature,
            power=power,
            fan=fan,
            swing_v=swing_v,
            swing_h=swing_h,
        )
        state[13] = {DaikinPreset.POWERFUL: 1, DaikinPreset.QUIET: 32}.get(preset, 0)
        state[16] = {DaikinPreset.ECONO: 4, DaikinPreset.SENSOR: 2}.get(preset, 0)
        first = checked(
            bytes(
                [
                    0x11,
                    0xDA,
                    0x27,
                    0,
                    0xC5,
                    0,
                    16 if preset == DaikinPreset.COMFORT else 0,
                ]
            )
        )
        second = checked(bytes([0x11, 0xDA, 0x27, 0, 0x42, 0x49, 5]))
        super().__init__(data=first + second + checked(bytes(state)))

    @property
    def preset(self) -> DaikinPreset:
        """Return the active preset across comfort and state sections."""
        for active, preset in (
            (self.data[29] & 1, DaikinPreset.POWERFUL),
            (self.data[29] & 32, DaikinPreset.QUIET),
            (self.data[32] & 4, DaikinPreset.ECONO),
            (self.data[32] & 2, DaikinPreset.SENSOR),
            (self.data[6] & 16, DaikinPreset.COMFORT),
        ):
            if active:
                return preset
        return DaikinPreset.NONE

    @classmethod
    def parse(cls, data: bytes) -> ClimateState:
        """Validate all three sections before exposing the state."""
        validate_sections(data, (8, 8, 19))
        if data[4] != 0xC5 or data[12] != 0x42 or data[20] != 0:
            raise ValueError("unexpected Daikin frame type")
        return parse_state(data[16:])
