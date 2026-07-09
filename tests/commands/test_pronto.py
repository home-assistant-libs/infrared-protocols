"""Tests for Pronto HEX command support."""

import pytest

from infrared_protocols.commands.pronto import (
    ProntoCode,
    ProntoCommand,
    ProntoError,
    decode_pronto_hex,
    encode_pronto_hex,
)

SIMPLE_PRONTO_HEX = "0000 006D 0002 0000 0156 00AB 0015 0015"
SIMPLE_RAW_TIMINGS = (8993, -4497, 552, -552)
RAW_TIMINGS = (9000, -4500, 562, -562)


def _assert_timings_close(
    actual: list[int] | tuple[int, ...],
    expected: list[int] | tuple[int, ...],
    *,
    tolerance: int = 30,
) -> None:
    """Assert raw timings are close enough after Pronto rounding."""
    assert len(actual) == len(expected)

    for actual_timing, expected_timing in zip(actual, expected, strict=True):
        assert abs(actual_timing - expected_timing) <= tolerance


def test_decode_pronto_hex() -> None:
    """Test decoding learned/raw Pronto HEX."""
    decoded = decode_pronto_hex(SIMPLE_PRONTO_HEX)

    assert isinstance(decoded, ProntoCode)
    assert decoded.modulation == 38029
    assert decoded.timings == SIMPLE_RAW_TIMINGS


def test_pronto_command_from_pronto_hex() -> None:
    """Test creating a Pronto command from Pronto HEX."""
    command = ProntoCommand(pronto_hex=SIMPLE_PRONTO_HEX)

    assert command.modulation == 38029
    assert command.repeat_count == 0
    assert command.get_raw_timings() == list(SIMPLE_RAW_TIMINGS)


def test_pronto_command_normalizes_pronto_hex() -> None:
    """Test Pronto HEX is normalized."""
    command = ProntoCommand(pronto_hex=SIMPLE_PRONTO_HEX.lower())

    assert command.to_pronto_hex() == SIMPLE_PRONTO_HEX
    assert str(command) == SIMPLE_PRONTO_HEX


def test_encode_pronto_hex() -> None:
    """Test encoding signed raw timings as Pronto HEX."""
    assert (
        encode_pronto_hex(RAW_TIMINGS, 38_000, trailing_gap_us=None)
        == SIMPLE_PRONTO_HEX
    )


def test_pronto_command_from_raw_timings() -> None:
    """Test creating a Pronto command from signed raw timings."""
    command = ProntoCommand.from_raw_timings(
        RAW_TIMINGS,
        modulation=38_000,
        trailing_gap_us=None,
    )

    assert command.to_pronto_hex() == SIMPLE_PRONTO_HEX
    assert command.modulation == 38029
    _assert_timings_close(command.get_raw_timings(), RAW_TIMINGS)


def test_pronto_command_repeats_full_timing_sequence() -> None:
    """Test repeat count repeats the full raw timing sequence."""
    command = ProntoCommand(pronto_hex=SIMPLE_PRONTO_HEX, repeat_count=2)

    assert command.repeat_count == 2
    assert command.get_raw_timings() == list(SIMPLE_RAW_TIMINGS) * 3


def test_encode_pronto_hex_adds_default_trailing_gap() -> None:
    """Test an odd timing count gets a default trailing gap."""
    pronto_hex = encode_pronto_hex([9000, -4500, 562], 38_000)

    words = pronto_hex.split()
    assert words[:4] == ["0000", "006D", "0002", "0000"]

    command = ProntoCommand(pronto_hex=pronto_hex)
    timings = command.get_raw_timings()

    assert len(timings) == 4
    assert timings[2] > 0
    assert timings[3] < 0
    assert abs(abs(timings[3]) - 100_000) <= 30


def test_encode_pronto_hex_rejects_odd_timings_without_trailing_gap() -> None:
    """Test odd timing counts are rejected without a trailing gap."""
    with pytest.raises(ProntoError):
        encode_pronto_hex([9000, -4500, 562], 38_000, trailing_gap_us=None)


@pytest.mark.parametrize(
    "pronto_hex",
    [
        "",
        "0100 006D 0002 0000 0156 00AB 0015 0015",
        "0000 0000 0002 0000 0156 00AB 0015 0015",
        "0000 006D 0000 0000",
        "0000 006D 0002 0000 0156 00AB",
        "0000 006D 0001 0000 0000 00AB",
        "0000 006D 0001 0000 0156 ZZZZ",
        "0000 006D 0001 0000 0156 -001",
        "0000 006D 0001 0000 0156 10000",
    ],
)
def test_decode_pronto_hex_rejects_invalid_data(pronto_hex: str) -> None:
    """Test invalid Pronto HEX data is rejected."""
    with pytest.raises(ProntoError):
        decode_pronto_hex(pronto_hex)


@pytest.mark.parametrize("modulation", [0, -1, True, 38_000.0])
def test_encode_pronto_hex_rejects_invalid_modulation(
    modulation: int | float | bool,
) -> None:
    """Test invalid modulation values are rejected."""
    with pytest.raises(ProntoError):
        encode_pronto_hex(RAW_TIMINGS, modulation)


@pytest.mark.parametrize(
    "timings",
    [
        [],
        [9000, 0],
        [True, -4500],
        [9000.0, -4500],
    ],
)
def test_encode_pronto_hex_rejects_invalid_timings(
    timings: list[int | float | bool],
) -> None:
    """Test invalid raw timing values are rejected."""
    with pytest.raises(ProntoError):
        encode_pronto_hex(timings, 38_000)

def test_decode_pronto_hex_rejects_short_header() -> None:
    """Test Pronto HEX shorter than the header is rejected."""
    with pytest.raises(ProntoError):
        decode_pronto_hex("0000 006D 0001")

@pytest.mark.parametrize("modulation", [1, 1_000_000_000])
def test_encode_pronto_hex_rejects_unencodable_modulation(
    modulation: int,
) -> None:
    """Test modulation values outside Pronto frequency-word range are rejected."""
    with pytest.raises(ProntoError):
        encode_pronto_hex(RAW_TIMINGS, modulation)

@pytest.mark.parametrize(
    "timings",
    [
        [1, -1],
        [10_000_000, -10_000_000],
    ],
)
def test_encode_pronto_hex_rejects_unencodable_timings(
    timings: list[int],
) -> None:
    """Test timings outside Pronto timing-word range are rejected."""
    with pytest.raises(ProntoError):
        encode_pronto_hex(timings, 38_000)

def test_encode_pronto_hex_rejects_too_many_timing_pairs() -> None:
    """Test timing pair count must fit in a Pronto word."""
    timings = [562, -562] * 65_536

    with pytest.raises(ProntoError):
        encode_pronto_hex(timings, 38_000)
