"""TCL 112-bit air-conditioner state commands."""

from ._climate import ClimatePacket
from ._climate_fields import decoded, selection, temperature_value
from .climate import (
    ClimateFan,
    ClimateMode,
    ClimateState,
)
from .pioneer_wyt import PioneerWytCommand

_MODES = {
    ClimateMode.HEAT: 1,
    ClimateMode.DRY: 2,
    ClimateMode.COOL: 3,
    ClimateMode.FAN_ONLY: 7,
    ClimateMode.AUTO: 8,
}
_FANS = {
    ClimateFan.QUIET: 1,
    ClimateFan.AUTO: 0,
    ClimateFan.LOW: 2,
    ClimateFan.MEDIUM: 3,
    ClimateFan.HIGH: 5,
}


class Tcl112Command(ClimatePacket):
    """TCL state with half-degree temperature and vertical swing."""

    HEADER = PioneerWytCommand.HEADER
    TIMING = PioneerWytCommand.TIMING
    LENGTH = 14
    GAP = 1650

    def __init__(
        self,
        *,
        mode: ClimateMode,
        temperature: float,
        power: bool = True,
        fan: ClimateFan = ClimateFan.AUTO,
        swing_v: bool = False,
    ) -> None:
        """Build a state for 16..31 °C in half degrees."""
        temperature_value(temperature, 16, 31, 0.5)
        data = bytes(
            [
                0x23,
                0xCB,
                0x26,
                1,
                0,
                0x20 | (4 if power else 0),
                selection(mode, _MODES) if power else 3,
                31 - int(temperature),
                0x40 | selection(fan, _FANS) | (0x38 if swing_v else 0),
                0,
                0,
                0,
                0x20 if temperature % 1 else 0,
            ]
        )
        super().__init__(data=data + bytes([self.checksum(data)]))

    @classmethod
    def parse(cls, data: bytes) -> ClimateState:
        """Read a validated state, including the half-degree bit."""
        super().parse(data)
        if data[:2] != b"\x23\xcb":
            raise ValueError("invalid TCL signature")
        temperature = 31 - (data[7] & 15) + (0.5 if data[12] & 32 else 0)
        temperature_value(temperature, 16, 31, 0.5)
        return ClimateState(
            power=bool(data[5] & 4),
            mode=decoded(data[6] & 15, _MODES) if data[5] & 4 else None,
            temperature=temperature,
            fan=decoded(data[8] & 7, _FANS),
            swing_v=data[8] & 0x38 == 0x38,
        )
