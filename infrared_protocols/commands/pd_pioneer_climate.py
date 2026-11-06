"""Parker Davis/Pioneer climate state in paired odd and even bursts."""

from ._climate import ClimatePacket, FramePart
from ._climate_fields import decoded, selection, temperature_value
from ._timing import PulseTiming
from .climate import (
    ClimateFan,
    ClimateMode,
    ClimateState,
)

_MODES = {
    ClimateMode.HEAT: 1,
    ClimateMode.DRY: 2,
    ClimateMode.COOL: 3,
    ClimateMode.FAN_ONLY: 7,
    ClimateMode.AUTO: 8,
}
_FANS = {
    ClimateFan.AUTO: 0,
    ClimateFan.LOW: 2,
    ClimateFan.MEDIUM: 3,
    ClimateFan.HIGH: 5,
}
_ODD_FANS = {
    ClimateFan.AUTO: (0x40, 0x20),
    ClimateFan.LOW: (0x60, 0x40),
    ClimateFan.MEDIUM: (0x40, 0x60),
    ClimateFan.HIGH: (0x40, 0xC0),
}


class PdPioneerClimateCommand(ClimatePacket):
    """Both bursts are needed to recover horizontal and vertical swing.

    Decoding requires all sections in one capture. Configure the receiver idle
    timeout above 10.01 ms, or join captures with their measured intervening gaps.
    A default 10 ms ESPHome receiver splits this packet; pass the consecutive
    bursts from one press to from_raw_captures() to decode it.
    """

    HEADER = (3120, -1560)
    TIMING = PulseTiming(520, 312, 1066)
    LENGTH = 28
    PARTS = (FramePart(14, HEADER, 10010), FramePart(14, HEADER, 10010))

    def __init__(
        self,
        *,
        mode: ClimateMode,
        temperature: float,
        power: bool = True,
        fan: ClimateFan = ClimateFan.AUTO,
        swing_v: bool = False,
        swing_h: bool = False,
        economy: bool = False,
    ) -> None:
        """Build a whole state, including half-degree set points from 16..31 °C."""
        temperature_value(temperature, 16, 31, 0.5)
        fan_code = selection(fan, _FANS)
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
        target = (
            19 if not power else 20 if mode == ClimateMode.FAN_ONLY else temperature
        )
        even = bytes(
            [
                0x23,
                0xCB,
                0x26,
                1,
                0,
                (0x25 if economy else 0x24) if power else 0xA0,
                selection(mode, _MODES) if power else 1,
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
    def parse(cls, data: bytes) -> ClimateState:
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
        fan = decoded(even[8] & 7, _FANS)
        if (
            tuple(odd[5:7]) != _ODD_FANS[fan]
            or bool(odd[7] & 8) != (even[8] & 0x38 == 0x38)
            or even[5] not in (0x24, 0x25, 0xA0)
        ):
            raise ValueError("inconsistent Pioneer state bursts")
        mode = decoded(even[6], _MODES)
        temp = 31 - even[7] + (0.5 if even[12] & 4 else 0)
        temperature_value(temp, 16, 31, 0.5)
        power = even[5] != 0xA0
        return ClimateState(
            power=power,
            mode=mode if power else None,
            temperature=temp if power and mode != ClimateMode.FAN_ONLY else None,
            fan=fan,
            swing_v=bool(odd[7] & 8),
            swing_h=odd[7] & 0x90 == 0x90,
        )
