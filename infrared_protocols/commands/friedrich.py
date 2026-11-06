"""Friedrich MW12Y3H state and utility commands over AEHA."""

from enum import IntEnum

from ._aeha_climate import AehaClimatePacket
from ._climate_fields import decoded, selection, temperature_value
from ._timing import bits, number
from .climate import (
    ClimateFan,
    ClimateMode,
    ClimateState,
)

_MODES = {
    ClimateMode.AUTO: 0,
    ClimateMode.COOL: 0x80,
    ClimateMode.DRY: 0x40,
    ClimateMode.FAN_ONLY: 0xC0,
    ClimateMode.HEAT: 0x20,
}
_FANS = {
    ClimateFan.AUTO: 0,
    ClimateFan.HIGH: 0x80,
    ClimateFan.MEDIUM: 0x40,
    ClimateFan.LOW: 0xC0,
    ClimateFan.QUIET: 0x20,
}


def _reverse(value: int, width: int = 8) -> int:
    return number(bits(value & ((1 << width) - 1), width), lsb=True)


class FriedrichCommand(AehaClimatePacket):
    """Power-on state with a native Fahrenheit set point."""

    LENGTH = 16
    LSB = False

    def __init__(
        self,
        *,
        mode: ClimateMode,
        temperature_f: int,
        fan: ClimateFan = ClimateFan.AUTO,
        swing_v: bool = False,
        economy: bool = False,
    ) -> None:
        """Build a state in even degrees: heat 60..88 °F, other modes 64..88 °F."""
        temperature_value(temperature_f, 60 if mode == ClimateMode.HEAT else 64, 88, 2)
        data = bytes(
            [
                0x28,
                0xC6,
                0,
                8,
                8,
                0x7F,
                0x90,
                12,
                128 | _reverse((temperature_f - 60) // 2, 4),
                selection(mode, _MODES),
                selection(fan, _FANS) | (8 if swing_v else 0),
                0,
                0,
                0,
                0 if economy else 4,
            ]
        )
        super().__init__(data=data + bytes([self.checksum(data)]))

    @staticmethod
    def checksum(data: bytes) -> int:
        """Checksum the variable portion in native byte order."""
        return _reverse(208 - sum(_reverse(value) for value in data[8:]))

    @property
    def temperature_f(self) -> int:
        """Return the native Fahrenheit set point."""
        return 60 + _reverse(self.data[8] & 15, 4) * 2

    @property
    def economy(self) -> bool:
        """Return the decoded economy flag."""
        return not bool(self.data[14] & 4)

    @classmethod
    def parse(cls, data: bytes) -> ClimateState:
        """Validate signature, checksum and settings."""
        super().parse(data)
        if (
            data[:8] != bytes([0x28, 0xC6, 0, 8, 8, 0x7F, 0x90, 12])
            or data[8] & 0xF0 != 128
        ):
            raise ValueError("invalid Friedrich signature")
        mode = decoded(data[9], _MODES)
        temp_f = 60 + _reverse(data[8] & 15, 4) * 2
        temperature_value(temp_f, 60 if mode == ClimateMode.HEAT else 64, 88, 2)
        return ClimateState(
            power=True,
            mode=mode,
            temperature=(temp_f - 32) * 5 / 9,
            fan=decoded(data[10] & ~8, _FANS),
            swing_v=bool(data[10] & 8),
        )


class FriedrichButton(IntEnum):
    """Utility commands that do not carry a full climate state."""

    POWER_OFF = 0x40


class FriedrichUtilityCommand(AehaClimatePacket):
    """Short power-off packet."""

    LENGTH = 7
    LSB = False

    def __init__(self, *, button: FriedrichButton) -> None:
        """Build the short utility command."""
        value = FriedrichButton(button)
        super().__init__(data=bytes([0x28, 0xC6, 0, 8, 8, value, value ^ 255]))

    @property
    def button(self) -> FriedrichButton:
        """Return the utility action."""
        return FriedrichButton(self.data[5])

    @classmethod
    def parse(cls, data: bytes) -> ClimateState:
        """Validate the signature and command complement."""
        if (
            len(data) != 7
            or data[:5] != bytes([0x28, 0xC6, 0, 8, 8])
            or data[5] ^ data[6] != 255
        ):
            raise ValueError("invalid Friedrich utility packet")
        button = FriedrichButton(data[5])
        return ClimateState(
            power=False if button == FriedrichButton.POWER_OFF else None
        )
