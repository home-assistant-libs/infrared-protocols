"""Daikin ARC 312-bit climate state and sensor query commands."""

from dataclasses import dataclass
from enum import IntEnum
from typing import Self

from ._climate import ClimatePacket, FramePart
from ._climate_fields import temperature_value
from ._daikin import checked, validate_sections
from ._timing import PulseTiming, Reader, pack_bytes
from .daikin_ac import DaikinAcFanSpeed, DaikinAcMode


@dataclass(frozen=True, kw_only=True)
class DaikinArcState:
    """Settings carried by a DaikinArc packet, using its native enums and units."""

    power: bool | None = None
    mode: DaikinAcMode | None = None
    temperature: float | None = None
    fan: DaikinAcFanSpeed | None = None
    swing_v: bool | None = None
    swing_h: bool | None = None


def _state_packet(
    *,
    mode: DaikinAcMode | None,
    temperature: float | None,
    power: bool,
    fan: DaikinAcFanSpeed,
    swing_v: bool,
    swing_h: bool,
) -> bytearray:
    """Build the ARC state section before humidity and checksum fields."""
    if power:
        DaikinAcMode(mode)
    if temperature is not None:
        temperature_value(temperature, 10, 30, 0.5)
    if power and mode in (DaikinAcMode.AUTO, DaikinAcMode.DRY):
        effective_temp = 0xC0
    elif power and mode == DaikinAcMode.FAN_ONLY:
        effective_temp = 0x32
    else:
        if temperature is None:
            raise ValueError("temperature is required for this mode and power state")
        effective_temp = int(temperature * 2)
    return bytearray(
        [
            0x11,
            0xDA,
            0x27,
            0,
            0,
            int(DaikinAcMode(mode)) << 4 | 1 if power else 0,
            effective_temp,
            0,
            (int(DaikinAcFanSpeed(fan))) << 4 | (15 if swing_v else 0),
            15 if swing_h else 0,
            0,
            6,
            0x60,
            0,
            0,
            0xC0,
            0,
            0,
        ]
    )


def _parse_state(data: bytes) -> DaikinArcState:
    """Decode ARC settings without treating fixed temperatures as set points."""
    power = bool(data[5] & 1)
    mode = DaikinAcMode(data[5] >> 4) if power else None
    temperature = (
        None if data[6] == 0xC0 or mode == DaikinAcMode.FAN_ONLY else data[6] / 2
    )
    if temperature is not None:
        temperature_value(temperature, 10, 30, 0.5)
    return DaikinArcState(
        power=bool(data[5] & 1),
        mode=mode,
        temperature=temperature,
        fan=DaikinAcFanSpeed(data[8] >> 4),
        swing_v=bool(data[8] & 15),
        swing_h=bool(data[9] & 15),
    )


class DaikinHumidity(IntEnum):
    """Wire humidity selections; automatic is not a numeric percentage."""

    OFF = 0
    PERCENT_40 = 40
    PERCENT_45 = 45
    PERCENT_50 = 50
    AUTO = 255


class DaikinArcCommand(ClimatePacket[DaikinArcState]):
    """Two-section ARC state with humidity selection.

    Decoding requires all sections in one capture. Configure the receiver idle
    timeout above 35 ms, or join captures with their measured intervening gaps.
    A default 10 ms ESPHome receiver splits this packet; pass the consecutive
    bursts from one press to from_raw_captures() to decode it.
    """

    HEADER = (9950, -25100, 3450, -1760)
    TIMING = PulseTiming(400, 480, 1300)
    LENGTH = 39
    PARTS = (FramePart(20, HEADER, 35000), FramePart(19, (3450, -1760)))

    def __init__(
        self,
        *,
        mode: DaikinAcMode | None,
        temperature: float | None = None,
        power: bool = True,
        fan: DaikinAcFanSpeed = DaikinAcFanSpeed.AUTO,
        swing_v: bool = False,
        swing_h: bool = False,
        humidity: DaikinHumidity = DaikinHumidity.OFF,
        humidity_changed: bool = False,
    ) -> None:
        """Build a state; humidity_changed records an explicit humidity adjustment."""
        state = _state_packet(
            mode=mode,
            temperature=temperature,
            power=power,
            fan=fan,
            swing_v=swing_v,
            swing_h=swing_h,
        )
        state[5] |= 8
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
    def humidity_changed(self) -> bool:
        """Return whether this powered-on command explicitly adjusts humidity."""
        return bool(self.data[9] & 0x10)

    @property
    def humidity(self) -> DaikinHumidity:
        """Return the target humidity selection."""
        return DaikinHumidity(self.data[27])

    @classmethod
    def parse(cls, data: bytes) -> DaikinArcState:
        """Validate both frame checksums and decode common settings."""
        validate_sections(data, (20, 19))
        if data[4] != 2 or data[24] != 0:
            raise ValueError("unexpected Daikin ARC frame type")
        DaikinHumidity(data[27])
        return _parse_state(data[20:])


class DaikinArcQueryCommand(ClimatePacket[DaikinArcState]):
    """ARC sensor query packet."""

    HEADER = DaikinArcCommand.HEADER
    TIMING = DaikinArcCommand.TIMING
    LENGTH = 8

    def __init__(self) -> None:
        """Build the fixed query."""
        super().__init__(data=checked(bytes([0x11, 0xDA, 0x27, 0, 0x84, 0x87, 0x20])))

    @classmethod
    def parse(cls, data: bytes) -> DaikinArcState:
        """Recognize a sensor query without inventing climate state."""
        validate_sections(data, (8,))
        if data[4:7] != bytes([0x84, 0x87, 0x20]):
            raise ValueError("invalid Daikin query")
        return DaikinArcState()


@dataclass(frozen=True, kw_only=True)
class DaikinArcSensorResponse:
    """Received ARC sensor packet; only the indoor temperature is identified.

    The response is not a climate command and its integrity field is unknown.
    Preserve its bytes without claiming checksum verification or exposing the
    unidentified sensor fields as measured values.
    """

    data: bytes
    known_bits: int = 192

    def __post_init__(self) -> None:
        """Validate the identified response structure."""
        if (
            len(self.data) != 24
            or self.data[:5] != bytes([0x11, 0xDA, 0x27, 0, 0])
            or self.known_bits not in (191, 192)
            or self.known_bits == 191
            and self.data[-1] & 128
        ):
            raise ValueError("invalid Daikin ARC sensor response")

    @property
    def inside_temperature(self) -> int:
        """Return the reported indoor temperature in degrees Celsius."""
        return self.data[5]

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Recognize sensor replies, preserving a missing final bit as unknown.

        A 385/386-entry receiver capture omits the last bit space. Its unknown
        high bit is stored as zero; known_bits distinguishes it from a measured zero.
        """
        reader = Reader(timings=timings)
        try:
            reader.expect(3450, -1760)
            count = 191 if len(timings) in (385, 386) else 192
            values = reader.read_bits(DaikinArcCommand.TIMING, count)
            data = pack_bytes(values + ([0] if count == 191 else []), lsb=True)
            reader.expect(400)
            reader.end()
        except ValueError:
            return None
        if data[:5] != bytes([0x11, 0xDA, 0x27, 0, 0]):
            return None
        return cls(data=data, known_bits=count)
