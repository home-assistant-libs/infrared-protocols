"""Toshiba RAC-PT1411HWRU and RAS-2819T complementary 48-bit packets."""

from dataclasses import dataclass
from enum import IntEnum
from typing import Self

from ._climate_fields import decoded, selection, temperature_value
from ._timing import PulseTiming, bits
from .toshiba_ac import ToshibaAcPacketCommand


class Toshiba48Mode(IntEnum):
    """Toshiba48 operating modes."""

    COOL = 0x0
    DRY = 0x4
    AUTO = 0x8
    HEAT = 0xC
    FAN_ONLY = 0xE4


class Toshiba48FanSpeed(IntEnum):
    """Toshiba48 fan speeds."""

    AUTO = 0xBF
    AUTO_ALT = 0x1F
    LOW = 0x9F
    MEDIUM = 0x5F
    HIGH = 0x3F
    QUIET = 0xFF


@dataclass(frozen=True, kw_only=True)
class Toshiba48State:
    """Settings carried by a Toshiba48 packet, using its native enums and units."""

    power: bool | None = None
    mode: Toshiba48Mode | None = None
    temperature: int | None = None
    fan: Toshiba48FanSpeed | None = None
    swing_v: bool | None = None
    is_fahrenheit: bool | None = None


_TEMPS_C = (0x10, 0, 1, 3, 2, 6, 7, 5, 4, 12, 13, 9, 8, 10, 11)
_TEMPS_F = (
    0x10, 0x30, 0x0, 0x20, 0x1, 0x21, 0x3, 0x23, 0x2, 0x22, 0x6, 0x26, 0x7,
    0x5, 0x25, 0x4, 0x24, 0xc, 0x2c, 0xd, 0x2d, 0x9, 0x8, 0x28, 0xa, 0x2a, 0xb,
)  # fmt: skip
_MODES = {
    Toshiba48Mode.COOL: 0,
    Toshiba48Mode.DRY: 4,
    Toshiba48Mode.AUTO: 8,
    Toshiba48Mode.HEAT: 12,
    Toshiba48Mode.FAN_ONLY: 4,
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
        if len(first) != 6 or second is not None and len(second) != 6:
            raise ValueError("invalid Toshiba 48-bit packet")
        super().__init__(
            rc_code_1=int.from_bytes(first),
            rc_code_2=int.from_bytes(second) if second is not None else None,
            modulation=modulation,
        )
        _ = self.state

    @property
    def first(self) -> bytes:
        """Return the primary payload sent by the shared transport."""
        bits(self.rc_code_1, 48)
        data = self.rc_code_1.to_bytes(6)
        if any(data[i] ^ data[i + 1] != 255 for i in (0, 2, 4)):
            raise ValueError("invalid Toshiba 48-bit packet")
        return data

    @property
    def second(self) -> bytes | None:
        """Return the optional extension sent by the shared transport."""
        if self.rc_code_2 is None:
            return None
        bits(self.rc_code_2, 48)
        return self.rc_code_2.to_bytes(6)

    @property
    def state(self) -> Toshiba48State:
        """Interpret a device-specific command."""
        _ = self.first, self.second
        return Toshiba48State()

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
        _ = self.state
        return (
            self.first[2] & 31
            if self.first[0] == 0xBA and self.first[2] & 128
            else None
        )

    @property
    def comfort_sense_enabled(self) -> bool | None:
        """Return the Comfort Sense enable flag, absent in other commands."""
        _ = self.state
        return bool(self.first[2] & 64) if self.first[0] == 0xBA else None

    @property
    def comfort_sense_reports_temperature(self) -> bool | None:
        """Return whether a Comfort Sense message contains a sensor reading."""
        _ = self.state
        return bool(self.first[2] & 128) if self.first[0] == 0xBA else None

    @property
    def comfort_sense_mode(self) -> Toshiba48Mode | None:
        """Return the mode carried by a Comfort Sense message."""
        _ = self.state
        if self.first[0] != 0xBA:
            return None
        return {
            0x7A: Toshiba48Mode.AUTO,
            0x72: Toshiba48Mode.COOL,
            0x7E: Toshiba48Mode.HEAT,
        }[self.first[4]]

    @classmethod
    def climate(
        cls,
        *,
        mode: Toshiba48Mode,
        temperature: int | None = None,
        fan: Toshiba48FanSpeed | None = None,
        is_fahrenheit: bool = False,
    ) -> Self:
        """Build an on-state, using 16..30 °C or 60..86 °F."""
        index = (
            None
            if temperature is None
            else temperature_value(
                temperature, 60 if is_fahrenheit else 16, 86 if is_fahrenheit else 30
            )
        )
        if mode == Toshiba48Mode.FAN_ONLY:
            index = 0
        if index is None:
            raise ValueError("temperature is required for this mode")
        auto = mode in (Toshiba48Mode.AUTO, Toshiba48Mode.DRY)
        if fan is None:
            fan = Toshiba48FanSpeed.AUTO_ALT if auto else Toshiba48FanSpeed.AUTO
        fan2_codes = {
            Toshiba48FanSpeed.AUTO: 0x66,
            Toshiba48FanSpeed.AUTO_ALT: 0x65,
            Toshiba48FanSpeed.LOW: 0x28,
            Toshiba48FanSpeed.MEDIUM: 0x3C,
            Toshiba48FanSpeed.HIGH: 0x64,
        }
        fan2 = selection(fan, fan2_codes)
        fan1 = int(Toshiba48FanSpeed(fan))
        if mode in (Toshiba48Mode.AUTO, Toshiba48Mode.DRY):
            if fan != Toshiba48FanSpeed.AUTO_ALT:
                raise ValueError("automatic and dry modes require AUTO_ALT fan")
            fan1, fan2 = 0x1F, 0x65
        elif fan == Toshiba48FanSpeed.AUTO_ALT:
            raise ValueError("RAC alternate automatic fan requires auto or dry mode")
        temp = (
            14
            if mode == Toshiba48Mode.FAN_ONLY
            else (_TEMPS_F if is_fahrenheit else _TEMPS_C)[index]
        )
        first = _paired((0xB2, fan1, (temp & 15) << 4 | selection(mode, _MODES)))
        second = bytes([0xD5, fan2, temp & 32, (temp & 16) | int(is_fahrenheit), 0])
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
        mode: Toshiba48Mode,
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
            {
                Toshiba48Mode.AUTO: 0x7A,
                Toshiba48Mode.COOL: 0x72,
                Toshiba48Mode.HEAT: 0x7E,
            },
        )
        return cls(first=_paired((0xBA, temperature | flags, mode_code)))

    @property
    def state(self) -> Toshiba48State:
        """Validate the extension checksum and recover unambiguous state."""
        first, second = self.first, self.second
        if (
            first[0] == 0xB9
            and first[2] == 0xF5
            and first[4] in (4, 5)
            and second is None
        ):
            return Toshiba48State(swing_v=first[4] == 4)
        if first[0] == 0xBA and first[4] in (0x7A, 0x72, 0x7E) and second is None:
            return Toshiba48State()
        if first == _paired((0xB2, 0x7B, 0xE0)) and second is None:
            return Toshiba48State(power=False)
        if (
            first[0] != 0xB2
            or second is None
            or second[0] != 0xD5
            or sum(second[:-1]) & 255 != second[-1]
        ):
            raise ValueError("invalid RAC state or extension checksum")
        mode = (
            Toshiba48Mode.FAN_ONLY
            if first[4] == 0xE4 and first[2] != 0x1F
            else decoded(first[4] & 15, _MODES)
        )
        auto = mode in (Toshiba48Mode.AUTO, Toshiba48Mode.DRY)
        fan = Toshiba48FanSpeed.AUTO_ALT if auto else Toshiba48FanSpeed(first[2])
        expected2 = (
            0x65
            if auto
            else selection(
                fan,
                {
                    Toshiba48FanSpeed.AUTO: 0x66,
                    Toshiba48FanSpeed.LOW: 0x28,
                    Toshiba48FanSpeed.MEDIUM: 0x3C,
                    Toshiba48FanSpeed.HIGH: 0x64,
                },
            )
        )
        if second[1] != expected2 or auto and first[2] != 0x1F:
            raise ValueError("inconsistent RAC fan fields")
        temp = (first[4] >> 4) | (second[2] & 32) | (second[3] & 16)
        temperature: int | None = None
        if mode != Toshiba48Mode.FAN_ONLY:
            if second[3] & 1:
                temperature = _TEMPS_F.index(temp) + 60
            else:
                temperature = _TEMPS_C.index(temp) + 16
        return Toshiba48State(
            power=True,
            mode=mode,
            temperature=temperature,
            fan=fan,
            is_fahrenheit=bool(second[3] & 1),
        )


class ToshibaRas2819Command(Toshiba48Command):
    """RAS-2819T climate state and power/swing actions."""

    @classmethod
    def climate(
        cls,
        *,
        mode: Toshiba48Mode,
        temperature: int | None = None,
        fan: Toshiba48FanSpeed | None = None,
    ) -> Self:
        """Build an 18..30 °C state; automatic/dry modes use automatic fan."""
        index = None if temperature is None else temperature_value(temperature, 18, 30)
        if mode == Toshiba48Mode.FAN_ONLY:
            index = 0
        if index is None:
            raise ValueError("temperature is required for this mode")
        auto = mode in (Toshiba48Mode.AUTO, Toshiba48Mode.DRY)
        if fan is None:
            fan = Toshiba48FanSpeed.AUTO_ALT if auto else Toshiba48FanSpeed.AUTO
        if auto and fan != Toshiba48FanSpeed.AUTO_ALT:
            raise ValueError("automatic and dry modes require AUTO_ALT fan")
        if (
            mode in (Toshiba48Mode.HEAT, Toshiba48Mode.FAN_ONLY)
            and fan == Toshiba48FanSpeed.AUTO_ALT
        ):
            raise ValueError(
                "AUTO_ALT fan is only available in auto, dry and cool modes"
            )
        temp = _TEMPS_C[index + 2] << 4
        temp |= selection(mode, _MODES)
        if mode == Toshiba48Mode.DRY:
            temp |= 0x20
        elif mode == Toshiba48Mode.FAN_ONLY:
            temp = 0xE4
        first = _paired((0xC2, 0x1F if auto else int(Toshiba48FanSpeed(fan)), temp))
        return cls(first=first, second=cls._extension(mode, fan))

    @staticmethod
    def _extension(mode: Toshiba48Mode, fan: Toshiba48FanSpeed) -> bytes:
        if fan == Toshiba48FanSpeed.AUTO_ALT:
            return bytes([0xD5, 0x65, 0, 0, 0, 0x3A])
        fan_code = selection(
            fan,
            {
                Toshiba48FanSpeed.AUTO: 0x66,
                Toshiba48FanSpeed.QUIET: 1,
                Toshiba48FanSpeed.LOW: 0x28,
                Toshiba48FanSpeed.MEDIUM: 0x3C,
                Toshiba48FanSpeed.HIGH: 0x50,
            },
        )
        suffix = selection(
            fan,
            {
                Toshiba48FanSpeed.AUTO: 0x3D,
                Toshiba48FanSpeed.QUIET: 0xD8,
                Toshiba48FanSpeed.LOW: 0xFF,
                Toshiba48FanSpeed.MEDIUM: 0x13,
                Toshiba48FanSpeed.HIGH: 0x27,
            },
        )
        return bytes(
            [
                0xD5,
                fan_code,
                0,
                0,
                2 if mode == Toshiba48Mode.COOL else 0,
                suffix if mode == Toshiba48Mode.COOL else 0x3B,
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
        _ = self.state
        return self._temperature_candidates()

    def _temperature_candidates(self) -> tuple[int, ...]:
        """Find set points after the caller validates the packet."""
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
    def state(self) -> Toshiba48State:
        """Validate both packet identities; ambiguous dry temperatures stay unknown."""
        first, second = self.first, self.second
        if first == _paired((0xC2, 0x7B, 0xE0)) and second is None:
            return Toshiba48State(power=False)
        if first == _paired((0xC2, 0x6B, 0xE0)) and second is None:
            return Toshiba48State()
        if first[0] != 0xC2 or second is None:
            raise ValueError("invalid RAS-2819T state")
        mode = (
            Toshiba48Mode.FAN_ONLY
            if first[4] == 0xE4 and first[2] != 0x1F
            else decoded(first[4] & 15, _MODES)
        )
        fan = Toshiba48FanSpeed(first[2])
        if mode == Toshiba48Mode.HEAT and fan == Toshiba48FanSpeed.AUTO_ALT:
            raise ValueError(
                "AUTO_ALT fan is only available in auto, dry and cool modes"
            )
        if mode in (Toshiba48Mode.AUTO, Toshiba48Mode.DRY) and first[2] != 0x1F:
            raise ValueError("RAS-2819T auto and dry require automatic fan")
        expected = self._extension(mode, fan)
        if second != expected:
            raise ValueError("inconsistent RAS-2819T extension")
        candidates = self._temperature_candidates()
        if mode != Toshiba48Mode.FAN_ONLY and not candidates:
            raise ValueError("invalid RAS-2819T temperature")
        return Toshiba48State(
            power=True,
            mode=mode,
            fan=fan,
            temperature=candidates[0] if len(candidates) == 1 else None,
        )
