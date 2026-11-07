"""Midea 48-bit packets followed by an inverted packet."""

from dataclasses import dataclass
from enum import IntEnum
from typing import Self, override

from . import Command
from ._climate_fields import temperature_value
from ._timing import PulseTiming, Reader, byte_bits, pack_bytes


class MideaMode(IntEnum):
    """Midea operating modes."""

    COOL = 0x0
    DRY = 0x1
    AUTO = 0x2
    HEAT = 0x3
    FAN_ONLY = 0x4


class MideaFanSpeed(IntEnum):
    """Midea fan speeds."""

    AUTO = 0x0
    LOW = 0x1
    MEDIUM = 0x2
    HIGH = 0x3


@dataclass(frozen=True, kw_only=True)
class MideaState:
    """Settings carried by a Midea packet, using its native enums and units."""

    power: bool | None = None
    mode: MideaMode | None = None
    temperature: int | None = None
    fan: MideaFanSpeed | None = None
    is_fahrenheit: bool = False
    sleep: bool = False


_TIMING = PulseTiming(560, 560, 1680)


def _reverse(byte: int) -> int:
    return int(f"{byte:08b}"[::-1], 2)


class MideaCommand(Command):
    """Five payload bytes with a reversed-byte additive checksum."""

    def __init__(self, *, data: bytes, modulation: int = 38000) -> None:
        """Initialize an immutable Midea payload, excluding its checksum."""
        if len(data) != 5:
            raise ValueError("Midea payload must be five bytes")
        super().__init__(modulation=modulation)
        self.data = bytes(data)

    @staticmethod
    def checksum(data: bytes) -> int:
        """Compute the reversed additive two's-complement checksum."""
        return _reverse(-sum(_reverse(byte) for byte in data) & 255)

    @override
    def get_raw_timings(self) -> list[int]:
        """Encode a payload and its inverted copy."""
        wire = self.data + bytes([self.checksum(self.data)])
        first = [4480, -4480, *_TIMING.encode(byte_bits(wire, lsb=False)), 560]
        second = [
            4480,
            -4480,
            *_TIMING.encode(byte_bits(bytes(byte ^ 255 for byte in wire), lsb=False)),
            560,
        ]
        return first + [-5600] + second

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Require a valid checksum and matching inverted packet."""
        r = Reader(timings=timings)
        try:
            r.expect(4480, -4480)
            wire = pack_bytes(r.read_bits(_TIMING, 48), lsb=False)
            r.expect(560, -5600, 4480, -4480)
            inverse = pack_bytes(r.read_bits(_TIMING, 48), lsb=False)
            r.expect(560)
            r.end()
            if (
                cls.checksum(wire[:-1]) != wire[-1]
                or bytes(b ^ 255 for b in wire) != inverse
            ):
                return None
            return cls(data=wire[:-1])
        except ValueError:
            return None

    @classmethod
    def climate(
        cls,
        *,
        mode: MideaMode | None,
        temperature: int | None = None,
        power: bool = True,
        fan: MideaFanSpeed = MideaFanSpeed.AUTO,
        sleep: bool = False,
        is_fahrenheit: bool = False,
    ) -> Self:
        """Build a control packet; temperature is 17..30 °C or 62..86 °F."""
        temp = (
            None
            if temperature is None
            else temperature_value(
                temperature, 62 if is_fahrenheit else 17, 86 if is_fahrenheit else 30
            )
        )
        mode = MideaMode(mode) if power else MideaMode.AUTO
        mode_code = int(mode)
        if mode == MideaMode.FAN_ONLY:
            temp = 31
        if temp is None:
            raise ValueError("temperature is required for this mode")
        fan_code = int(MideaFanSpeed(fan))
        flags = (128 if power else 0) | (64 if sleep else 0) | fan_code << 3 | mode_code
        if fan_code == 0 and mode in (
            MideaMode.COOL,
            MideaMode.HEAT,
            MideaMode.FAN_ONLY,
        ):
            flags |= 32
        temp_code = 31 if mode == MideaMode.FAN_ONLY else temp
        return cls(
            data=bytes(
                [0xA1, flags, 0x40 | (32 if is_fahrenheit else 0) | temp_code, 255, 255]
            )
        )

    @classmethod
    def follow_me(cls, *, temperature: int, beeper: bool = False) -> Self:
        """Report a remote sensor temperature of 0..37 °C."""
        temperature_value(temperature, 0, 37)
        return cls(
            data=bytes([0xA4, 0x82, 0x48, 0xFF if beeper else 0x7F, temperature + 1])
        )

    @property
    def follow_me_temperature(self) -> int | None:
        """Return the sensor report's Celsius temperature, when present."""
        return self.data[4] - 1 if self.data[0] == 0xA4 else None

    @property
    def follow_me_beeper(self) -> bool | None:
        """Return the sensor report's beeper flag, when present."""
        return bool(self.data[3] & 128) if self.data[0] == 0xA4 else None

    @property
    def state(self) -> MideaState | None:
        """Read control state; special and sensor packets have no climate state."""
        if self.data[0] != 0xA1:
            return None
        if self.data[1] & 7 not in MideaMode:
            return None
        mode = MideaMode(self.data[1] & 7)
        temp = self.data[2] & 31
        is_fahrenheit = bool(self.data[2] & 32)
        temperature = temp + (62 if is_fahrenheit else 17)
        if mode != MideaMode.FAN_ONLY:
            if temp > (24 if is_fahrenheit else 13):
                return None
        return MideaState(
            power=bool(self.data[1] & 128),
            mode=mode if self.data[1] & 128 else None,
            temperature=None if mode == MideaMode.FAN_ONLY else temperature,
            is_fahrenheit=is_fahrenheit,
            sleep=bool(self.data[1] & 64),
            fan=MideaFanSpeed(self.data[1] >> 3 & 3),
        )
