"""TCL 112-bit air-conditioner state commands."""

from dataclasses import dataclass
from enum import IntEnum

from ._climate import ClimatePacket
from ._climate_fields import temperature_value
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


class Tcl112Command(ClimatePacket[Tcl112State]):
    """TCL state with half-degree temperature and vertical swing."""

    HEADER = PioneerWytCommand.HEADER
    TIMING = PioneerWytCommand.TIMING
    LENGTH = 14
    GAP = 1650

    def __init__(
        self,
        *,
        mode: Tcl112Mode | None,
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
                int(Tcl112Mode(mode)) if power else 3,
                31 - int(temperature),
                0x40 | int(Tcl112FanSpeed(fan)) | (0x38 if swing_v else 0),
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
            mode=Tcl112Mode(data[6] & 15) if data[5] & 4 else None,
            temperature=temperature,
            fan=Tcl112FanSpeed(data[8] & 7),
            swing_v=data[8] & 0x38 == 0x38,
        )
