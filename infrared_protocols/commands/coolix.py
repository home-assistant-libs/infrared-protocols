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
    """Three-bit fan codes, separate from the adjacent sensor temperature."""

    AUTO = 0x5
    AUTO_ALT = 0x0
    ZONE_FOLLOW = 0x6
    FIXED = 0x7
    LOW = 0x4
    MEDIUM = 0x2
    HIGH = 0x1


@dataclass(frozen=True, kw_only=True)
class CoolixState:
    """Settings carried by a Coolix packet, using its native enums and units."""

    power: bool | None = None
    mode: CoolixMode | None = None
    temperature: int | None = None
    fan: CoolixFanSpeed | None = None
    sensor_temperature: int | None = None
    zone_follow: bool | None = None


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
        temperature: int | None = None,
        fan: CoolixFanSpeed | None = None,
        sensor_temperature: int | None = None,
        zone_follow: bool = False,
    ) -> Self:
        """Build an on-state; power off and swing use separate button commands."""
        temp = None if temperature is None else temperature_value(temperature, 17, 30)
        if mode == CoolixMode.FAN_ONLY:
            temp = 0
        if temp is None:
            raise ValueError("temperature is required for this mode")
        mode_code = selection(mode, _MODES)
        if fan is None:
            fan = (
                CoolixFanSpeed.AUTO_ALT
                if mode in (CoolixMode.AUTO, CoolixMode.DRY)
                else CoolixFanSpeed.AUTO
            )
        auto = mode in (CoolixMode.AUTO, CoolixMode.DRY)
        if auto and fan == CoolixFanSpeed.AUTO:
            raise ValueError("auto and dry modes require AUTO_ALT instead of AUTO")
        if not auto and fan == CoolixFanSpeed.AUTO_ALT:
            raise ValueError("AUTO_ALT fan is only available in auto and dry modes")
        fan_code = int(CoolixFanSpeed(fan))
        temp_code = 14 if mode == CoolixMode.FAN_ONLY else _TEMPERATURES[temp]
        sensor = (
            31
            if sensor_temperature is None
            else temperature_value(sensor_temperature, 0, 30)
        )
        word = 0xB20000 | fan_code << 13 | sensor << 8 | temp_code << 4 | mode_code
        if zone_follow:
            word |= 0x80002
        return cls(first=word, second=word)

    @property
    def state(self) -> CoolixState | None:
        """Decode the last state packet; button commands carry no full state."""
        value = self.second if self.second is not None else self.first
        if value == 0xB27BE0:
            return CoolixState(power=False)
        if value & 0xF70001 != 0xB20000 or bool(value & 2) != bool(value & 0x80000):
            return None
        fan_code, temp_code = value >> 13 & 7, value >> 4 & 15
        mode_code = value & 12
        mode = (
            CoolixMode.FAN_ONLY
            if mode_code == 4 and temp_code == 14
            else decoded(mode_code, _MODES)
        )
        if (
            temp_code not in _TEMPERATURES
            and mode != CoolixMode.FAN_ONLY
            or fan_code not in CoolixFanSpeed
        ):
            return None
        temperature = (
            None if mode == CoolixMode.FAN_ONLY else _TEMPERATURES.index(temp_code) + 17
        )
        fan = CoolixFanSpeed(fan_code)
        sensor = value >> 8 & 31
        return CoolixState(
            power=True,
            mode=mode,
            temperature=temperature,
            fan=fan,
            sensor_temperature=None if sensor == 31 else sensor,
            zone_follow=bool(value & 2),
        )


_MODES = {
    CoolixMode.COOL: 0,
    CoolixMode.DRY: 4,
    CoolixMode.AUTO: 8,
    CoolixMode.HEAT: 12,
    CoolixMode.FAN_ONLY: 4,
}
_TEMPERATURES = (0, 1, 3, 2, 6, 7, 5, 4, 12, 13, 9, 8, 10, 11)
