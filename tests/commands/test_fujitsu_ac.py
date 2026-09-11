"""Tests for the Fujitsu General air-conditioner IR command."""

import pytest

from infrared_protocols.commands.fujitsu_ac import (
    MAX_TEMP_F,
    MIN_TEMP_F,
    FujitsuAcCommand,
    FujitsuAcFanSpeed,
    FujitsuAcMode,
    FujitsuAcProtocol,
    FujitsuAcSwing,
    temperature_step,
)

# Physical-layer constants are duplicated here rather than imported
# so the tests are independent
_HDR_MARK = 3300
_HDR_SPACE = 1600
_BIT_MARK = 420
_BIT_ONE_SPACE = 1200
_BIT_ZERO_SPACE = 420
_TRL_MARK = 420
_TRL_SPACE = 8000

_ONE_THRESHOLD = (_BIT_ONE_SPACE + _BIT_ZERO_SPACE) // 2

# Last byte of a state message; the checksum covers bytes 7 up to it.
_CHECKSUM_BYTE = 15

# Bit strings in transmission order, from the captures documented in the ESPHome
# fujitsu_general component. Bytes 0-7 and 11-14 are identical in every state message,
# so each case below only names the three state bytes and the checksum that vary.
_STATE_PREFIX = "".join(
    [
        "00101000",
        "11000110",
        "00000000",
        "00001000",
        "00001000",
        "01111111",
        "10010000",
        "00001100",
    ]
)
_STATE_MIDDLE = "".join(["00000000", "00000000", "00000000", "00000100"])

_OFF_BITS = "".join(
    [
        "00101000",
        "11000110",
        "00000000",
        "00001000",
        "00001000",
        "01000000",
        "10111111",
    ]
)

# Every documented state capture, as (byte 8, byte 9, byte 10, checksum) with the state
# it encodes.
_STATE_CAPTURES = [
    pytest.param(
        "10000100",
        "00000000",
        "00000000",
        "11110001",
        True,
        FujitsuAcMode.AUTO,
        18,
        FujitsuAcFanSpeed.AUTO,
        FujitsuAcSwing.OFF,
        id="turn_on_auto_18",
    ),
    pytest.param(
        "10001100",
        "00000000",
        "00000000",
        "11111110",
        True,
        FujitsuAcMode.AUTO,
        19,
        FujitsuAcFanSpeed.AUTO,
        FujitsuAcSwing.OFF,
        id="turn_on_auto_19",
    ),
    pytest.param(
        "10000111",
        "00000000",
        "00000000",
        "11110011",
        True,
        FujitsuAcMode.AUTO,
        30,
        FujitsuAcFanSpeed.AUTO,
        FujitsuAcSwing.OFF,
        id="turn_on_auto_30",
    ),
    pytest.param(
        "10000000",
        "00100000",
        "00000000",
        "11010101",
        True,
        FujitsuAcMode.HEAT,
        16,
        FujitsuAcFanSpeed.AUTO,
        FujitsuAcSwing.OFF,
        id="turn_on_heat_16",
    ),
    pytest.param(
        "00000000",
        "00100000",
        "00000000",
        "00110101",
        False,
        FujitsuAcMode.HEAT,
        16,
        FujitsuAcFanSpeed.AUTO,
        FujitsuAcSwing.OFF,
        id="running_heat_16",
    ),
    pytest.param(
        "10000111",
        "10000000",
        "00000000",
        "01110011",
        True,
        FujitsuAcMode.COOL,
        30,
        FujitsuAcFanSpeed.AUTO,
        FujitsuAcSwing.OFF,
        id="turn_on_cool_30",
    ),
    pytest.param(
        "10000111",
        "01000000",
        "00000000",
        "10110011",
        True,
        FujitsuAcMode.DRY,
        30,
        FujitsuAcFanSpeed.AUTO,
        FujitsuAcSwing.OFF,
        id="turn_on_dry_30",
    ),
    pytest.param(
        "10000111",
        "11000000",
        "00000000",
        "00110011",
        True,
        FujitsuAcMode.FAN_ONLY,
        30,
        FujitsuAcFanSpeed.AUTO,
        FujitsuAcSwing.OFF,
        id="turn_on_fan_only_30",
    ),
    pytest.param(
        "10000111",
        "00100000",
        "00000000",
        "11010011",
        True,
        FujitsuAcMode.HEAT,
        30,
        FujitsuAcFanSpeed.AUTO,
        FujitsuAcSwing.OFF,
        id="turn_on_heat_30",
    ),
    pytest.param(
        "10000111",
        "00100000",
        "10000000",
        "01010011",
        True,
        FujitsuAcMode.HEAT,
        30,
        FujitsuAcFanSpeed.HIGH,
        FujitsuAcSwing.OFF,
        id="turn_on_heat_30_high",
    ),
    pytest.param(
        "00000111",
        "00100000",
        "01000000",
        "01010011",
        False,
        FujitsuAcMode.HEAT,
        30,
        FujitsuAcFanSpeed.MEDIUM,
        FujitsuAcSwing.OFF,
        id="running_heat_30_medium",
    ),
    pytest.param(
        "00000111",
        "00100000",
        "11000000",
        "10010011",
        False,
        FujitsuAcMode.HEAT,
        30,
        FujitsuAcFanSpeed.LOW,
        FujitsuAcSwing.OFF,
        id="running_heat_30_low",
    ),
    pytest.param(
        "00000111",
        "00100000",
        "00100000",
        "00010011",
        False,
        FujitsuAcMode.HEAT,
        30,
        FujitsuAcFanSpeed.QUIET,
        FujitsuAcSwing.OFF,
        id="running_heat_30_quiet",
    ),
    pytest.param(
        "00000111",
        "00100000",
        "00101000",
        "00011101",
        False,
        FujitsuAcMode.HEAT,
        30,
        FujitsuAcFanSpeed.QUIET,
        FujitsuAcSwing.VERTICAL,
        id="running_heat_30_quiet_swing_vertical",
    ),
]


def _capture_bits(byte8: str, byte9: str, byte10: str, checksum: str) -> str:
    """Assemble a full state capture from the four bytes that vary between them."""
    return _STATE_PREFIX + byte8 + byte9 + byte10 + _STATE_MIDDLE + checksum


def _bits_to_bytes(bits: str) -> list[int]:
    """Convert a transmission-order bit string into message bytes."""
    return [
        sum(int(bits[8 * i + bit]) << bit for bit in range(8))
        for i in range(len(bits) // 8)
    ]


def _timings_from_bytes(message: list[int]) -> list[int]:
    """Build raw timings for a message without going through the encoder."""
    timings = [_HDR_MARK, -_HDR_SPACE]
    for byte in message:
        for bit in range(8):
            one = (byte >> bit) & 1
            timings += [_BIT_MARK, -(_BIT_ONE_SPACE if one else _BIT_ZERO_SPACE)]
    return timings + [_TRL_MARK, -_TRL_SPACE]


def _transmitted_bits(timings: list[int], byte_count: int) -> str:
    """Recover the transmitted bit string from raw timings, one bit per pair."""
    return "".join(
        "1" if abs(timings[3 + 2 * i]) > _ONE_THRESHOLD else "0"
        for i in range(8 * byte_count)
    )


def _state_checksum(message: list[int]) -> int:
    """Return the state message checksum: the two's complement of bytes 7-14."""
    return -sum(message[7:_CHECKSUM_BYTE]) & 0xFF


def _heat_30_high_bytes() -> list[int]:
    """Return a known-good state message as bytes, for mutation in decode tests."""
    return _bits_to_bytes(_capture_bits("10000111", "00100000", "10000000", "01010011"))


def test_encode_timing_values() -> None:
    """Pin the physical layer: header, bit mark, bit spaces, and trailer."""
    timings = FujitsuAcCommand(temperature=24).get_raw_timings()

    assert timings[:2] == [_HDR_MARK, -_HDR_SPACE]
    assert timings[-2:] == [_TRL_MARK, -_TRL_SPACE]
    assert set(timings[2:-2:2]) == {_BIT_MARK}
    assert set(timings[3:-2:2]) <= {-_BIT_ONE_SPACE, -_BIT_ZERO_SPACE}


@pytest.mark.parametrize(
    ("byte8", "byte9", "byte10", "checksum", "power", "mode", "temp", "fan", "swing"),
    _STATE_CAPTURES,
)
def test_encode_matches_captured_state(
    byte8: str,
    byte9: str,
    byte10: str,
    checksum: str,
    power: bool,
    mode: FujitsuAcMode,
    temp: int,
    fan: FujitsuAcFanSpeed,
    swing: FujitsuAcSwing,
) -> None:
    """Encoded state messages must be bit-identical to the captured ones."""
    timings = FujitsuAcCommand(
        power=power, mode=mode, temperature=temp, fan=fan, swing=swing
    ).get_raw_timings()

    assert _transmitted_bits(timings, 16) == _capture_bits(
        byte8, byte9, byte10, checksum
    )


@pytest.mark.parametrize(
    ("byte8", "byte9", "byte10", "checksum", "power", "mode", "temp", "fan", "swing"),
    _STATE_CAPTURES,
)
def test_decode_captured_state(
    byte8: str,
    byte9: str,
    byte10: str,
    checksum: str,
    power: bool,
    mode: FujitsuAcMode,
    temp: int,
    fan: FujitsuAcFanSpeed,
    swing: FujitsuAcSwing,
) -> None:
    """Captured state messages must decode back to the state they encode."""
    bits = _capture_bits(byte8, byte9, byte10, checksum)

    command = FujitsuAcCommand.from_raw_timings(
        _timings_from_bytes(_bits_to_bytes(bits))
    )

    assert command is not None
    assert command.power is power
    assert command.mode is mode
    assert command.temperature == temp
    assert command.fan is fan
    assert command.swing is swing
    assert command.get_raw_timings() == _timings_from_bytes(_bits_to_bytes(bits))


@pytest.mark.parametrize(
    ("swing", "expected_byte10"),
    [
        pytest.param(FujitsuAcSwing.OFF, 0x00, id="off"),
        pytest.param(FujitsuAcSwing.VERTICAL, 0x10, id="vertical"),
        pytest.param(FujitsuAcSwing.HORIZONTAL, 0x20, id="horizontal"),
        pytest.param(FujitsuAcSwing.BOTH, 0x30, id="both"),
    ],
)
def test_swing_occupies_byte_10_bits_4_and_5(
    swing: FujitsuAcSwing, expected_byte10: int
) -> None:
    """Every swing position must encode into byte 10 and decode back.

    Only OFF and VERTICAL appear in the captures, so all four are checked against the
    documented layout here. The fan is left on AUTO, which is zero, so byte 10 holds
    nothing but the swing.
    """
    timings = FujitsuAcCommand(temperature=24, swing=swing).get_raw_timings()

    message = _bits_to_bytes(_transmitted_bits(timings, 16))
    decoded = FujitsuAcCommand.from_raw_timings(timings)

    assert message[10] == expected_byte10
    assert decoded is not None
    assert decoded.swing is swing


@pytest.mark.parametrize(
    ("clean", "outside_quiet", "expected_byte9", "expected_byte14"),
    [
        pytest.param(False, False, 0x00, 0x20, id="neither"),
        pytest.param(True, False, 0x08, 0x20, id="clean"),
        pytest.param(False, True, 0x00, 0xA0, id="outside_quiet"),
        pytest.param(True, True, 0x08, 0xA0, id="clean_and_outside_quiet"),
    ],
)
def test_clean_and_outside_quiet_occupy_their_own_bits(
    clean: bool, outside_quiet: bool, expected_byte9: int, expected_byte14: int
) -> None:
    """Clean and outside quiet sit in different bytes and must not disturb each other.

    Neither appears in the captures. The mode is left on AUTO, which is zero, so byte 9
    holds nothing but the clean bit, and byte 14 holds bit 5 in every frame.
    """
    timings = FujitsuAcCommand(
        temperature=24, clean=clean, outside_quiet=outside_quiet
    ).get_raw_timings()

    message = _bits_to_bytes(_transmitted_bits(timings, 16))
    decoded = FujitsuAcCommand.from_raw_timings(timings)

    assert message[9] == expected_byte9
    assert message[14] == expected_byte14
    assert decoded is not None
    assert decoded.clean is clean
    assert decoded.outside_quiet is outside_quiet


def test_a_util_message_does_not_decode_as_state() -> None:
    """A util message carries no state, so the state decoder must reject it."""
    timings = _timings_from_bytes(_bits_to_bytes(_OFF_BITS))

    assert FujitsuAcCommand.from_raw_timings(timings) is None


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(
            FujitsuAcCommand(power=True, temperature=18), id="turn_on_auto_18"
        ),
        pytest.param(
            FujitsuAcCommand(
                mode=FujitsuAcMode.HEAT,
                temperature=30,
                fan=FujitsuAcFanSpeed.HIGH,
                swing=FujitsuAcSwing.BOTH,
                clean=True,
                outside_quiet=True,
            ),
            id="heat_30_high_both_clean_quiet",
        ),
        pytest.param(
            FujitsuAcCommand(
                protocol=FujitsuAcProtocol.EXTENDED,
                mode=FujitsuAcMode.COOL,
                temperature=24.5,
            ),
            id="extended_cool_24_5",
        ),
    ],
)
def test_reencoding_a_decoded_command_reproduces_the_burst(
    command: FujitsuAcCommand,
) -> None:
    """Everything the decoder accepts must re-encode to the burst it came from."""
    timings = command.get_raw_timings()

    decoded = FujitsuAcCommand.from_raw_timings(timings)

    assert decoded is not None
    assert decoded.get_raw_timings() == timings


@pytest.mark.parametrize(
    "temperature",
    [pytest.param(15, id="below_min"), pytest.param(31, id="above_max")],
)
def test_temperature_out_of_range(temperature: float) -> None:
    """Out-of-range temperatures must raise ValueError."""
    with pytest.raises(ValueError, match="out of range"):
        FujitsuAcCommand(temperature=temperature)


@pytest.mark.parametrize(
    ("protocol", "temperature"),
    [
        pytest.param(FujitsuAcProtocol.STANDARD, 24.5, id="standard_half_degree"),
        pytest.param(FujitsuAcProtocol.EXTENDED, 24.25, id="extended_quarter_degree"),
    ],
)
def test_temperature_finer_than_the_protocol_can_carry(
    protocol: FujitsuAcProtocol, temperature: float
) -> None:
    """A temperature the field cannot hold exactly must not be silently rounded."""
    with pytest.raises(ValueError, match="not a multiple"):
        FujitsuAcCommand(protocol=protocol, temperature=temperature)


def test_default_modulation() -> None:
    """Default modulation must be 38 kHz."""
    command = FujitsuAcCommand(temperature=24)

    assert command.modulation == 38000
    assert command.repeat_count == 0


@pytest.mark.parametrize(
    ("byte_index", "value"),
    [
        pytest.param(0, 0x15, id="wrong_signature"),
        pytest.param(7, 0x32, id="unknown_protocol"),
        pytest.param(5, 0x7F, id="unknown_message_type"),
        pytest.param(9, 0x05, id="unknown_mode_field"),
        pytest.param(10, 0x05, id="unknown_fan_field"),
        pytest.param(8, 0xF1, id="temperature_above_max"),
        pytest.param(8, 0xDC, id="temperature_off_the_standard_grid"),
        pytest.param(14, 0x00, id="flags_base_bit_clear"),
    ],
)
def test_decode_rejects_invalid_state(byte_index: int, value: int) -> None:
    """A state message that fails a field's validation must not decode.

    The checksum is recomputed over the changed message so that the named field is what
    rejects it. Left stale, every case here would be caught by the checksum instead and
    the field checks would never run.
    """
    message = _heat_30_high_bytes()
    message[byte_index] = value
    message[_CHECKSUM_BYTE] = _state_checksum(message)

    assert FujitsuAcCommand.from_raw_timings(_timings_from_bytes(message)) is None


def test_decode_rejects_bad_state_checksum() -> None:
    """A state message whose checksum does not cover its contents must not decode."""
    message = _heat_30_high_bytes()
    message[_CHECKSUM_BYTE] ^= 0xFF

    assert FujitsuAcCommand.from_raw_timings(_timings_from_bytes(message)) is None


@pytest.mark.parametrize(
    ("index", "value"),
    [
        pytest.param(0, 8000, id="header_mark_too_long"),
        pytest.param(1, -4500, id="header_space_too_long"),
        pytest.param(3, -800, id="bit_space_between_zero_and_one"),
        pytest.param(2, -_BIT_MARK, id="bit_mark_missing"),
    ],
)
def test_decode_rejects_invalid_timings(index: int, value: int) -> None:
    """Timings outside the accepted windows must not decode."""
    timings = _timings_from_bytes(_heat_30_high_bytes())
    timings[index] = value

    assert FujitsuAcCommand.from_raw_timings(timings) is None


@pytest.mark.parametrize(
    "length",
    [pytest.param(0, id="empty"), pytest.param(60, id="shorter_than_common_header")],
)
def test_decode_rejects_truncated_timings(length: int) -> None:
    """Timings too short to hold a message must not decode."""
    timings = _timings_from_bytes(_heat_30_high_bytes())[:length]

    assert FujitsuAcCommand.from_raw_timings(timings) is None


def test_decode_rejects_a_signature_without_a_type_byte() -> None:
    """A burst cut off right after the signature has no type byte to dispatch on."""
    timings = _timings_from_bytes(_heat_30_high_bytes()[:5])

    assert FujitsuAcCommand.from_raw_timings(timings) is None


def test_decode_rejects_a_corrupt_rest_length() -> None:
    """Byte 6 must count the bytes after it, since the checksum does not cover it."""
    message = _heat_30_high_bytes()
    message[6] ^= 0xFF
    message[_CHECKSUM_BYTE] = _state_checksum(message)

    assert FujitsuAcCommand.from_raw_timings(_timings_from_bytes(message)) is None


_EXTENDED_PREFIX = [0x14, 0x63, 0x00, 0x10, 0x10, 0xFE, 0x09, 0x31]

# Captured from a physical ARREW4E remote, which reports protocol 0x31 and steps in
# 0.5 C. Its temperature field is scaled differently from the 0x30 family: the two
# agree only at 24 C, which is why an encoder built for one looks correct there.
_EXTENDED_CAPTURES = [
    pytest.param([0x50, 0x01, 0x01, 0x20, 0x5D], 18.0, id="cool_18_0_the_cool_floor"),
    pytest.param([0x54, 0x01, 0x01, 0x20, 0x59], 18.5, id="cool_18_5"),
    pytest.param([0x80, 0x01, 0x01, 0x20, 0x2D], 24.0, id="cool_24_0"),
    pytest.param([0x84, 0x01, 0x01, 0x20, 0x29], 24.5, id="cool_24_5"),
    pytest.param([0xB0, 0x01, 0x01, 0x20, 0xFD], 30.0, id="cool_30_0_the_ceiling"),
    pytest.param([0x40, 0x04, 0x01, 0x20, 0x6A], 16.0, id="heat_16_0_the_heat_floor"),
]


@pytest.mark.parametrize(("tail", "expected"), _EXTENDED_CAPTURES)
def test_decode_temperature_a_physical_extended_remote_sent(
    tail: list[int], expected: float
) -> None:
    """The 0.5 C scale must come from the frame's own protocol byte."""
    message = [*_EXTENDED_PREFIX, *tail[:3], 0, 0, 0, *tail[3:]]

    command = FujitsuAcCommand.from_raw_timings(_timings_from_bytes(message))

    assert command is not None
    assert command.protocol is FujitsuAcProtocol.EXTENDED
    assert command.temperature == expected


@pytest.mark.parametrize(("tail", "expected"), _EXTENDED_CAPTURES)
def test_encode_temperature_matches_a_physical_extended_remote(
    tail: list[int], expected: float
) -> None:
    """Encoding those temperatures must reproduce the remote's bytes exactly."""
    command = FujitsuAcCommand(
        protocol=FujitsuAcProtocol.EXTENDED,
        temperature=expected,
        mode=FujitsuAcMode(tail[1] & 0x07),
        fan=FujitsuAcFanSpeed(tail[2] & 0x07),
    )

    message = _bits_to_bytes(_transmitted_bits(command.get_raw_timings(), 16))

    assert message[8] == tail[0]
    assert message[15] == tail[4]


# Captured from the same physical ARREW4E remote with its display switched to
# Fahrenheit. The field is the same six bits and spans the same 16-44 range in both
# units, so only the scale changes: 60-88 F against 16-30 C.
_FAHRENHEIT_CAPTURES = [
    pytest.param(0x52, 64.0, id="cool_64f_the_cool_floor"),
    pytest.param(0x7A, 74.0, id="cool_74f"),
    pytest.param(0x7E, 75.0, id="cool_75f"),
    pytest.param(0xB2, 88.0, id="cool_88f_the_ceiling"),
]


@pytest.mark.parametrize(("byte8", "expected"), _FAHRENHEIT_CAPTURES)
def test_decode_fahrenheit_a_physical_remote_sent(byte8: int, expected: float) -> None:
    """The Fahrenheit flag must pick the scale, not just label the value."""
    message = [*_EXTENDED_PREFIX, byte8, 0x01, 0x00, 0, 0, 0, 0x20, 0]
    message[_CHECKSUM_BYTE] = _state_checksum(message)

    command = FujitsuAcCommand.from_raw_timings(_timings_from_bytes(message))

    assert command is not None
    assert command.is_fahrenheit is True
    assert command.temperature == expected


@pytest.mark.parametrize(("byte8", "temperature"), _FAHRENHEIT_CAPTURES)
def test_encode_fahrenheit_matches_a_physical_remote(
    byte8: int, temperature: float
) -> None:
    """Encoding a Fahrenheit setpoint must reproduce the remote's byte exactly."""
    command = FujitsuAcCommand(
        protocol=FujitsuAcProtocol.EXTENDED,
        mode=FujitsuAcMode.COOL,
        temperature=temperature,
        is_fahrenheit=True,
    )

    message = _bits_to_bytes(_transmitted_bits(command.get_raw_timings(), 16))

    assert message[8] == byte8


@pytest.mark.parametrize(
    "temperature",
    [
        pytest.param(MIN_TEMP_F - 1, id="below_min"),
        pytest.param(MAX_TEMP_F + 1, id="above_max"),
    ],
)
def test_fahrenheit_temperature_out_of_range(temperature: float) -> None:
    """The Fahrenheit range is its own, not the Celsius one relabelled."""
    with pytest.raises(ValueError, match="out of range"):
        FujitsuAcCommand(
            protocol=FujitsuAcProtocol.EXTENDED,
            temperature=temperature,
            is_fahrenheit=True,
        )


def test_standard_protocol_has_no_fahrenheit_setting() -> None:
    """Only an EXTENDED remote carries the flag, so the rest cannot be asked for it."""
    with pytest.raises(ValueError, match="no Fahrenheit setting"):
        FujitsuAcCommand(
            protocol=FujitsuAcProtocol.STANDARD, temperature=24, is_fahrenheit=True
        )


def test_decode_rejects_a_standard_frame_claiming_fahrenheit() -> None:
    """A 0x30 frame with the flag set is not something a remote sends."""
    message = _heat_30_high_bytes()
    message[8] |= 0x02
    message[_CHECKSUM_BYTE] = _state_checksum(message)

    assert FujitsuAcCommand.from_raw_timings(_timings_from_bytes(message)) is None


@pytest.mark.parametrize(
    ("protocol", "is_fahrenheit", "expected"),
    [
        pytest.param(FujitsuAcProtocol.STANDARD, False, 1.0, id="standard_celsius"),
        pytest.param(FujitsuAcProtocol.EXTENDED, False, 0.5, id="extended_celsius"),
        pytest.param(FujitsuAcProtocol.EXTENDED, True, 1.0, id="extended_fahrenheit"),
    ],
)
def test_temperature_step(
    protocol: FujitsuAcProtocol, is_fahrenheit: bool, expected: float
) -> None:
    """The step a consumer advertises must match what the remote can express."""
    assert temperature_step(protocol, is_fahrenheit=is_fahrenheit) == expected


def test_the_two_protocols_agree_only_at_24_degrees() -> None:
    """Pin the trap that hid this bug: both families encode 24 C identically."""
    common = {"temperature": 24, "mode": FujitsuAcMode.COOL}
    standard = FujitsuAcCommand(protocol=FujitsuAcProtocol.STANDARD, **common)
    extended = FujitsuAcCommand(protocol=FujitsuAcProtocol.EXTENDED, **common)

    standard_bytes = _bits_to_bytes(_transmitted_bits(standard.get_raw_timings(), 16))
    extended_bytes = _bits_to_bytes(_transmitted_bits(extended.get_raw_timings(), 16))

    assert standard_bytes[8] == extended_bytes[8]
    assert standard_bytes[7] != extended_bytes[7]


@pytest.mark.parametrize("temperature", [18.0, 20.0, 22.0, 26.0, 30.0])
def test_the_two_protocols_disagree_everywhere_else(temperature: float) -> None:
    """Away from 24 C the same temperature is a different field value."""
    common = {"temperature": temperature, "mode": FujitsuAcMode.COOL}
    standard = FujitsuAcCommand(protocol=FujitsuAcProtocol.STANDARD, **common)
    extended = FujitsuAcCommand(protocol=FujitsuAcProtocol.EXTENDED, **common)

    standard_bytes = _bits_to_bytes(_transmitted_bits(standard.get_raw_timings(), 16))
    extended_bytes = _bits_to_bytes(_transmitted_bits(extended.get_raw_timings(), 16))

    assert standard_bytes[8] != extended_bytes[8]


@pytest.mark.parametrize("protocol", list(FujitsuAcProtocol))
@pytest.mark.parametrize("temperature", [18.0, 20.0, 24.0, 30.0])
def test_decode_reads_the_family_out_of_the_frame(
    protocol: FujitsuAcProtocol, temperature: float
) -> None:
    """A frame decodes on its own terms, whichever family sent it.

    This is why an emitter of one family keeps a receiver of the other in sync, and
    why sync alone never proves the configured family is right.
    """
    command = FujitsuAcCommand(
        protocol=protocol, temperature=temperature, mode=FujitsuAcMode.COOL
    )

    decoded = FujitsuAcCommand.from_raw_timings(command.get_raw_timings())

    assert decoded is not None
    assert decoded.protocol is protocol
    assert decoded.temperature == temperature


def test_decode_rejects_truncated_state_message() -> None:
    """A state message cut short after the common header must not decode."""
    # The common header is 6 bytes: its header pair plus 96 bit pairs.
    timings = _timings_from_bytes(_heat_30_high_bytes())[: 2 + 2 * 8 * 6]

    assert FujitsuAcCommand.from_raw_timings(timings) is None


def test_decode_tolerates_measured_receiver_distortion() -> None:
    """Decode must survive the worst distortion measured on real hardware.

    Received from a transmitter running this protocol, bit marks came back as short as
    125 us against their 420 us nominal and zero spaces as long as 688 us, while one
    spaces stayed near 1200. Every bit here is set to that worst case at once, which is
    harsher than anything actually captured.
    """
    timings = _timings_from_bytes(_heat_30_high_bytes())
    for i in range(2, len(timings) - 2, 2):
        timings[i] = 125
        timings[i + 1] = -688 if abs(timings[i + 1]) == _BIT_ZERO_SPACE else -1125

    command = FujitsuAcCommand.from_raw_timings(timings)

    assert command is not None
    assert command.mode is FujitsuAcMode.HEAT
    assert command.temperature == 30
    assert command.fan is FujitsuAcFanSpeed.HIGH


def test_decode_tolerates_stretched_marks() -> None:
    """A receiver's AGC stretches marks, which must not stop a frame decoding."""
    timings = _timings_from_bytes(_heat_30_high_bytes())
    timings[0] = 5000
    for i in range(2, len(timings), 2):
        timings[i] += 150

    command = FujitsuAcCommand.from_raw_timings(timings)

    assert command is not None
    assert command.mode is FujitsuAcMode.HEAT
    assert command.temperature == 30
    assert command.fan is FujitsuAcFanSpeed.HIGH
