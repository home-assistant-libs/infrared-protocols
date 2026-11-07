"""Coolix 24-bit words transmitted with inverted copies of each byte."""

from dataclasses import dataclass
from enum import IntEnum
from typing import Self, override

from . import Command
from ._climate_fields import decoded, selection, temperature_value
from ._timing import PulseTiming, Reader, bits, byte_bits, pack_bytes


class CoolixMode(IntEnum):
    """Coolix operating modes."""

    COOL = 0x0
    DRY = 0x4
    AUTO = 0x8
    HEAT = 0xC
    FAN_ONLY = 0xE4


class CoolixFanSpeed(IntEnum):
    """Coolix fan speeds."""

    AUTO = 0xB
    LOW = 0x9
    MEDIUM = 0x5
    HIGH = 0x3


@dataclass(frozen=True, kw_only=True)
class CoolixState:
    """Settings carried by a Coolix packet, using its native enums and units."""

    power: bool | None = None
    mode: CoolixMode | None = None
    temperature: float | None = None
    fan: CoolixFanSpeed | None = None
    swing_v: bool | None = None
    swing_h: bool | None = None
    is_fahrenheit: bool = False


_TIMING = PulseTiming(560, 560, 1680)


class CoolixCommand(Command):
    """One or two Coolix words; None omits the second frame."""

    def __init__(
        self, *, first: int, second: int | None = None, modulation: int = 38000
    ) -> None:
        """Initialize explicitly selected frames."""
        bits(first, 24)
        if second is not None:
            bits(second, 24)
        super().__init__(modulation=modulation)
        self.first, self.second = first, second

    @override
    def get_raw_timings(self) -> list[int]:
        """Encode each byte and its complement."""
        frames = [self.first] if self.second is None else [self.first, self.second]
        result: list[int] = []
        for value in frames:
            if result:
                result.append(-5600)
            wire = bytes(
                item for byte in value.to_bytes(3, "big") for item in (byte, byte ^ 255)
            )
            result.extend(
                [4480, -4480, *_TIMING.encode(byte_bits(wire, lsb=False)), 560]
            )
        return result

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Validate every complement and preserve both frames when present."""
        r = Reader(timings=timings)
        words: list[int] = []
        try:
            while True:
                r.expect(4480, -4480)
                wire = pack_bytes(r.read_bits(_TIMING, 48), lsb=False)
                if any(
                    a ^ b != 255 for a, b in zip(wire[::2], wire[1::2], strict=True)
                ):
                    return None
                words.append(int.from_bytes(wire[::2], "big"))
                r.expect(560)
                if len(timings) - r.pos <= 1:
                    break
                if len(words) == 2:
                    return None
                r.expect(-5600)
            r.end()
            return cls(first=words[0], second=words[1] if len(words) == 2 else None)
        except ValueError:
            return None

    @classmethod
    def climate(
        cls,
        *,
        mode: CoolixMode,
        temperature: int,
        fan: CoolixFanSpeed = CoolixFanSpeed.AUTO,
    ) -> Self:
        """Build an on-state; power off and swing use separate button commands."""
        temp = temperature_value(temperature, 17, 30)
        mode_code = selection(mode, _MODES)
        if mode in (CoolixMode.AUTO, CoolixMode.DRY):
            if fan != CoolixFanSpeed.AUTO:
                raise ValueError("automatic and dry modes require automatic fan")
            fan_code = 1
        else:
            fan_code = selection(fan, _FANS)
        temp_code = 14 if mode == CoolixMode.FAN_ONLY else _TEMPERATURES[temp]
        word = 0xB20F00 | fan_code << 12 | temp_code << 4 | mode_code
        return cls(first=word, second=word)

    @property
    def state(self) -> CoolixState | None:
        """Decode the last state packet; button commands carry no full state."""
        value = self.second if self.second is not None else self.first
        if value == 0xB27BE0:
            return CoolixState(power=False)
        if value & 0xFF0F03 != 0xB20F00:
            return None
        fan_code, temp_code = value >> 12 & 15, value >> 4 & 15
        mode_code = value & 12
        mode = (
            CoolixMode.FAN_ONLY
            if mode_code == 4 and temp_code == 14
            else decoded(mode_code, _MODES)
        )
        if (
            temp_code not in _TEMPERATURES
            and mode != CoolixMode.FAN_ONLY
            or fan_code not in (*_FANS.values(), 1)
        ):
            return None
        temperature = (
            None if mode == CoolixMode.FAN_ONLY else _TEMPERATURES.index(temp_code) + 17
        )
        fan = CoolixFanSpeed.AUTO if fan_code == 1 else decoded(fan_code, _FANS)
        return CoolixState(power=True, mode=mode, temperature=temperature, fan=fan)


_MODES = {
    CoolixMode.COOL: 0,
    CoolixMode.DRY: 4,
    CoolixMode.AUTO: 8,
    CoolixMode.HEAT: 12,
    CoolixMode.FAN_ONLY: 4,
}
_FANS = {
    CoolixFanSpeed.AUTO: 11,
    CoolixFanSpeed.LOW: 9,
    CoolixFanSpeed.MEDIUM: 5,
    CoolixFanSpeed.HIGH: 3,
}
_TEMPERATURES = (0, 1, 3, 2, 6, 7, 5, 4, 12, 13, 9, 8, 10, 11)
