"""TCL 112-bit air-conditioner state commands."""

from dataclasses import dataclass
from enum import IntEnum

from ._climate import ClimatePacket
from ._climate_fields import decoded, selection, temperature_value
from .pioneer_wyt import PioneerWytCommand


class Tcl112Mode(IntEnum):
    """Tcl112 operating modes."""

    HEAT = 0x1
    DRY = 0x2
    COOL = 0x3
    FAN_ONLY = 0x7
    AUTO = 0x8


class Tcl112FanSpeed(IntEnum):
    """Tcl112 fan speeds."""

    QUIET = 0x1
    AUTO = 0x0
    LOW = 0x2
    MEDIUM = 0x3
    HIGH = 0x5


@dataclass(frozen=True, kw_only=True)
class Tcl112State:
    """Settings carried by a Tcl112 packet, using its native enums and units."""

    power: bool | None = None
    mode: Tcl112Mode | None = None
    temperature: float | None = None
    fan: Tcl112FanSpeed | None = None
    swing_v: bool | None = None
    swing_h: bool | None = None
    is_fahrenheit: bool = False


_MODES = {
    Tcl112Mode.HEAT: 1,
    Tcl112Mode.DRY: 2,
    Tcl112Mode.COOL: 3,
    Tcl112Mode.FAN_ONLY: 7,
    Tcl112Mode.AUTO: 8,
}
_FANS = {
    Tcl112FanSpeed.QUIET: 1,
    Tcl112FanSpeed.AUTO: 0,
    Tcl112FanSpeed.LOW: 2,
    Tcl112FanSpeed.MEDIUM: 3,
    Tcl112FanSpeed.HIGH: 5,
}


class Tcl112Command(ClimatePacket[Tcl112State]):
    """TCL state with half-degree temperature and vertical swing."""

    HEADER = PioneerWytCommand.HEADER
    TIMING = PioneerWytCommand.TIMING
    LENGTH = 14
    GAP = 1650

    def __init__(
        self,
        *,
        mode: Tcl112Mode,
        temperature: float,
        power: bool = True,
        fan: Tcl112FanSpeed = Tcl112FanSpeed.AUTO,
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
    def parse(cls, data: bytes) -> Tcl112State:
        """Read a validated state, including the half-degree bit."""
        cls._validate_packet(data)
        if data[:2] != b"\x23\xcb":
            raise ValueError("invalid TCL signature")
        temperature = 31 - (data[7] & 15) + (0.5 if data[12] & 32 else 0)
        temperature_value(temperature, 16, 31, 0.5)
        return Tcl112State(
            power=bool(data[5] & 4),
            mode=decoded(data[6] & 15, _MODES) if data[5] & 4 else None,
            temperature=temperature,
            fan=decoded(data[8] & 7, _FANS),
            swing_v=data[8] & 0x38 == 0x38,
        )
