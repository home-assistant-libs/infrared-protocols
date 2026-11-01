"""Whirlpool DG11J1 and Hisense ARG commands with explicit power toggles."""

from functools import reduce
from operator import xor
from typing import ClassVar

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
    ClimateMode.HEAT: 0,
    ClimateMode.AUTO: 1,
    ClimateMode.COOL: 2,
    ClimateMode.DRY: 3,
    ClimateMode.FAN_ONLY: 4,
}
_FANS = {
    ClimateFan.AUTO: 0,
    ClimateFan.HIGH: 1,
    ClimateFan.MEDIUM: 2,
    ClimateFan.LOW: 3,
}


class WhirlpoolCommand(ClimatePacket):
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
        mode: ClimateMode,
        temperature: int,
        power_toggle: bool = False,
        fan: ClimateFan = ClimateFan.AUTO,
        swing_toggle: bool = False,
        swing_v: bool | None = None,
        off_command: bool = False,
    ) -> None:
        """Build a state; use off_command with power_toggle to request shutdown.

        Hisense ARG uses absolute swing_v; DG11J1 uses swing_toggle. An HA
        integration must retain the assumed power and DG11J1 swing state.
        """
        temp = temperature_value(temperature, self.MIN_TEMP, self.MIN_TEMP + 14)
        if self.HISENSE and swing_toggle or not self.HISENSE and swing_v is not None:
            raise ValueError("swing semantics do not match the selected model")
        data = bytearray(21)
        data[:2] = b"\x83\x06"
        data[2] = selection(fan, _FANS) | (4 if power_toggle else 0)
        data[3] = temp << 4 | (0 if off_command else selection(mode, _MODES))
        data[6], data[18] = 128, 8
        data[15] = (
            (1 if power_toggle else 0)
            if off_command
            else 23
            if mode == ClimateMode.AUTO
            else 6
        )
        if swing_v if self.HISENSE else swing_toggle:
            data[2] |= 128
            data[8] = 64
        if self.HISENSE:
            data[11], data[12], data[15] = 128, 24, 1 if power_toggle else 2
            if off_command:
                data[3] = temp << 4 | 2
            elif mode == ClimateMode.AUTO:
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
            elif mode == ClimateMode.FAN_ONLY:
                data[3] = 0x74
                if fan == ClimateFan.AUTO:
                    data[2] |= 2
            elif mode == ClimateMode.DRY:
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
        if self.HISENSE and self.state.mode == ClimateMode.AUTO:
            return {
                0x30: tuple(range(16, 22)),
                0x50: (22,),
                0x40: (24,),
                0x20: (23, 25, 26, 27, 28, 29, 30),
            }.get(self.data[2] & 0x70, ())
        temperature = self.state.temperature
        return () if temperature is None else (int(temperature),)

    @classmethod
    def parse(cls, data: bytes) -> ClimateState:
        """Verify both XOR checksums, without inventing an absolute power state."""
        if (
            len(data) != cls.LENGTH
            or data[:2] != b"\x83\x06"
            or reduce(xor, data[2:14], 0)
            or reduce(xor, data[14:21], 0)
        ):
            raise ValueError("invalid Whirlpool packet or checksum")
        mode = decoded(data[3] & 15, _MODES)
        temperature = (data[3] >> 4) + cls.MIN_TEMP
        temperature_value(temperature, cls.MIN_TEMP, cls.MIN_TEMP + 14)
        if cls.HISENSE and mode == ClimateMode.AUTO:
            temperature = {0x50: 22, 0x40: 24}.get(data[2] & 0x70)
        return ClimateState(
            mode=mode,
            temperature=temperature,
            fan=decoded(data[2] & 3, _FANS),
            swing_v=bool(data[2] & 128) if cls.HISENSE else None,
        )


class WhirlpoolDg11j191Command(WhirlpoolCommand):
    """DG11J1-91 uses a 16..30 °C range with the same wire fields."""

    MIN_TEMP = 16


class HisenseArgCommand(WhirlpoolCommand):
    """Hisense/BGH Argentina variant, with absolute swing and auto range codes."""

    MIN_TEMP = 16
    HISENSE = True
