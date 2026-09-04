"""Tests for the AEHA physical layer."""

import pytest

from infrared_protocols.commands.aeha import AEHA_NOMINAL, AehaCommand, AehaTiming

# Physical-layer constants are duplicated here rather than imported
# so the tests are independent
_BASE_UNIT = 425
_LEADER_MARK = 8 * _BASE_UNIT
_LEADER_SPACE = 4 * _BASE_UNIT
_BIT_MARK = _BASE_UNIT
_ZERO_SPACE = _BASE_UNIT
_ONE_SPACE = 3 * _BASE_UNIT
_TRAILER_SPACE = 8000


class _VariantCommand(AehaCommand):
    """A variant whose vendor rounded the base unit differently."""

    TIMING = AehaTiming(
        leader_mark=3300,
        leader_space=1600,
        bit_mark=420,
        zero_space=420,
        one_space=1200,
    )


def _timings_for(data: bytes, timing: AehaTiming = AEHA_NOMINAL) -> list[int]:
    """Build raw timings for a payload without going through the encoder."""
    timings = [timing.leader_mark, -timing.leader_space]
    for byte in data:
        for bit in range(8):
            one = (byte >> bit) & 1
            timings += [
                timing.bit_mark,
                -(timing.one_space if one else timing.zero_space),
            ]
    return timings + [timing.bit_mark, -timing.trailer_space]


def test_nominal_timings() -> None:
    """The default timings must be the nominal 8T/4T leader and 1T/3T bits."""
    timings = AehaCommand(data=b"\x01").get_raw_timings()

    assert timings[:2] == [_LEADER_MARK, -_LEADER_SPACE]
    assert timings[-2:] == [_BIT_MARK, -_TRAILER_SPACE]
    assert set(timings[2:-2:2]) == {_BIT_MARK}
    assert set(timings[3:-2:2]) <= {-_ONE_SPACE, -_ZERO_SPACE}


def test_bytes_are_sent_least_significant_bit_first() -> None:
    """A payload byte must go out with its low bit first."""
    timings = AehaCommand(data=b"\x01").get_raw_timings()

    spaces = [abs(space) for space in timings[3:-2:2]]

    assert spaces == [_ONE_SPACE] + [_ZERO_SPACE] * 7


def test_default_modulation() -> None:
    """Default modulation must be 38 kHz."""
    command = AehaCommand(data=b"\x00")

    assert command.modulation == 38000
    assert command.repeat_count == 0


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(b"\x00", id="single_zero_byte"),
        pytest.param(b"\xff", id="single_full_byte"),
        pytest.param(b"\x14\x63\x00\x10\x10\x02\xfd", id="seven_bytes"),
        pytest.param(bytes(range(16)), id="sixteen_bytes"),
    ],
)
def test_roundtrip(data: bytes) -> None:
    """Encoding then decoding a payload must return it unchanged."""
    timings = AehaCommand(data=data).get_raw_timings()

    assert AehaCommand._decode_data(timings) == data


def test_variant_timings_are_used_for_both_directions() -> None:
    """A subclass's timings must drive its encoding and its decoding."""
    command = _VariantCommand(data=b"\x14\x63")
    timings = command.get_raw_timings()

    assert timings[:2] == [3300, -1600]
    assert _VariantCommand._decode_data(timings) == b"\x14\x63"


def test_variants_within_receiver_tolerance_decode_each_other() -> None:
    """Variants that differ by less than a receiver's own error are interchangeable.

    The tolerances are wide enough to absorb real receiver distortion, which is larger
    than the gap between two vendors' roundings of the base unit. A protocol built on
    this layer therefore has to identify itself from its payload, not from its timings.
    """
    nominal = AehaCommand(data=b"\x14").get_raw_timings()

    assert _VariantCommand._decode_data(nominal) == b"\x14"


@pytest.mark.parametrize(
    ("index", "value"),
    [
        pytest.param(0, 9000, id="leader_mark_too_long"),
        pytest.param(0, 500, id="leader_mark_too_short"),
        pytest.param(1, -4500, id="leader_space_too_long"),
        pytest.param(1, -600, id="leader_space_too_short"),
    ],
)
def test_decode_rejects_bad_leader(index: int, value: int) -> None:
    """A burst that does not open with the leader must not decode."""
    timings = _timings_for(b"\x14\x63")
    timings[index] = value

    assert AehaCommand._decode_data(timings) is None


@pytest.mark.parametrize(
    "timings",
    [
        pytest.param([], id="empty"),
        pytest.param([_LEADER_MARK], id="leader_mark_only"),
        pytest.param([_LEADER_MARK, -_LEADER_SPACE], id="leader_only"),
    ],
)
def test_decode_rejects_too_short(timings: list[int]) -> None:
    """Timings with no payload at all must not decode."""
    assert AehaCommand._decode_data(timings) is None


def test_decode_rejects_partial_byte() -> None:
    """A burst that stops mid-byte cannot be trusted, so it must not decode."""
    timings = _timings_for(b"\x14\x63")
    # Drop the last three bit pairs, leaving 13 bits.
    truncated = timings[: 2 + 2 * 13]

    assert AehaCommand._decode_data(truncated) is None


def test_decode_stops_at_the_trailer() -> None:
    """The trailer's long space ends the payload rather than decoding as a bit."""
    timings = _timings_for(b"\x14\x63")

    assert AehaCommand._decode_data(timings) == b"\x14\x63"
    assert len(timings) == 2 + 2 * 16 + 2


def test_decode_stops_at_the_first_timing_that_is_not_a_bit() -> None:
    """Whatever follows a whole payload ends it, the trailer being one such thing.

    The trailer is not special-cased, so a burst that runs into another signal, or into
    noise, still yields the bytes it did carry as long as they are whole.
    """
    timings = _timings_for(b"\x14\x63")[:-2] + [_BIT_MARK, -900, _BIT_MARK, -900]

    assert AehaCommand._decode_data(timings) == b"\x14\x63"


@pytest.mark.parametrize(
    ("mark", "space", "expected"),
    [
        pytest.param(_BIT_MARK, _ZERO_SPACE, b"\x00", id="nominal_zero"),
        pytest.param(_BIT_MARK, _ONE_SPACE, b"\xff", id="nominal_one"),
        pytest.param(75, _ZERO_SPACE, b"\x00", id="mark_at_lower_edge"),
        pytest.param(775, _ZERO_SPACE, b"\x00", id="mark_at_upper_edge"),
        pytest.param(_BIT_MARK, 775, b"\x00", id="zero_space_at_upper_edge"),
        pytest.param(_BIT_MARK, 925, b"\xff", id="one_space_at_lower_edge"),
    ],
)
def test_decode_accepts_distorted_bits(mark: int, space: int, expected: bytes) -> None:
    """Bits inside the tolerance windows must decode, however distorted."""
    timings = [_LEADER_MARK, -_LEADER_SPACE]
    for _ in range(8):
        timings += [mark, -space]
    timings += [_BIT_MARK, -_TRAILER_SPACE]

    assert AehaCommand._decode_data(timings) == expected


@pytest.mark.parametrize(
    ("mark", "space"),
    [
        pytest.param(20, _ZERO_SPACE, id="mark_below_window"),
        pytest.param(900, _ZERO_SPACE, id="mark_above_window"),
        pytest.param(_BIT_MARK, 810, id="space_between_zero_and_one"),
        pytest.param(_BIT_MARK, 1700, id="space_above_one"),
    ],
)
def test_decode_rejects_bits_outside_the_windows(mark: int, space: int) -> None:
    """A first bit that matches neither window leaves no payload to decode."""
    timings = [_LEADER_MARK, -_LEADER_SPACE]
    for _ in range(8):
        timings += [mark, -space]
    timings += [_BIT_MARK, -_TRAILER_SPACE]

    assert AehaCommand._decode_data(timings) is None


def test_decode_rejects_a_foreign_burst() -> None:
    """Timings that are not AEHA at all must not decode."""
    assert AehaCommand._decode_data([500, -500, 300, -300]) is None


def test_timing_is_immutable() -> None:
    """Timings are a value object, so a variant cannot be mutated in place."""
    with pytest.raises(AttributeError):
        AEHA_NOMINAL.bit_mark = 999  # type: ignore[misc]


def test_empty_payload_encodes_to_leader_and_trailer_only() -> None:
    """An empty payload must still produce a well-formed, if useless, burst."""
    timings = AehaCommand(data=b"").get_raw_timings()

    assert timings == [_LEADER_MARK, -_LEADER_SPACE, _BIT_MARK, -_TRAILER_SPACE]
    assert AehaCommand._decode_data(timings) is None
