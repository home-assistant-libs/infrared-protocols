"""Noblex split-frame climate commands with a four-bit checksum."""

from dataclasses import dataclass
from enum import IntEnum

from ._climate_fields import temperature_value
from ._split_climate import SplitClimateCommand
from ._timing import PulseTiming, bits, byte_bits, number, pack_bytes


class NoblexMode(IntEnum):
    """Noblex operating modes."""

    AUTO = 0x0
    COOL = 0x4
    DRY = 0x2
    FAN_ONLY = 0x6
    HEAT = 0x1


class NoblexFanSpeed(IntEnum):
    """Noblex fan speeds."""

    AUTO = 0x0
    LOW = 0x2
    MEDIUM = 0x1
    HIGH = 0x3


@dataclass(frozen=True, kw_only=True)
class NoblexState:
    """Settings carried by a Noblex packet, using its native enums and units."""

    power: bool | None = None
    mode: NoblexMode | None = None
    temperature: int | None = None
    fan: NoblexFanSpeed | None = None
    swing_v: bool | None = None


def _reverse(value: int) -> int:
    return number(bits(value, 8), lsb=True)


def _checksum(data: bytes) -> int:
    return _reverse(sum(_reverse(value) for value in data) & 15) >> 4


class NoblexCommand(SplitClimateCommand[NoblexState]):
    """Noblex absolute state; the divider replaces a fixed one bit.

    Decoding requires all sections in one capture. Configure the receiver idle
    timeout above 20 ms, or join captures with their measured intervening gaps.
    A default 10 ms ESPHome receiver splits this packet; pass the consecutive
    bursts from one press to from_raw_captures() to decode it.
    """

    HEADER = (9000, -4500)
    TIMING = PulseTiming(660, 520, 1640)

    def __init__(
        self,
        *,
        mode: NoblexMode | None,
        temperature: int | None = None,
        power: bool = True,
        fan: NoblexFanSpeed = NoblexFanSpeed.AUTO,
        swing_v: bool = False,
    ) -> None:
        """Build a state using the receiver's mode fields, with 25 °C in auto.

        ESPHome's transmitter currently ORs mode into a cool template, which
        changes auto/dry/heat codes. Here the mode field is assigned explicitly.
        """
        temp = None if temperature is None else temperature_value(temperature, 16, 30)
        if power and mode == NoblexMode.AUTO:
            temp = 9
        if temp is None:
            raise ValueError("temperature is required for this mode")
        code = int(NoblexMode(mode)) if power else 4
        data = bytes(
            [
                code << 5
                | (16 if power else 0)
                | int(NoblexFanSpeed(fan)) << 2
                | (2 if swing_v else 0),
                _reverse(temp),
                2 if power else 0,
                10,
                0x58 if swing_v else 0x50,
                0,
                0x20,
                0,
            ]
        )
        values = byte_bits(data, lsb=False)
        super().__init__(
            data=number(values[:35] + values[36:] + bits(_checksum(data), 4))
        )

    @property
    def state(self) -> NoblexState:
        """Reconstruct the omitted fixed bit and verify the checksum."""
        values = bits(self.data, self.WIDTH)
        data = pack_bytes(values[:35] + [1] + values[35:63], lsb=False)
        if (
            data[3] != 10
            or data[4] & ~8 != 0x50
            or data[6:] != bytes([32, 0])
            or number(values[63:]) != _checksum(data)
        ):
            raise ValueError("invalid Noblex signature or checksum")
        temp = (_reverse(data[1]) & 15) + 16
        temperature_value(temp, 16, 30)
        mode = NoblexMode(data[0] >> 5) if data[0] & 16 else None
        return NoblexState(
            power=bool(data[0] & 16),
            mode=mode,
            temperature=None if mode == NoblexMode.AUTO else temp,
            fan=NoblexFanSpeed(data[0] >> 2 & 3),
            swing_v=bool(data[0] & 2),
        )
