"""Parker Davis/Pioneer climate state in paired odd and even bursts."""

from dataclasses import dataclass
from enum import IntEnum

from ._climate import ClimatePacket, FramePart
from ._climate_fields import temperature_value
from .pd_pioneer import PdPioneerCommand


class PdPioneerClimateMode(IntEnum):
    """PdPioneerClimate operating modes."""

    HEAT = 0x1
    DRY = 0x2
    COOL = 0x3
    FAN_ONLY = 0x7
    AUTO = 0x8


class PdPioneerClimateFanSpeed(IntEnum):
    """PdPioneerClimate fan speeds."""

    AUTO = 0x0
    LOW = 0x2
    MEDIUM = 0x3
    HIGH = 0x5


@dataclass(frozen=True, kw_only=True)
class PdPioneerClimateState:
    """Pioneer settings with native mode and fan selections."""

    power: bool | None = None
    mode: PdPioneerClimateMode | None = None
    temperature: float | None = None
    fan: PdPioneerClimateFanSpeed | None = None
    swing_v: bool | None = None
    swing_h: bool | None = None


_ODD_FANS = {
    PdPioneerClimateFanSpeed.AUTO: (0x40, 0x20),
    PdPioneerClimateFanSpeed.LOW: (0x60, 0x40),
    PdPioneerClimateFanSpeed.MEDIUM: (0x40, 0x60),
    PdPioneerClimateFanSpeed.HIGH: (0x40, 0xC0),
}


class PdPioneerClimateCommand(ClimatePacket[PdPioneerClimateState]):
    """Both bursts are needed to recover horizontal and vertical swing.

    Decoding requires all sections in one capture. Configure the receiver idle
    timeout above 10.01 ms, or join captures with their measured intervening gaps.
    A default 10 ms ESPHome receiver splits this packet; pass the consecutive
    bursts from one press to from_raw_captures() to decode it.
    """

    HEADER = PdPioneerCommand.HEADER
    TIMING = PdPioneerCommand.TIMING
    LENGTH = 28
    PARTS = (
        FramePart(14, HEADER, PdPioneerCommand.GAP),
        FramePart(14, HEADER, PdPioneerCommand.GAP),
    )

    def __init__(
        self,
        *,
        mode: PdPioneerClimateMode | None,
        temperature: float | None = None,
        power: bool = True,
        fan: PdPioneerClimateFanSpeed = PdPioneerClimateFanSpeed.AUTO,
        swing_v: bool = False,
        swing_h: bool = False,
        economy: bool = False,
    ) -> None:
        """Build a whole state, including half-degree set points from 16..31 °C."""
        if temperature is not None:
            temperature_value(temperature, 16, 31, 0.5)
        if not power:
            temperature = 19
        elif mode == PdPioneerClimateMode.FAN_ONLY:
            temperature = 20
        if temperature is None:
            raise ValueError("temperature is required for this mode")
        fan_code = int(PdPioneerClimateFanSpeed(fan))
        odd_fan = _ODD_FANS[fan]
        odd = bytes(
            [
                0x23,
                0xCB,
                0x26,
                2,
                0,
                *odd_fan,
                (8 if swing_v else 0) | (0x90 if swing_h else 0),
                0xC3,
                0,
                0,
                0,
                0,
            ]
        )
        target = temperature
        even = bytes(
            [
                0x23,
                0xCB,
                0x26,
                1,
                0,
                (0x25 if economy else 0x24) if power else 0xA0,
                int(PdPioneerClimateMode(mode)) if power else 1,
                31 - int(target),
                fan_code | (0x38 if swing_v else 0),
                0,
                0,
                0,
                128 | (4 if target % 1 else 0),
            ]
        )
        super().__init__(
            data=odd + bytes([(sum(odd) + 15) & 255]) + even + bytes([sum(even) & 255])
        )

    @property
    def economy(self) -> bool:
        """Return the economy power setting."""
        return self.data[19] == 0x25

    @classmethod
    def parse(cls, data: bytes) -> PdPioneerClimateState:
        """Check both burst types, checksums and duplicated fan/swing fields."""
        if len(data) != cls.LENGTH:
            raise ValueError("incomplete Pioneer state")
        odd, even = data[:14], data[14:]
        if (
            odd[:5] != bytes([0x23, 0xCB, 0x26, 2, 0])
            or even[:5] != bytes([0x23, 0xCB, 0x26, 1, 0])
            or (sum(odd[:-1]) + 15) & 255 != odd[-1]
            or sum(even[:-1]) & 255 != even[-1]
        ):
            raise ValueError("invalid Pioneer burst signature or checksum")
        fan = PdPioneerClimateFanSpeed(even[8] & 7)
        if (
            tuple(odd[5:7]) != _ODD_FANS[fan]
            or bool(odd[7] & 8) != (even[8] & 0x38 == 0x38)
            or even[5] not in (0x24, 0x25, 0xA0)
        ):
            raise ValueError("inconsistent Pioneer state bursts")
        mode = PdPioneerClimateMode(even[6])
        temp = 31 - even[7] + (0.5 if even[12] & 4 else 0)
        temperature_value(temp, 16, 31, 0.5)
        power = even[5] != 0xA0
        return PdPioneerClimateState(
            power=power,
            mode=mode if power else None,
            temperature=temp
            if power and mode != PdPioneerClimateMode.FAN_ONLY
            else None,
            fan=fan,
            swing_v=bool(odd[7] & 8),
            swing_h=odd[7] & 0x90 == 0x90,
        )
