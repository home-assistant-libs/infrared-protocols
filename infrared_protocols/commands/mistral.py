"""Mistral MHFE1126A / MR112C AEHA climate commands."""

from dataclasses import dataclass
from enum import IntEnum

from ._aeha_climate import AehaClimatePacket
from ._climate_fields import temperature_value


class MistralMode(IntEnum):
    """Mistral operating modes."""

    COOL = 0x3
    DRY = 0x2
    FAN_ONLY = 0x1
    HEAT = 0x6
    AUTO = 0x8


class MistralFanSpeed(IntEnum):
    """Mistral fan speeds."""

    AUTO = 0x2500
    LOW = 0x2202
    MEDIUM = 0x2403
    HIGH = 0x2505


@dataclass(frozen=True, kw_only=True)
class MistralState:
    """Settings carried by a Mistral packet, using its native enums and units."""

    power: bool | None = None
    mode: MistralMode | None = None
    temperature: int | None = None
    fan: MistralFanSpeed | None = None


class MistralCommand(AehaClimatePacket[MistralState]):
    """Mistral full state; data includes the AEHA address bytes in wire order."""

    LENGTH = 14

    def __init__(
        self,
        *,
        mode: MistralMode | None,
        temperature: int,
        power: bool = True,
        fan: MistralFanSpeed = MistralFanSpeed.AUTO,
    ) -> None:
        """Build a whole-degree 16..30 °C state."""
        if power:
            MistralMode(mode)
        temperature_value(temperature, 16, 30)
        fan_code = int(MistralFanSpeed(fan))
        data = bytes(
            [
                0x4C,
                0x34,
                0x6A,
                fan_code >> 8,
                16,
                4 if power else 0,
                int(MistralMode(mode)) if power else 8,
                159 - int(temperature),
                fan_code & 255,
                0,
                0x17,
                0,
                6,
            ]
        )
        super().__init__(data=data + bytes([self.checksum(data)]))

    @staticmethod
    def checksum(data: bytes) -> int:
        """Checksum the six defined fields in their native bit order."""
        return sum(data[i] for i in (3, 5, 6, 7, 8, 10)) & 255

    @classmethod
    def parse(cls, data: bytes) -> MistralState:
        """Validate the frame signature and recover the state."""
        cls._validate_packet(data)
        if (
            data[:3] != b"\x4c\x34\x6a"
            or data[4] != 16
            or data[9:13] != b"\x00\x17\x00\x06"
            or data[5] not in (0, 4)
        ):
            raise ValueError("invalid Mistral signature")
        temperature = 159 - data[7]
        temperature_value(temperature, 16, 30)
        return MistralState(
            power=bool(data[5]),
            mode=MistralMode(data[6]) if bool(data[5]) else None,
            temperature=temperature,
            fan=MistralFanSpeed(data[3] << 8 | data[8]),
        )
