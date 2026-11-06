"""Midea 48-bit packets followed by an inverted packet."""

from typing import Self, override

from . import Command
from ._climate_fields import decoded, selection, temperature_value
from ._timing import PulseTiming, Reader, byte_bits, pack_bytes
from .climate import (
    ClimateFan,
    ClimateMode,
    ClimateState,
)

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
        mode: ClimateMode,
        temperature: int,
        power: bool = True,
        fan: ClimateFan = ClimateFan.AUTO,
        sleep: bool = False,
        fahrenheit: bool = False,
    ) -> Self:
        """Build a control packet; temperature is 17..30 °C or 62..86 °F."""
        temp = temperature_value(
            temperature, 62 if fahrenheit else 17, 86 if fahrenheit else 30
        )
        mode_code = selection(mode, _MODES)
        if not power:
            mode, mode_code = ClimateMode.AUTO, _MODES[ClimateMode.AUTO]
        fan_code = selection(fan, _FANS)
        flags = (128 if power else 0) | (64 if sleep else 0) | fan_code << 3 | mode_code
        if fan_code == 0 and mode in (
            ClimateMode.COOL,
            ClimateMode.HEAT,
            ClimateMode.FAN_ONLY,
        ):
            flags |= 32
        temp_code = 31 if mode == ClimateMode.FAN_ONLY else temp
        return cls(
            data=bytes(
                [0xA1, flags, 0x40 | (32 if fahrenheit else 0) | temp_code, 255, 255]
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
    def fahrenheit(self) -> bool | None:
        """Return the control packet's native units, absent on standalone actions."""
        return bool(self.data[2] & 32) if self.data[0] == 0xA1 else None

    @property
    def temperature(self) -> int | None:
        """Return the native set point, absent on fan-only and standalone actions."""
        if self.data[0] != 0xA1 or self.data[1] & 7 == _MODES[ClimateMode.FAN_ONLY]:
            return None
        return (self.data[2] & 31) + (62 if self.fahrenheit else 17)

    @property
    def sleep(self) -> bool | None:
        """Return the sleep flag only for control packets."""
        return bool(self.data[1] & 64) if self.data[0] == 0xA1 else None

    @property
    def follow_me_temperature(self) -> int | None:
        """Return the sensor report's Celsius temperature, when present."""
        return self.data[4] - 1 if self.data[0] == 0xA4 else None

    @property
    def follow_me_beeper(self) -> bool | None:
        """Return the sensor report's beeper flag, when present."""
        return bool(self.data[3] & 128) if self.data[0] == 0xA4 else None

    @property
    def state(self) -> ClimateState | None:
        """Read control state; special and sensor packets have no climate state."""
        if self.data[0] != 0xA1:
            return None
        if self.data[1] & 7 not in _MODES.values():
            return None
        mode = decoded(self.data[1] & 7, _MODES)
        temp = self.data[2] & 31
        fahrenheit = bool(self.data[2] & 32)
        temperature = (temp + 62 - 32) * 5 / 9 if fahrenheit else temp + 17
        if mode != ClimateMode.FAN_ONLY:
            if temp > (24 if fahrenheit else 13):
                return None
        return ClimateState(
            power=bool(self.data[1] & 128),
            mode=mode if self.data[1] & 128 else None,
            temperature=None if mode == ClimateMode.FAN_ONLY else temperature,
            fan=decoded(self.data[1] >> 3 & 3, _FANS),
        )


_MODES = {
    ClimateMode.COOL: 0,
    ClimateMode.DRY: 1,
    ClimateMode.AUTO: 2,
    ClimateMode.HEAT: 3,
    ClimateMode.FAN_ONLY: 4,
}
_FANS = {
    ClimateFan.AUTO: 0,
    ClimateFan.LOW: 1,
    ClimateFan.MEDIUM: 2,
    ClimateFan.HIGH: 3,
}
