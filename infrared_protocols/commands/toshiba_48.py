"""Toshiba RAC-PT1411HWRU and RAS-2819T complementary 48-bit packets."""

from typing import Self

from ._climate_fields import decoded, selection, temperature_value
from ._timing import PulseTiming
from .climate import (
    ClimateFan,
    ClimateMode,
    ClimateState,
)
from .toshiba_ac import ToshibaAcPacketCommand

_TEMPS_C = (0x10, 0, 1, 3, 2, 6, 7, 5, 4, 12, 13, 9, 8, 10, 11)
_TEMPS_F = (
    0x10,
    0x30,
    0,
    0x20,
    1,
    0x21,
    3,
    0x23,
    2,
    0x22,
    6,
    0x26,
    7,
    5,
    0x25,
    4,
    0x24,
    12,
    0x2C,
    13,
    0x2D,
    9,
    8,
    0x28,
    10,
    0x2A,
    11,
)
_MODES = {
    ClimateMode.COOL: 0,
    ClimateMode.DRY: 4,
    ClimateMode.AUTO: 8,
    ClimateMode.HEAT: 12,
    ClimateMode.FAN_ONLY: 4,
}
_FANS = {
    ClimateFan.AUTO: 0xBF,
    ClimateFan.LOW: 0x9F,
    ClimateFan.MEDIUM: 0x5F,
    ClimateFan.HIGH: 0x3F,
    ClimateFan.QUIET: 0xFF,
}


def _paired(values: tuple[int, int, int]) -> bytes:
    return bytes(byte for value in values for byte in (value, value ^ 255))


class Toshiba48Command(ToshibaAcPacketCommand):
    """One complementary packet sent twice, followed by an optional extension."""

    HEADER = (4380, -4370)
    TIMING = PulseTiming(540, 540, 1620)
    GAP = 5480

    def __init__(
        self, *, first: bytes, second: bytes | None = None, modulation: int = 38000
    ) -> None:
        """Validate packet sizes and the three complement pairs."""
        if (
            len(first) != 6
            or any(first[i] ^ first[i + 1] != 255 for i in (0, 2, 4))
            or second is not None
            and len(second) != 6
        ):
            raise ValueError("invalid Toshiba 48-bit packet")
        super().__init__(
            rc_code_1=int.from_bytes(first),
            rc_code_2=int.from_bytes(second) if second is not None else None,
            modulation=modulation,
        )
        self.first, self.second = (
            bytes(first),
            bytes(second) if second is not None else None,
        )
        _ = self.state

    @property
    def state(self) -> ClimateState:
        """Interpret a device-specific command."""
        return ClimateState()

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Use the shared 48-bit transport, then validate the model's packets."""
        words = cls._read_words(timings)
        if words is None:
            return None
        try:
            return cls(
                first=words[0].to_bytes(6),
                second=words[2].to_bytes(6) if len(words) == 3 else None,
            )
        except ValueError:
            return None


class ToshibaRacCommand(Toshiba48Command):
    """RAC-PT1411HWRU C/F state, absolute swing and Comfort Sense messages."""

    @property
    def room_temperature(self) -> int | None:
        """Return the Comfort Sense report's Celsius reading, when present."""
        return (
            self.first[2] & 31
            if self.first[0] == 0xBA and self.first[2] & 128
            else None
        )

    @property
    def comfort_sense_enabled(self) -> bool | None:
        """Return the Comfort Sense enable flag, absent in other commands."""
        return bool(self.first[2] & 64) if self.first[0] == 0xBA else None

    @property
    def comfort_sense_reports_temperature(self) -> bool | None:
        """Return whether a Comfort Sense message contains a sensor reading."""
        return bool(self.first[2] & 128) if self.first[0] == 0xBA else None

    @property
    def comfort_sense_mode(self) -> ClimateMode | None:
        """Return the mode carried by a Comfort Sense message."""
        if self.first[0] != 0xBA:
            return None
        return {0x7A: ClimateMode.AUTO, 0x72: ClimateMode.COOL, 0x7E: ClimateMode.HEAT}[
            self.first[4]
        ]

    @property
    def fahrenheit(self) -> bool | None:
        """Return the native unit flag, absent in standalone actions."""
        return bool(self.second[3] & 1) if self.second is not None else None

    @property
    def temperature(self) -> int | None:
        """Return the native setpoint accepted by climate(), without conversion."""
        second = self.second
        if second is None or self.state.mode == ClimateMode.FAN_ONLY:
            return None
        value = (self.first[4] >> 4) | (second[2] & 32) | (second[3] & 16)
        return (
            _TEMPS_F.index(value) + 60
            if self.fahrenheit
            else _TEMPS_C.index(value) + 16
        )

    @classmethod
    def climate(
        cls,
        *,
        mode: ClimateMode,
        temperature: int,
        fan: ClimateFan = ClimateFan.AUTO,
        fahrenheit: bool = False,
    ) -> Self:
        """Build an on-state, using 16..30 °C or 60..86 °F."""
        index = temperature_value(
            temperature, 60 if fahrenheit else 16, 86 if fahrenheit else 30
        )
        fan2_codes = {
            ClimateFan.AUTO: 0x66,
            ClimateFan.LOW: 0x28,
            ClimateFan.MEDIUM: 0x3C,
            ClimateFan.HIGH: 0x64,
        }
        fan2 = selection(fan, fan2_codes)
        fan1 = selection(fan, _FANS)
        if mode in (ClimateMode.AUTO, ClimateMode.DRY):
            if fan != ClimateFan.AUTO:
                raise ValueError("automatic and dry modes require automatic fan")
            fan1, fan2 = 0x1F, 0x65
        temp = (
            14
            if mode == ClimateMode.FAN_ONLY
            else (_TEMPS_F if fahrenheit else _TEMPS_C)[index]
        )
        first = _paired((0xB2, fan1, (temp & 15) << 4 | selection(mode, _MODES)))
        second = bytes([0xD5, fan2, temp & 32, (temp & 16) | int(fahrenheit), 0])
        return cls(first=first, second=second + bytes([sum(second) & 255]))

    @classmethod
    def power_off(cls) -> Self:
        """Build the short power-off command."""
        return cls(first=_paired((0xB2, 0x7B, 0xE0)))

    @classmethod
    def swing(cls, *, enabled: bool) -> Self:
        """Set vertical swing to an absolute state."""
        return cls(first=_paired((0xB9, 0xF5, 4 if enabled else 5)))

    @classmethod
    def comfort_sense(
        cls,
        *,
        mode: ClimateMode,
        temperature: int,
        enabled: bool = True,
        send_temperature: bool = True,
    ) -> Self:
        """Report an ambient sensor value, or enable/disable Comfort Sense."""
        temperature_value(temperature, 0, 31)
        if send_temperature and not enabled:
            raise ValueError("temperature reports require Comfort Sense enabled")
        flags = (64 if enabled else 0) | (128 if send_temperature else 0)
        mode_code = selection(
            mode,
            {ClimateMode.AUTO: 0x7A, ClimateMode.COOL: 0x72, ClimateMode.HEAT: 0x7E},
        )
        return cls(first=_paired((0xBA, temperature | flags, mode_code)))

    @property
    def state(self) -> ClimateState:
        """Validate the extension checksum and recover unambiguous state."""
        first, second = self.first, self.second
        if (
            first[0] == 0xB9
            and first[2] == 0xF5
            and first[4] in (4, 5)
            and second is None
        ):
            return ClimateState(swing_v=first[4] == 4)
        if first[0] == 0xBA and first[4] in (0x7A, 0x72, 0x7E) and second is None:
            return ClimateState()
        if first == _paired((0xB2, 0x7B, 0xE0)) and second is None:
            return ClimateState(power=False)
        if (
            first[0] != 0xB2
            or second is None
            or second[0] != 0xD5
            or sum(second[:-1]) & 255 != second[-1]
        ):
            raise ValueError("invalid RAC state or extension checksum")
        mode = (
            ClimateMode.FAN_ONLY
            if first[4] == 0xE4 and first[2] != 0x1F
            else decoded(first[4] & 15, _MODES)
        )
        auto = mode in (ClimateMode.AUTO, ClimateMode.DRY)
        fan = ClimateFan.AUTO if auto else decoded(first[2], _FANS)
        expected2 = (
            0x65
            if auto
            else selection(
                fan,
                {
                    ClimateFan.AUTO: 0x66,
                    ClimateFan.LOW: 0x28,
                    ClimateFan.MEDIUM: 0x3C,
                    ClimateFan.HIGH: 0x64,
                },
            )
        )
        if second[1] != expected2 or auto and first[2] != 0x1F:
            raise ValueError("inconsistent RAC fan fields")
        temp = (first[4] >> 4) | (second[2] & 32) | (second[3] & 16)
        temperature: float | None = None
        if mode != ClimateMode.FAN_ONLY:
            if second[3] & 1:
                temperature = (_TEMPS_F.index(temp) + 60 - 32) * 5 / 9
            else:
                temperature = _TEMPS_C.index(temp) + 16
        return ClimateState(power=True, mode=mode, temperature=temperature, fan=fan)


class ToshibaRas2819Command(Toshiba48Command):
    """RAS-2819T climate state and power/swing actions."""

    @classmethod
    def climate(
        cls, *, mode: ClimateMode, temperature: int, fan: ClimateFan = ClimateFan.AUTO
    ) -> Self:
        """Build an 18..30 °C state; automatic/dry modes use automatic fan."""
        index = temperature_value(temperature, 18, 30)
        auto = mode in (ClimateMode.AUTO, ClimateMode.DRY)
        if auto and fan != ClimateFan.AUTO:
            raise ValueError("automatic and dry modes require automatic fan")
        temp = _TEMPS_C[index + 2] << 4
        temp |= selection(mode, _MODES)
        if mode == ClimateMode.DRY:
            temp |= 0x20
        elif mode == ClimateMode.FAN_ONLY:
            temp = 0xE4
        first = _paired((0xC2, 0x1F if auto else selection(fan, _FANS), temp))
        return cls(first=first, second=cls._extension(mode, fan))

    @staticmethod
    def _extension(mode: ClimateMode, fan: ClimateFan) -> bytes:
        if mode in (ClimateMode.AUTO, ClimateMode.DRY):
            return bytes([0xD5, 0x65, 0, 0, 0, 0x3A])
        fan_code = selection(
            fan,
            {
                ClimateFan.AUTO: 0x66,
                ClimateFan.QUIET: 1,
                ClimateFan.LOW: 0x28,
                ClimateFan.MEDIUM: 0x3C,
                ClimateFan.HIGH: 0x50,
            },
        )
        suffix = selection(
            fan,
            {
                ClimateFan.AUTO: 0x3D,
                ClimateFan.QUIET: 0xD8,
                ClimateFan.LOW: 0xFF,
                ClimateFan.MEDIUM: 0x13,
                ClimateFan.HIGH: 0x27,
            },
        )
        return bytes(
            [
                0xD5,
                fan_code,
                0,
                0,
                2 if mode == ClimateMode.COOL else 0,
                suffix if mode == ClimateMode.COOL else 0x3B,
            ]
        )

    @classmethod
    def power_off(cls) -> Self:
        """Build the short power-off command."""
        return cls(first=_paired((0xC2, 0x7B, 0xE0)))

    @classmethod
    def swing_toggle(cls) -> Self:
        """Toggle vertical swing; the caller must retain the assumed state."""
        return cls(first=_paired((0xC2, 0x6B, 0xE0)))

    @property
    def temperature_candidates(self) -> tuple[int, ...]:
        """Return all set points matching the code; dry mode has collisions."""
        code = self.first[4]
        if code == 0xE4 and self.first[2] != 0x1F or self.second is None:
            return ()
        extra = 0x24 if code & 15 == 4 else code & 15
        return tuple(
            temperature
            for temperature in range(18, 31)
            if (_TEMPS_C[temperature - 16] << 4 | extra) == code
        )

    @property
    def state(self) -> ClimateState:
        """Validate both packet identities; ambiguous dry temperatures stay unknown."""
        first, second = self.first, self.second
        if first == _paired((0xC2, 0x7B, 0xE0)) and second is None:
            return ClimateState(power=False)
        if first == _paired((0xC2, 0x6B, 0xE0)) and second is None:
            return ClimateState()
        if first[0] != 0xC2 or second is None:
            raise ValueError("invalid RAS-2819T state")
        mode = (
            ClimateMode.FAN_ONLY
            if first[4] == 0xE4 and first[2] != 0x1F
            else decoded(first[4] & 15, _MODES)
        )
        fan = ClimateFan.AUTO if first[2] == 0x1F else decoded(first[2], _FANS)
        if mode in (ClimateMode.AUTO, ClimateMode.DRY) and first[2] != 0x1F:
            raise ValueError("RAS-2819T auto and dry require automatic fan")
        expected = self._extension(ClimateMode.AUTO if first[2] == 0x1F else mode, fan)
        if second != expected:
            raise ValueError("inconsistent RAS-2819T extension")
        candidates = self.temperature_candidates
        if mode != ClimateMode.FAN_ONLY and not candidates:
            raise ValueError("invalid RAS-2819T temperature")
        return ClimateState(
            power=True,
            mode=mode,
            fan=fan,
            temperature=candidates[0] if len(candidates) == 1 else None,
        )
