"""Friedrich MW12Y3H state and utility commands over AEHA."""

from dataclasses import dataclass
from enum import IntEnum

from ._aeha_climate import AehaClimatePacket
from ._climate_fields import temperature_value
from ._timing import bits, number


class FriedrichMode(IntEnum):
    """Friedrich operating modes."""

    AUTO = 0x0
    COOL = 0x80
    DRY = 0x40
    FAN_ONLY = 0xC0
    HEAT = 0x20


class FriedrichFanSpeed(IntEnum):
    """Friedrich fan speeds."""

    AUTO = 0x0
    HIGH = 0x80
    MEDIUM = 0x40
    LOW = 0xC0
    QUIET = 0x20


@dataclass(frozen=True, kw_only=True)
class FriedrichState:
    """Settings carried by a Friedrich packet, using its native enums and units."""

    power: bool | None = None
    mode: FriedrichMode | None = None
    temperature: int | None = None
    fan: FriedrichFanSpeed | None = None
    swing_v: bool | None = None
    is_fahrenheit: bool | None = None


def _reverse(value: int, width: int = 8) -> int:
    return number(bits(value & ((1 << width) - 1), width), lsb=True)


class FriedrichCommand(AehaClimatePacket[FriedrichState]):
    """Power-on state with a native Fahrenheit set point."""

    LENGTH = 16
    LSB = False

    def __init__(
        self,
        *,
        mode: FriedrichMode,
        temperature: int,
        is_fahrenheit: bool = True,
        fan: FriedrichFanSpeed = FriedrichFanSpeed.AUTO,
        swing_v: bool = False,
        economy: bool = False,
    ) -> None:
        """Build a state in even degrees: heat 60..88 °F, other modes 64..88 °F."""
        if not is_fahrenheit:
            raise ValueError("this remote only supports Fahrenheit set points")
        temperature_value(temperature, 60 if mode == FriedrichMode.HEAT else 64, 88, 2)
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
                128 | _reverse((temperature - 60) // 2, 4),
                int(FriedrichMode(mode)),
                int(FriedrichFanSpeed(fan)) | (8 if swing_v else 0),
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
    def economy(self) -> bool:
        """Return the decoded economy flag."""
        return not bool(self.data[14] & 4)

    @classmethod
    def parse(cls, data: bytes) -> FriedrichState:
        """Validate signature, checksum and settings."""
        cls._validate_packet(data)
        if (
            data[:8] != bytes([0x28, 0xC6, 0, 8, 8, 0x7F, 0x90, 12])
            or data[8] & 0xF0 != 128
        ):
            raise ValueError("invalid Friedrich signature")
        mode = FriedrichMode(data[9])
        temp_f = 60 + _reverse(data[8] & 15, 4) * 2
        temperature_value(temp_f, 60 if mode == FriedrichMode.HEAT else 64, 88, 2)
        return FriedrichState(
            power=True,
            mode=mode,
            temperature=temp_f,
            is_fahrenheit=True,
            fan=FriedrichFanSpeed(data[10] & ~8),
            swing_v=bool(data[10] & 8),
        )


class FriedrichButton(IntEnum):
    """Utility commands that do not carry a full climate state."""

    POWER_OFF = 0x40


class FriedrichUtilityCommand(AehaClimatePacket[FriedrichState]):
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
    def parse(cls, data: bytes) -> FriedrichState:
        """Validate the signature and command complement."""
        if (
            len(data) != 7
            or data[:5] != bytes([0x28, 0xC6, 0, 8, 8])
            or data[5] ^ data[6] != 255
        ):
            raise ValueError("invalid Friedrich utility packet")
        button = FriedrichButton(data[5])
        return FriedrichState(
            power=False if button == FriedrichButton.POWER_OFF else None
        )
