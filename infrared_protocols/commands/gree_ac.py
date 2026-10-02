"""Gree air-conditioner IR protocol.

A 9000/4500 leader, 562 marks, and 562 and 1687 spaces. Remotes vary around these
values, so the decoder matches bits with a window wide enough to also take a 620
mark and 540/1600 spaces.

A command is a single frame built from two bit blocks separated by a long space:

  leader + block A (35 data bits) + end pulse + ~20100 us space
         + block B (32 data bits) + end pulse

Block A carries the full state; block B carries the swing detail and the checksum.

Bits are sent least-significant first within each field; index 0 below is the first
transmitted bit.

Block A (35 bits):
  bits 0-2:   mode
  bit 3:      power
  bits 4-5:   fan speed
  bit 6:      swing (set while either axis is actually swinging)
  bit 7:      sleep
  bits 8-11:  temperature (temp_c - 16)
  bits 12-19: timer (half hour at 12, hour tens at 13-14, enabled at 15,
              hour units at 16-19; the hour is split into decimal digits)
  bit 20:     turbo
  bit 21:     display light
  bit 22:     anion
  bit 23:     blow
  bits 24-25: fresh-air intake (the fourth value is undefined)
  bits 28,30,33: fixed trailer

Block B (32 bits):
  bit 0:      vertical swing
  bit 4:      horizontal swing
  bit 13:     fixed signature
  bits 28-31: checksum

Block A's bit 6 records whether anything is swinging; block B's bits 0 and 4 say which
axis. Block B's bits latch: they keep the last selected axis after swing is switched
off, so they only describe live movement while block A's bit 6 is set. The checksum is
computed over block B's latched horizontal bit rather than the effective state.

Only part of the state enters the checksum, so many fields do not affect it; see
``_checksum``.
"""

from enum import IntEnum, StrEnum
from typing import Self, override

from . import Command

MIN_TEMP = 16
MAX_TEMP = 30
MIN_TEMP_F = 61
MAX_TEMP_F = 86

MIN_TIMER_HOURS = 0.5
MAX_TIMER_HOURS = 24

_TEMP_OFFSET = 16

_LEADER_MARK = 9000
_LEADER_SPACE = 4500
_BIT_MARK = 562
_BIT_ONE_SPACE = 1687
_BIT_ZERO_SPACE = 562

# Generic Gree framing stays unchanged; YAP1F uses its capture class means.
_YAP1F_LEADER_MARK = 8796
_YAP1F_LEADER_SPACE = 4365
_YAP1F_BIT_MARK = 673
_YAP1F_BIT_ONE_SPACE = 1580
_YAP1F_BIT_ZERO_SPACE = 516
_YAP1F_GAPS = (19500, 39000, 19500)

_FRAME_GAP = 20100

_FRAME_A_BITS = 35
_FRAME_B_BITS = 32
# Timings in one generic frame: leader + block A + mid-gap + block B.
_FRAME_TIMINGS = 2 + 2 * _FRAME_A_BITS + 1 + 1 + 2 * _FRAME_B_BITS + 1
# YAP1F remotes transmit at 38029 Hz; generic stays at 38000.
_YAP1F_MODULATION = 38029
# YAP1F vertical vane positions accepted by ``swing_v_position``.
YAP1F_SWING_POSITIONS = (0, 1, 2, 3, 4, 5, 6, 7, 9, 11)
_YAP1F_ACTIVE_SWING_POSITIONS = (1, 7, 9, 11)
# Block-B byte1 default from all 29 captures: DisplayTemp 0b10, unknown2=0,
# WiFi and bit7 set, IFeel clear (IFeel is ORed in from state, giving 0xC6).
_YAP1F_B1_DEFAULT = 0xC2

_TOLERANCE = 0.35
# Marks are stretched by receiver AGC far more than spaces, so bit timing is matched
# with an absolute window that keeps a zero and a one space apart (562 vs 1687). The
# window is also wide enough to decode remotes emitting a 620 mark and 540/1600
# spaces.
_BIT_TOLERANCE = 350

# Block A field positions (bit index, width), LSB-first within the field.
_A_MODE = (0, 3)
_A_POWER = 3
_A_FAN = (4, 2)
_A_SWING = 6
_A_SLEEP = 7
_A_TEMP = (8, 4)
_A_TIMER_HALF = 12
_A_TIMER_TENS = (13, 2)
_A_TIMER_ENABLED = 15
_A_TIMER_UNITS = (16, 4)
_A_TURBO = 20
_A_DISPLAY = 21
_A_ANION = 22
_A_BLOW = 23
_A_FRESH_AIR = (24, 2)
_A_TEMP_EXTRA_F = 26
_A_USE_FAHRENHEIT = 27
_A_TRAILER = (28, 30, 33)

# Block B field positions.
_B_SWING_V = 0
_B_SWING_H = 4
_B_SWING_H_FIELD = (4, 3)
_B_SIGNATURE = 13
_B1_DISPLAY_TEMP = (8, 2)
_B1_IFEEL = 10
_B1_UNKNOWN2 = (11, 3)
_B1_WIFI = 14
_B1_BIT7 = 15
# The YAP1F CLOCK+TEMP absence flag shares this energy-saving bit (byte 7,
# 0x04); the 2026-10-02 capture shows both functions excluded from the checksum.
_B_ECONO = 26
_B_CHECKSUM = (28, 4)

# The checksum starts from a fixed base rather than zero.
_CHECKSUM_BASE = 10


class GreeAcMode(IntEnum):
    """AC operating mode; value is the mode field at block A bits 0-2."""

    AUTO = 0
    COOL = 1
    DRY = 2
    FAN_ONLY = 3
    HEAT = 4


class GreeAcModel(StrEnum):
    """Wire profile for Gree commands."""

    GENERIC = "generic"
    YAP1F = "yap1f"


class GreeAcFanSpeed(IntEnum):
    """Fan speed; value is the fan field at block A bits 4-5."""

    AUTO = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class GreeAcFreshAir(IntEnum):
    """Fresh-air intake; value is the field at block A bits 24-25.

    The field's fourth value is not produced by the remote and has no known
    meaning, so it is rejected when decoding.
    """

    OFF = 0
    LEVEL_1 = 1
    LEVEL_2 = 2


def _get_field(bits: list[int], start: int, width: int) -> int:
    """Read a LSB-first field of the given width from a bit list."""
    return sum(bits[start + i] << i for i in range(width))


def _set_field(bits: list[int], start: int, width: int, value: int) -> None:
    """Write a LSB-first field of the given width into a bit list."""
    for i in range(width):
        bits[start + i] = (value >> i) & 1


def _pack_timer(bits: list[int], hours: float | None) -> None:
    """Write a timer setting into block A bits 12-19; an off timer leaves them zero."""
    if hours is None:
        return
    whole_hours, half = divmod(round(hours * 2), 2)
    tens, units = divmod(whole_hours, 10)
    bits[_A_TIMER_HALF] = half
    _set_field(bits, *_A_TIMER_TENS, tens)
    bits[_A_TIMER_ENABLED] = 1
    _set_field(bits, *_A_TIMER_UNITS, units)


def _unpack_timer(bits: list[int]) -> float | None:
    """Read the timer from block A bits 12-19, or None when it is off.

    Raises ValueError for a digit or duration the remote cannot produce, so the
    decoder rejects the frame alongside the undefined enum values.
    """
    half = bits[_A_TIMER_HALF]
    tens = _get_field(bits, *_A_TIMER_TENS)
    units = _get_field(bits, *_A_TIMER_UNITS)

    if not bits[_A_TIMER_ENABLED]:
        # The remote zeroes the whole field when the timer is off.
        if half or tens or units:
            raise ValueError("timer bits set while the timer is off")
        return None

    hours = tens * 10 + units + 0.5 * half
    if units > 9 or not MIN_TIMER_HOURS <= hours <= MAX_TIMER_HOURS:
        raise ValueError(
            f"timer {hours} out of range {MIN_TIMER_HOURS}..{MAX_TIMER_HOURS}"
        )
    return hours


def _checksum(frame_a: list[int], frame_b: list[int]) -> int:
    """Return the block B checksum nibble for the two blocks as sent.

    The sum takes the low nibble of the first four and high nibble of the next
    three bytes. All horizontal swing position bits 4-6 therefore contribute to
    the checksum. Temperature, fresh air, and timer units also enter; vertical
    swing and the remaining fields do not.
    """
    total = _CHECKSUM_BASE
    total += sum(_get_field(frame_a, 8 * i, 4) for i in range(4))
    total += sum(_get_field(frame_b, 8 * i + 4, 4) for i in range(3))
    return total & 0xF


def _is_close(actual: int, expected: int, tolerance: float) -> bool:
    """Check if a timing is within the given relative tolerance of the expected."""
    margin = expected * tolerance
    return expected - margin <= actual <= expected + margin


def _decode_bit(mark: int, space: int) -> int | None:
    """Decode one bit from its mark and space, or None if it matches neither."""
    if abs(mark - _BIT_MARK) > _BIT_TOLERANCE:
        return None
    if abs(space - _BIT_ZERO_SPACE) <= _BIT_TOLERANCE:
        return 0
    if abs(space - _BIT_ONE_SPACE) <= _BIT_TOLERANCE:
        return 1
    return None


def _encode_frame(
    bits: list[int],
    *,
    leader: bool,
    leader_mark: int = _LEADER_MARK,
    leader_space: int = _LEADER_SPACE,
    bit_mark: int = _BIT_MARK,
    bit_one_space: int = _BIT_ONE_SPACE,
    bit_zero_space: int = _BIT_ZERO_SPACE,
) -> list[int]:
    """Encode a bit list into raw timings, with or without the leader."""
    timings = [leader_mark, -leader_space] if leader else []
    for bit in bits:
        timings.append(bit_mark)
        timings.append(-(bit_one_space if bit else bit_zero_space))
    timings.append(bit_mark)
    return timings


def _decode_bits(timings: list[int], offset: int, count: int) -> list[int] | None:
    """Decode ``count`` bits starting at ``offset``, or None on any bad bit."""
    bits: list[int] = []
    for i in range(count):
        bit = _decode_bit(timings[offset + 2 * i], abs(timings[offset + 2 * i + 1]))
        if bit is None:
            return None
        bits.append(bit)
    return bits


class GreeAcCommand(Command):
    """Gree air-conditioner IR command.

    ``temperature`` is in whole degrees Celsius (16 to 30), or Fahrenheit (61 to
    86) when ``fahrenheit`` is true.

    ``timer_hours`` is the countdown the remote is set to, 0.5 to 24 in half-hour
    steps, or None when the timer is off.

    ``absence`` (YAP1F only) is the CLOCK+TEMP 8 °C frost-protection flag from
    the 2026-10-02 capture; it shares the energy-saving bit with ``econo``, so
    the wire cannot distinguish the two functions and either one sets the bit.
    """

    power: bool
    mode: GreeAcMode
    temperature: int
    fan: GreeAcFanSpeed
    swing_v: bool
    swing_h: bool
    swing_h_position: int
    fahrenheit: bool
    econo: bool
    absence: bool
    display_temp: int
    turbo: bool
    display: bool
    blow: bool
    sleep: bool
    timer_hours: float | None
    anion: bool
    fresh_air: GreeAcFreshAir
    ifeel: bool
    swing_v_position: int | None
    model: GreeAcModel

    def __init__(
        self,
        *,
        power: bool = True,
        mode: GreeAcMode,
        temperature: int,
        fan: GreeAcFanSpeed = GreeAcFanSpeed.AUTO,
        swing_v: bool = False,
        swing_h: bool | None = None,
        swing_h_position: int | None = None,
        fahrenheit: bool = False,
        econo: bool = False,
        absence: bool = False,
        display_temp: int | None = None,
        turbo: bool = False,
        display: bool = True,
        blow: bool = False,
        sleep: bool = False,
        timer_hours: float | None = None,
        anion: bool = False,
        fresh_air: GreeAcFreshAir = GreeAcFreshAir.OFF,
        ifeel: bool = False,
        swing_v_position: int | None = None,
        model: GreeAcModel = GreeAcModel.GENERIC,
        modulation: int | None = None,
    ) -> None:
        """Initialize the Gree AC IR command."""
        if modulation is None:
            modulation = _YAP1F_MODULATION if model is GreeAcModel.YAP1F else 38000
        super().__init__(modulation=modulation)

        min_temp, max_temp = (
            (MIN_TEMP_F, MAX_TEMP_F) if fahrenheit else (MIN_TEMP, MAX_TEMP)
        )
        if not min_temp <= temperature <= max_temp:
            raise ValueError(
                f"temperature {temperature} out of range {min_temp}..{max_temp}"
            )
        if timer_hours is not None:
            if not MIN_TIMER_HOURS <= timer_hours <= MAX_TIMER_HOURS:
                raise ValueError(
                    f"timer_hours {timer_hours} out of range "
                    f"{MIN_TIMER_HOURS}..{MAX_TIMER_HOURS}"
                )
            if (timer_hours * 2) % 1:
                raise ValueError(f"timer_hours {timer_hours} is not a multiple of 0.5")
        if swing_v_position is not None and (
            model is not GreeAcModel.YAP1F
            or swing_v_position not in YAP1F_SWING_POSITIONS
        ):
            raise ValueError(f"unsupported swing_v_position {swing_v_position}")
        if swing_h_position is None:
            swing_h_position = int(bool(swing_h))
        if swing_h_position not in range(7) and not (
            model is GreeAcModel.YAP1F and swing_h_position in (12, 13)
        ):
            raise ValueError(f"unsupported swing_h_position {swing_h_position}")
        if display_temp is None:
            display_temp = 2 if model is GreeAcModel.YAP1F else 0
        if display_temp not in range(4):
            raise ValueError(f"unsupported display_temp {display_temp}")

        self.power = power
        self.mode = mode
        self.temperature = temperature
        self.fan = fan
        self.swing_v = swing_v
        self.swing_h_position = swing_h_position
        self.swing_h = (
            (swing_h_position in (1, 13) if swing_h is None else swing_h)
            if model is GreeAcModel.YAP1F
            else swing_h_position != 0
        )
        self.fahrenheit = fahrenheit
        self.econo = econo
        self.absence = absence
        self.display_temp = display_temp
        self.turbo = turbo
        self.display = display
        self.blow = blow
        self.sleep = sleep
        self.timer_hours = timer_hours
        self.anion = anion
        self.fresh_air = fresh_air
        self.ifeel = ifeel
        self.swing_v_position = swing_v_position
        self.model = model

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Gree AC command."""
        if self.model is GreeAcModel.YAP1F:
            return self._get_yap1f_raw_timings()
        frame_a, frame_b = self._build_frames()
        return self._encode_signal(frame_a, frame_b)

    def _build_frames(self) -> tuple[list[int], list[int]]:
        """Build the standard 8-byte Gree frame as block A/B bit lists."""
        frame_a = [0] * _FRAME_A_BITS
        _set_field(frame_a, *_A_MODE, self.mode.value)
        frame_a[_A_POWER] = int(self.power)
        _set_field(frame_a, *_A_FAN, self.fan.value)
        frame_a[_A_SWING] = int(self.swing_v or self.swing_h_position != 0)
        frame_a[_A_SLEEP] = int(self.sleep)
        if self.fahrenheit:
            # Keep IRremoteESP8266's +0.6 °F conversion, without float truncation
            # errors at exact Celsius boundaries.
            celsius = min(
                MAX_TEMP, max(MIN_TEMP, ((self.temperature - 32) * 5 + 3) // 9)
            )
            _set_field(frame_a, *_A_TEMP, celsius - _TEMP_OFFSET)
            base_fahrenheit = max(
                MIN_TEMP_F, min(MAX_TEMP_F, celsius * 9 // 5 + 32)
            )
            frame_a[_A_TEMP_EXTRA_F] = self.temperature - base_fahrenheit
            frame_a[_A_USE_FAHRENHEIT] = 1
        else:
            _set_field(frame_a, *_A_TEMP, self.temperature - _TEMP_OFFSET)
        _pack_timer(frame_a, self.timer_hours)
        frame_a[_A_TURBO] = int(self.turbo)
        frame_a[_A_DISPLAY] = int(self.display)
        frame_a[_A_ANION] = int(self.anion)
        frame_a[_A_BLOW] = int(self.blow)
        _set_field(frame_a, *_A_FRESH_AIR, self.fresh_air.value)
        for index in _A_TRAILER:
            frame_a[index] = 1

        frame_b = [0] * _FRAME_B_BITS
        _set_field(
            frame_b, 4, 4 if self.model is GreeAcModel.YAP1F else 3,
            self.swing_h_position,
        )
        if self.model is GreeAcModel.YAP1F:
            swing_v_position = self.swing_v_position
            if swing_v_position is None:
                swing_v_position = int(self.swing_v)
            _set_field(frame_b, 0, 4, swing_v_position)
            frame_a[_A_SWING] = int(self.swing_v or self.swing_h)
            _set_field(frame_b, 8, 8, _YAP1F_B1_DEFAULT)
            frame_b[_B1_IFEEL] = int(self.ifeel)
        else:
            frame_b[_B_SIGNATURE] = 1
            frame_b[_B_SWING_V] = int(self.swing_v)
        _set_field(frame_b, *_B1_DISPLAY_TEMP, self.display_temp)
        # Absence shares the energy-saving bit, so either flag sets it.
        frame_b[_B_ECONO] = int(self.econo or self.absence)
        _set_field(frame_b, *_B_CHECKSUM, _checksum(frame_a, frame_b))
        return frame_a, frame_b

    @staticmethod
    def _encode_signal(
        frame_a: list[int], frame_b: list[int], *, gap: int = _FRAME_GAP
    ) -> list[int]:
        """Encode one standard frame into raw timings with a trailing gap."""
        timings = _encode_frame(frame_a, leader=True)
        timings.append(-gap)
        timings.extend(_encode_frame(frame_b, leader=False))
        timings.append(-gap)
        return timings

    def _get_yap1f_raw_timings(self) -> list[int]:
        """Encode YAP1F's two leader-bearing bursts with capture class means."""
        frame_a, frame_b = self._build_frames()
        fixed_a = [0] * _FRAME_A_BITS
        fixed_a[29] = 1
        fixed_a[31] = 1
        fixed_a[33] = 1
        fixed_b = [0] * _FRAME_B_BITS
        _set_field(fixed_b, *_B_CHECKSUM, _checksum(fixed_a, fixed_b))

        frames = (frame_a, frame_b, fixed_a, fixed_b)
        timings: list[int] = []
        for index, bits in enumerate(frames):
            timings.extend(
                _encode_frame(
                    bits,
                    leader=index in (0, 2),
                    leader_mark=_YAP1F_LEADER_MARK,
                    leader_space=_YAP1F_LEADER_SPACE,
                    bit_mark=_YAP1F_BIT_MARK,
                    bit_one_space=_YAP1F_BIT_ONE_SPACE,
                    bit_zero_space=_YAP1F_BIT_ZERO_SPACE,
                )
            )
            if index < len(_YAP1F_GAPS):
                timings.append(-_YAP1F_GAPS[index])
        return timings

    @classmethod
    def from_raw_timings(
        cls, timings: list[int], *, model: GreeAcModel = GreeAcModel.GENERIC
    ) -> Self | None:
        """Decode raw IR timings into a GreeAcCommand."""
        if model is GreeAcModel.YAP1F:
            return cls._from_yap1f_raw_timings(timings)
        # Block A: leader (2) + 35 bit pairs (70) + end mark (1).
        frame_a_len = 2 + 2 * _FRAME_A_BITS + 1
        # Then the mid-frame gap (1), then block B: 32 bit pairs (64) + end mark (1).
        if len(timings) < frame_a_len + 1 + 2 * _FRAME_B_BITS + 1:
            return None

        if not _is_close(timings[0], _LEADER_MARK, _TOLERANCE) or not _is_close(
            abs(timings[1]), _LEADER_SPACE, _TOLERANCE
        ):
            return None

        frame_a = _decode_bits(timings, 2, _FRAME_A_BITS)
        if frame_a is None:
            return None
        if abs(timings[2 + 2 * _FRAME_A_BITS] - _BIT_MARK) > _BIT_TOLERANCE:
            return None

        # The mid-frame gap is a space, so it must be negative as well as long.
        if timings[frame_a_len] >= 0 or not _is_close(
            abs(timings[frame_a_len]), _FRAME_GAP, _TOLERANCE
        ):
            return None

        frame_b_start = frame_a_len + 1
        frame_b = _decode_bits(timings, frame_b_start, _FRAME_B_BITS)
        if frame_b is None:
            return None
        if abs(timings[frame_b_start + 2 * _FRAME_B_BITS] - _BIT_MARK) > _BIT_TOLERANCE:
            return None

        for index in _A_TRAILER:
            if frame_a[index] != 1:
                return None
        if frame_b[_B_SIGNATURE] != 1:
            return None

        # The checksum sums block B's high nibbles, including the full horizontal
        # swing field, whether or not block A marks that axis active.
        if _get_field(frame_b, *_B_CHECKSUM) != _checksum(frame_a, frame_b):
            return None

        # The mode, fan, fresh-air and timer fields are wider than the values the
        # protocol defines.
        try:
            mode = GreeAcMode(_get_field(frame_a, *_A_MODE))
            fan = GreeAcFanSpeed(_get_field(frame_a, *_A_FAN))
            fresh_air = GreeAcFreshAir(_get_field(frame_a, *_A_FRESH_AIR))
            timer_hours = _unpack_timer(frame_a)
        except ValueError:
            return None

        temperature_c = _get_field(frame_a, *_A_TEMP) + _TEMP_OFFSET
        fahrenheit = bool(frame_a[_A_USE_FAHRENHEIT])
        temperature = temperature_c
        if fahrenheit:
            temperature = max(
                MIN_TEMP_F,
                min(
                    MAX_TEMP_F,
                    int(temperature_c * 9 / 5 + 32)
                    + int(bool(frame_a[_A_TEMP_EXTRA_F])),
                ),
            )
        if fahrenheit and not MIN_TEMP_F <= temperature <= MAX_TEMP_F:
            return None
        if not fahrenheit and not MIN_TEMP <= temperature <= MAX_TEMP:
            return None

        display_temp = _get_field(frame_b, *_B1_DISPLAY_TEMP)
        swing_h_position = _get_field(frame_b, *_B_SWING_H_FIELD)
        power = bool(frame_a[_A_POWER])
        # Block B's fields latch their last values after the corresponding swing is
        # stopped; block A says whether either axis is currently active.
        swinging = bool(frame_a[_A_SWING])
        swing_v = swinging and bool(frame_b[_B_SWING_V])
        swing_h_position = swing_h_position if swinging else 0

        return cls(
            power=power,
            mode=mode,
            temperature=temperature,
            fahrenheit=fahrenheit,
            fan=fan,
            swing_v=swing_v,
            swing_h_position=swing_h_position,
            econo=bool(frame_b[_B_ECONO]),
            display_temp=display_temp,
            turbo=bool(frame_a[_A_TURBO]),
            display=bool(frame_a[_A_DISPLAY]),
            blow=bool(frame_a[_A_BLOW]),
            sleep=bool(frame_a[_A_SLEEP]),
            timer_hours=timer_hours,
            anion=bool(frame_a[_A_ANION]),
            fresh_air=fresh_air,
        )

    @classmethod
    def _from_yap1f_raw_timings(cls, timings: list[int]) -> Self | None:
        a_length = 2 + 2 * _FRAME_A_BITS + 1
        b_length = 2 * _FRAME_B_BITS + 1
        if len(timings) == 3 * (a_length + b_length) + 5:
            companion_start = a_length + b_length + 2
            companion_a = _decode_bits(timings, companion_start + 2, _FRAME_A_BITS)
            companion_b = _decode_bits(
                timings, companion_start + a_length + 1, _FRAME_B_BITS
            )
            state_a = _decode_bits(timings, 2, _FRAME_A_BITS)
            if companion_a is None or companion_b is None or state_a is None:
                return None
            expected_a = list(state_a)
            expected_a[28] = 0
            expected_a[29] = 1
            if (
                companion_a != expected_a
                or _get_field(companion_b, *_B_CHECKSUM)
                != _checksum(companion_a, companion_b)
                or not _is_close(
                    timings[companion_start], _YAP1F_LEADER_MARK, _TOLERANCE
                )
                or not _is_close(
                    abs(timings[companion_start + 1]), _YAP1F_LEADER_SPACE, _TOLERANCE
                )
                or abs(timings[companion_start + a_length - 1] - _YAP1F_BIT_MARK)
                > _BIT_TOLERANCE
                or abs(timings[companion_start + a_length + b_length] - _YAP1F_BIT_MARK)
                > _BIT_TOLERANCE
                or timings[companion_start + a_length] >= 0
                or not _is_close(
                    abs(timings[companion_start + a_length]),
                    _YAP1F_GAPS[0], _TOLERANCE,
                )
                or timings[companion_start + a_length + b_length + 1] >= 0
                or not _is_close(
                    abs(timings[companion_start + a_length + b_length + 1]),
                    _YAP1F_GAPS[1], _TOLERANCE,
                )
            ):
                return None
            return cls._from_yap1f_raw_timings(
                timings[:companion_start]
                + timings[companion_start + a_length + b_length + 2 :]
            )
        if len(timings) != 2 * (a_length + b_length) + len(_YAP1F_GAPS):
            return None

        offsets = (
            0,
            a_length + 1,
            a_length + b_length + 2,
            2 * a_length + b_length + 3,
        )
        lengths = (a_length, b_length, a_length, b_length)
        for burst in range(4):
            offset = offsets[burst]
            frame = timings[offset : offset + lengths[burst]]
            if burst in (0, 2) and (
                not _is_close(frame[0], _YAP1F_LEADER_MARK, _TOLERANCE)
                or not _is_close(abs(frame[1]), _YAP1F_LEADER_SPACE, _TOLERANCE)
            ):
                return None
            bit_offset = 2 if burst in (0, 2) else 0
            bit_count = _FRAME_A_BITS if burst in (0, 2) else _FRAME_B_BITS
            if any(
                abs(frame[bit_offset + 2 * index] - _YAP1F_BIT_MARK)
                > _BIT_TOLERANCE
                for index in range(bit_count)
            ):
                return None
            bits = _decode_bits(frame, bit_offset, bit_count)
            end_mark = bit_offset + 2 * bit_count
            if bits is None or abs(frame[end_mark] - _YAP1F_BIT_MARK) > _BIT_TOLERANCE:
                return None
            if burst < 3:
                gap_index = offset + lengths[burst]
                gap = timings[gap_index]
                if gap >= 0 or not _is_close(abs(gap), _YAP1F_GAPS[burst], _TOLERANCE):
                    return None
            if burst in (0, 2):
                frame_a = bits
            else:
                frame_b = bits
            if burst == 1:
                state_a, state_b = frame_a, frame_b
            if burst == 3:
                fixed_a, fixed_b = frame_a, frame_b

        expected_fixed_a = [0] * _FRAME_A_BITS
        expected_fixed_a[29] = 1
        expected_fixed_a[31] = 1
        expected_fixed_a[33] = 1
        expected_fixed_b = [0] * _FRAME_B_BITS
        _set_field(
            expected_fixed_b,
            *_B_CHECKSUM,
            _checksum(expected_fixed_a, expected_fixed_b),
        )
        if (fixed_a, fixed_b) != (expected_fixed_a, expected_fixed_b):
            return None
        if any(state_a[index] != 1 for index in _A_TRAILER):
            return None
        # Byte 8's low bits carry the display-source field and the I-Feel flag,
        # so both are excluded from the constant check.
        if (
            _get_field(state_b, 8, 8) & ~0x07 != _YAP1F_B1_DEFAULT & ~0x07
            or _get_field(state_b, 16, 8) != 0
            or _get_field(state_b, 24, 2) != 0
            or _get_field(state_b, 27, 1) != 0
            or _get_field(state_b, *_B_CHECKSUM) != _checksum(state_a, state_b)
        ):
            return None
        swing_v_position = _get_field(state_b, 0, 4)
        if swing_v_position not in YAP1F_SWING_POSITIONS:
            return None

        generic_b = list(state_b)
        generic_b[_B_SIGNATURE] = 1
        _set_field(generic_b, *_B_CHECKSUM, _checksum(state_a, generic_b))
        first = cls.from_raw_timings(cls._encode_signal(state_a, generic_b))
        if first is None:
            return None
        return cls(
            power=first.power,
            mode=first.mode,
            temperature=first.temperature,
            fahrenheit=first.fahrenheit,
            fan=first.fan,
            swing_v=first.swing_v,
            swing_h=bool(state_a[_A_SWING])
            and swing_v_position not in _YAP1F_ACTIVE_SWING_POSITIONS,
            swing_h_position=_get_field(state_b, 4, 4),
            swing_v_position=swing_v_position,
            econo=first.econo,
            # The shared bit cannot be told apart on the wire; a YAP1F frame
            # with it set reads as both functions.
            absence=first.econo,
            display_temp=first.display_temp,
            turbo=first.turbo,
            display=first.display,
            blow=first.blow,
            sleep=first.sleep,
            timer_hours=first.timer_hours,
            anion=first.anion,
            fresh_air=first.fresh_air,
            ifeel=bool(state_b[_B1_IFEEL]),
            model=GreeAcModel.YAP1F,
        )
