"""Whirlpool DG11J1 and Hisense ARG commands with explicit power toggles."""

from dataclasses import dataclass
from enum import IntEnum
from functools import reduce
from operator import xor
from typing import ClassVar, Self, override

from ._climate import ClimatePacket, FramePart
from ._climate_fields import temperature_value
from ._timing import PulseTiming, Reader, byte_bits, pack_bytes


class WhirlpoolMode(IntEnum):
    """Whirlpool operating modes."""

    HEAT = 0x0
    AUTO = 0x1
    COOL = 0x2
    DRY = 0x3
    FAN_ONLY = 0x4


class WhirlpoolFanSpeed(IntEnum):
    """Whirlpool fan speeds."""

    AUTO = 0x0
    HIGH = 0x1
    MEDIUM = 0x2
    LOW = 0x3


@dataclass(frozen=True, kw_only=True)
class WhirlpoolState:
    """Settings carried by a Whirlpool packet, using its native enums and units."""

    power: bool | None = None
    mode: WhirlpoolMode | None = None
    temperature: int | None = None
    fan: WhirlpoolFanSpeed | None = None
    swing_v: bool | None = None


class WhirlpoolCommand(ClimatePacket[WhirlpoolState]):
    """DG11J1-3A state; power and swing bits request toggles, not absolute states."""

    HEADER = (9000, -4494)
    TIMING = PulseTiming(572, 553, 1659)
    LENGTH = 21
    PARTS = (FramePart(6, HEADER, 7960), FramePart(8, gap=7960), FramePart(7))
    MIN_TEMP: ClassVar[int] = 18
    HISENSE: ClassVar[bool] = False

    def __init__(
        self,
        *,
        mode: WhirlpoolMode | None,
        temperature: int | None = None,
        power_toggle: bool = False,
        fan: WhirlpoolFanSpeed = WhirlpoolFanSpeed.AUTO,
        swing_toggle: bool = False,
        swing_v: bool | None = None,
        off_command: bool = False,
    ) -> None:
        """Build a state; use off_command with power_toggle to request shutdown.

        Hisense ARG uses absolute swing_v; DG11J1 uses swing_toggle. An HA
        integration must retain the assumed power and DG11J1 swing state.
        """
        temp = (
            None
            if temperature is None
            else temperature_value(temperature, self.MIN_TEMP, self.MIN_TEMP + 14)
        )
        if self.HISENSE and mode == WhirlpoolMode.FAN_ONLY and not off_command:
            temp = 7
        if temp is None:
            raise ValueError("temperature is required for this mode")
        if self.HISENSE and swing_toggle or not self.HISENSE and swing_v is not None:
            raise ValueError("swing semantics do not match the selected model")
        data = bytearray(21)
        data[:2] = b"\x83\x06"
        data[2] = int(WhirlpoolFanSpeed(fan)) | (4 if power_toggle else 0)
        data[3] = temp << 4 | (0 if off_command else int(WhirlpoolMode(mode)))
        data[6], data[18] = 128, 8
        data[15] = (
            (1 if power_toggle else 0)
            if off_command
            else 23
            if mode == WhirlpoolMode.AUTO
            else 6
        )
        if swing_v if self.HISENSE else swing_toggle:
            data[2] |= 128
            data[8] = 64
        if self.HISENSE:
            data[11], data[12], data[15] = 128, 24, 1 if power_toggle else 2
            if off_command:
                data[3] = temp << 4 | 2
            elif mode == WhirlpoolMode.AUTO:
                data[3] = 0x71
                data[2] |= (
                    0x30
                    if temp < 6
                    else 0x50
                    if temp == 6
                    else 0x40
                    if temp == 8
                    else 0x20
                )
            elif mode == WhirlpoolMode.FAN_ONLY:
                data[3] = 0x74
                if fan == WhirlpoolFanSpeed.AUTO:
                    data[2] |= 2
            elif mode == WhirlpoolMode.DRY:
                data[2] &= ~3
        data[13] = reduce(xor, data[2:13], 0)
        data[20] = reduce(xor, data[14:20], 0)
        super().__init__(data=bytes(data))

    @property
    def power_toggle(self) -> bool:
        """Return whether the receiver should toggle its assumed power state."""
        return bool(self.data[2] & 4)

    @property
    def swing_toggle(self) -> bool:
        """Return a vertical-swing toggle only on DG11J1 models."""
        return not self.HISENSE and bool(self.data[2] & 128)

    @property
    def temperature_candidates(self) -> tuple[int, ...]:
        """Return all set points consistent with an ambiguous Hisense auto code."""
        if self.HISENSE and self.state.mode == WhirlpoolMode.AUTO:
            return {
                0x30: tuple(range(16, 22)),
                0x50: (22,),
                0x40: (24,),
                0x20: (23, 25, 26, 27, 28, 29, 30),
            }.get(self.data[2] & 0x70, ())
        temperature = self.state.temperature
        return () if temperature is None else (int(temperature),)

    @override
    def get_raw_timings(self) -> list[int]:
        """Preserve a received short packet instead of inventing its third part."""
        if len(self.data) == 21:
            return super().get_raw_timings()
        return [
            *self.HEADER,
            *self.TIMING.encode(byte_bits(self.data[:6])),
            self.TIMING.mark,
            -7960,
            *self.TIMING.encode(byte_bits(self.data[6:])),
            self.TIMING.mark,
        ]

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Accept complete 21-byte packets and the remote's short 14-byte form."""
        result = super().from_raw_timings(timings)
        if result is not None:
            return result
        reader = Reader(timings=timings)
        try:
            reader.expect(*cls.HEADER)
            first = pack_bytes(reader.read_bits(cls.TIMING, 48))
            reader.expect(cls.TIMING.mark, -7960)
            second = pack_bytes(reader.read_bits(cls.TIMING, 64))
            reader.expect(cls.TIMING.mark)
            reader.end()
            result = cls.__new__(cls)
            ClimatePacket.__init__(result, data=first + second)
            return result
        except ValueError:
            return None

    @classmethod
    def parse(cls, data: bytes) -> WhirlpoolState:
        """Verify both XOR checksums, without inventing an absolute power state."""
        if (
            len(data) not in (14, cls.LENGTH)
            or data[:2] != b"\x83\x06"
            or reduce(xor, data[2:14], 0)
            or len(data) == 21
            and reduce(xor, data[14:21], 0)
        ):
            raise ValueError("invalid Whirlpool packet or checksum")
        mode = WhirlpoolMode(data[3] & 15)
        temperature: int | None = (data[3] >> 4) + cls.MIN_TEMP
        temperature_value(temperature, cls.MIN_TEMP, cls.MIN_TEMP + 14)
        if cls.HISENSE and mode == WhirlpoolMode.AUTO:
            temperature = {0x50: 22, 0x40: 24}.get(data[2] & 0x70)
        if cls.HISENSE and mode == WhirlpoolMode.FAN_ONLY:
            temperature = None
        return WhirlpoolState(
            mode=None
            if len(data) == 21
            and (
                not cls.HISENSE
                and data[15] in (0, 1)
                and data[3] & 15 == 0
                or cls.HISENSE
                and data[15] == 1
                and mode == WhirlpoolMode.COOL
            )
            else mode,
            temperature=temperature,
            fan=WhirlpoolFanSpeed(data[2] & 3),
            swing_v=bool(data[8] & 64) if cls.HISENSE else None,
        )


class WhirlpoolDg11j191Command(WhirlpoolCommand):
    """DG11J1-91 uses a 16..30 °C range with the same wire fields."""

    MIN_TEMP = 16


class HisenseArgCommand(WhirlpoolCommand):
    """Hisense/BGH Argentina variant, with absolute swing and auto range codes.

    Cool power-on and power-off toggles are byte-identical. Without the unit's
    previous power state, these commands report mode=None.
    """

    MIN_TEMP = 16
    HISENSE = True
