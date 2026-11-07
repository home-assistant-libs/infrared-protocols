"""ZH/LT-01 remote commands used by Chigo, Eurom and related units."""

from dataclasses import dataclass
from enum import IntEnum

from ._climate import ClimatePacket
from ._climate_fields import temperature_value
from ._timing import PulseTiming


class Zhlt01Mode(IntEnum):
    """Zhlt01 operating modes."""

    AUTO = 0x0
    COOL = 0x1
    DRY = 0x2
    FAN_ONLY = 0x3
    HEAT = 0x4


class Zhlt01FanSpeed(IntEnum):
    """Zhlt01 fan speeds."""

    AUTO = 0x0
    HIGH = 0x20
    MEDIUM = 0x40
    LOW = 0x60
    QUIET = 0x1


@dataclass(frozen=True, kw_only=True)
class Zhlt01State:
    """Settings carried by a Zhlt01 packet, using its native enums and units."""

    power: bool | None = None
    mode: Zhlt01Mode | None = None
    temperature: int | None = None
    fan: Zhlt01FanSpeed | None = None
    swing_v: bool | None = None
    swing_h: bool | None = None


class Zhlt01Command(ClimatePacket[Zhlt01State]):
    """ZH/LT-01 full state with boost and silent/sleep fan selection."""

    HEADER = (6100, -7400)
    TIMING = PulseTiming(500, 600, 1800)
    LENGTH = 12

    def __init__(
        self,
        *,
        mode: Zhlt01Mode | None,
        temperature: int,
        power: bool = True,
        fan: Zhlt01FanSpeed = Zhlt01FanSpeed.AUTO,
        swing_v: bool = False,
        swing_h: bool = False,
        boost: bool = False,
    ) -> None:
        """Build a state for 16..32 °C; QUIET selects the sleep fan setting."""
        if power:
            Zhlt01Mode(mode)
        temp = temperature_value(temperature, 16, 32)
        control = (2 if power else 0) | (4 if swing_v else 8) | (0 if swing_h else 16)
        control |= int(Zhlt01FanSpeed(Zhlt01FanSpeed.HIGH if boost else fan))
        values = bytes(
            [
                0,
                8 if boost else 0,
                0,
                control,
                (int(Zhlt01Mode(mode)) << 5 if power else 0) | temp,
                0xD5,
            ]
        )
        data = bytes(byte for value in values for byte in (value ^ 255, value))
        super().__init__(data=data)

    @property
    def boost(self) -> bool:
        """Return whether turbo is enabled."""
        return bool(self.data[3] & 8)

    @classmethod
    def parse(cls, data: bytes) -> Zhlt01State:
        """Validate every inverted byte pair and the remote identifier."""
        if (
            len(data) != cls.LENGTH
            or data[-1] != 0xD5
            or any(data[i] ^ data[i + 1] != 255 for i in range(0, 12, 2))
        ):
            raise ValueError("invalid ZH/LT-01 byte pair or identifier")
        temperature = (data[9] & 31) + 16
        temperature_value(temperature, 16, 32)
        return Zhlt01State(
            power=bool(data[7] & 2),
            mode=Zhlt01Mode(data[9] >> 5) if bool(data[7] & 2) else None,
            temperature=temperature,
            fan=Zhlt01FanSpeed(data[7] & 0xE1),
            swing_v=data[7] & 12 != 8,
            swing_h=not bool(data[7] & 16),
        )
