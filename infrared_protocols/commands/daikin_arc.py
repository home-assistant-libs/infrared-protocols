"""Daikin ARC 312-bit climate state and sensor query commands."""

from enum import IntEnum

from ._climate import ClimatePacket, FramePart
from ._timing import PulseTiming
from .climate import ClimateFan, ClimateMode, ClimateState
from .daikin import checked, parse_state, state_packet, validate_sections


class DaikinHumidity(IntEnum):
    """Wire humidity selections; automatic is not a numeric percentage."""

    OFF = 0
    PERCENT_40 = 40
    PERCENT_45 = 45
    PERCENT_50 = 50
    AUTO = 255


class DaikinArcCommand(ClimatePacket):
    """Two-section ARC state with humidity selection."""

    HEADER = (9950, -25100, 3450, -1760)
    TIMING = PulseTiming(400, 480, 1300)
    LENGTH = 39
    PARTS = (FramePart(20, HEADER, 35000), FramePart(19, (3450, -1760)))

    def __init__(
        self,
        *,
        mode: ClimateMode,
        temperature: float,
        power: bool = True,
        fan: ClimateFan = ClimateFan.AUTO,
        swing_v: bool = False,
        swing_h: bool = False,
        humidity: DaikinHumidity = DaikinHumidity.OFF,
        humidity_changed: bool = False,
    ) -> None:
        """Build a state; humidity_changed records an explicit humidity adjustment."""
        state = state_packet(
            mode=mode,
            temperature=temperature,
            power=power,
            fan=fan,
            swing_v=swing_v,
            swing_h=swing_h,
        )
        state[5] |= 8
        if mode == ClimateMode.AUTO and power:
            state[6] = 0xC0
        state[7] = DaikinHumidity(humidity)
        state[14:18] = bytes([10, 0xC4, 0x80, 0x24])
        header = bytes(
            [
                0x11,
                0xDA,
                0x27,
                0,
                2,
                0xD0,
                2,
                3,
                128,
                0x13 if humidity_changed and power else 3,
                0x82,
                0x30,
                0x41,
                0x1F,
                0x82,
                0xF4,
                0,
                0x24,
                0,
            ]
        )
        super().__init__(data=checked(header) + checked(bytes(state)))

    @property
    def humidity(self) -> DaikinHumidity:
        """Return the target humidity selection."""
        return DaikinHumidity(self.data[27])

    @classmethod
    def parse(cls, data: bytes) -> ClimateState:
        """Validate both frame checksums and decode common settings."""
        validate_sections(data, (20, 19))
        if data[4] != 2 or data[24] != 0:
            raise ValueError("unexpected Daikin ARC frame type")
        DaikinHumidity(data[27])
        return parse_state(data[20:])


class DaikinArcQueryCommand(ClimatePacket):
    """ARC sensor query packet."""

    HEADER = DaikinArcCommand.HEADER
    TIMING = DaikinArcCommand.TIMING
    LENGTH = 8

    def __init__(self) -> None:
        """Build the fixed query."""
        super().__init__(data=checked(bytes([0x11, 0xDA, 0x27, 0, 0x84, 0x87, 0x20])))

    @classmethod
    def parse(cls, data: bytes) -> ClimateState:
        """Recognize a sensor query without inventing climate state."""
        validate_sections(data, (8,))
        if data[4:7] != bytes([0x84, 0x87, 0x20]):
            raise ValueError("invalid Daikin query")
        return ClimateState()
