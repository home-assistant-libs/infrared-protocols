<<<<<<< HEAD
import pytest
=======
"""Tests for the Pronto IR commands."""
>>>>>>> origin/main

from infrared_protocols.commands.pronto import ProntoCommand

TEST_DATA_KNOWN_GOOD_RAW_TIMINGS = [
    9100, -4446, 598, -494, 598, -494, 598, -494, 598, -1612, 598, -494, 598, -494, 598,
    -1612, 598, -494, 598, -494, 598, -1612, 598, -494, 598, -494, 598, -494, 598, -494,
    598, -494, 598, -1612, 598, -1612, 598, -494, 598, -494, 598, -494, 598, -494, 598,
    -494, 598, -494, 598, -1612, 598, -494, 598, -494, 598, -494, 598, -1612, 598, -494,
    598, -494, 598, -494, 598, -494, 598, -9984
]  # fmt: skip
TEST_DATA_KNOWN_GOOD_MODULATION = 38000
TEST_DATA_KNOWN_GOOD_REPEATS = 0
<<<<<<< HEAD
TEST_DATA_KNOWN_GOOD_PRONTO = b'\x01Z\x00\xaa\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00?\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00?\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00?\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00?\x00\x16\x00?\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00?\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00?\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x01}'
TEST_DATA_KNOWN_GOOD_PRONTO_REPR = "0000 006d 0022 0000 015a 00aa 0016 0014 0016 0014 0016 0014 0016 003f 0016 0014 0016 0014 0016 003f 0016 0014 0016 0014 0016 003f 0016 0014 0016 0014 0016 0014 0016 0014 0016 0014 0016 003f 0016 003f 0016 0014 0016 0014 0016 0014 0016 0014 0016 0014 0016 0014 0016 003f 0016 0014 0016 0014 0016 0014 0016 003f 0016 0014 0016 0014 0016 0014 0016 0014 0016 017d"
TEST_DATA_KNOWN_GOOD_PRONTO_PREAMBLE = b"\x00\x00\x00\x6d\x00\x22\x00\x00"
TEST_DATA_KNOWN_GOOD_PRONTO_FULL = (
    TEST_DATA_KNOWN_GOOD_PRONTO_PREAMBLE + TEST_DATA_KNOWN_GOOD_PRONTO
)
# The frequency word 006d only approximates 38000 Hz, so the modulation derived
# from the preamble is 38029.
TEST_DATA_KNOWN_GOOD_PRONTO_MODULATION = 38029

def test_encode_pronto_from_timing():
    pronto = ProntoCommand.from_raw_timings(
        TEST_DATA_KNOWN_GOOD_RAW_TIMINGS, TEST_DATA_KNOWN_GOOD_MODULATION
    )
    assert pronto.modulation == TEST_DATA_KNOWN_GOOD_PRONTO_MODULATION
=======
TEST_DATA_KNOWN_GOOD_PRONTO = (
    b"\x01Z\x00\xaa\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00?"
    b"\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00?\x00\x16\x00\x14\x00\x16\x00"
    b"\x14\x00\x16\x00?\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16"
    b"\x00\x14\x00\x16\x00\x14\x00\x16\x00?\x00\x16\x00?\x00\x16\x00\x14\x00\x16"
    b"\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14"
    b"\x00\x16\x00?\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00?"
    b"\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x01}"
)
TEST_DATA_KNOWN_GOOD_PRONTO_REPR = (
    "0000 006d 0022 0000 015a 00aa 0016 0014 0016 0014 0016 0014 0016 003f 0016 0014 "
    "0016 0014 0016 003f 0016 0014 0016 0014 0016 003f 0016 0014 0016 0014 0016 0014 "
    "0016 0014 0016 0014 0016 003f 0016 003f 0016 0014 0016 0014 0016 0014 0016 0014 "
    "0016 0014 0016 0014 0016 003f 0016 0014 0016 0014 0016 0014 0016 003f 0016 0014 "
    "0016 0014 0016 0014 0016 0014 0016 017d"
)


def test_encode_pronto_from_timing() -> None:
    """Test that a ProntoCommand can be constructed."""
    pronto = ProntoCommand.from_raw_timings(TEST_DATA_KNOWN_GOOD_RAW_TIMINGS)
    assert pronto.modulation == TEST_DATA_KNOWN_GOOD_MODULATION
>>>>>>> origin/main
    assert pronto.repeat_count == TEST_DATA_KNOWN_GOOD_REPEATS
    assert pronto.pronto_data == TEST_DATA_KNOWN_GOOD_PRONTO_FULL

<<<<<<< HEAD
def test_decode_pronto_to_timing():
    pronto = ProntoCommand(pronto_data=TEST_DATA_KNOWN_GOOD_PRONTO_FULL)
    assert pronto.modulation == TEST_DATA_KNOWN_GOOD_PRONTO_MODULATION
=======

def test_decode_pronto_to_timing() -> None:
    """Test that a ProntoCommand can be decoded to raw timings."""
    pronto = ProntoCommand(
        timing_data=TEST_DATA_KNOWN_GOOD_PRONTO,
        modulation=TEST_DATA_KNOWN_GOOD_MODULATION,
        repeat_count=TEST_DATA_KNOWN_GOOD_REPEATS,
    )
    assert pronto.modulation == 38000
>>>>>>> origin/main
    assert pronto.repeat_count == TEST_DATA_KNOWN_GOOD_REPEATS
    assert all(
        abs(calculated - expected)
        < 2 * ProntoCommand._time_base(modulation=pronto.modulation)
        for calculated, expected in zip(
            pronto.get_raw_timings(), TEST_DATA_KNOWN_GOOD_RAW_TIMINGS, strict=True
        )
    )

<<<<<<< HEAD
def test_pronto_to_pronto_hex():
=======

def test_pronto_repr() -> None:
    """Test that the repr of a ProntoCommand matches the expected value."""
>>>>>>> origin/main
    pronto = ProntoCommand.from_raw_timings(TEST_DATA_KNOWN_GOOD_RAW_TIMINGS)
    assert pronto.to_pronto_hex() == TEST_DATA_KNOWN_GOOD_PRONTO_REPR

<<<<<<< HEAD
def test_pronto_repr_delegates_to_pronto_hex():
    pronto = ProntoCommand.from_raw_timings(TEST_DATA_KNOWN_GOOD_RAW_TIMINGS)
    assert repr(pronto) == pronto.to_pronto_hex()

def test_decode_pronto_hex():
    pronto = ProntoCommand.from_pronto_hex(TEST_DATA_KNOWN_GOOD_PRONTO_REPR)
    assert pronto.pronto_data == TEST_DATA_KNOWN_GOOD_PRONTO_FULL
    assert pronto.modulation == TEST_DATA_KNOWN_GOOD_PRONTO_MODULATION
    assert pronto.to_pronto_hex() == TEST_DATA_KNOWN_GOOD_PRONTO_REPR

def test_decode_pronto_hex_flexible_formatting():
    pronto = ProntoCommand.from_pronto_hex(
        TEST_DATA_KNOWN_GOOD_PRONTO_REPR.upper().replace(" ", "\n \t")
    )
    assert pronto.pronto_data == TEST_DATA_KNOWN_GOOD_PRONTO_FULL

@pytest.mark.parametrize(
    ("pronto_hex", "repeat_count", "expected_timings"),
    [
        pytest.param(
            "0000 006d 0002 0000 0156 00ab 0015 0015",
            0,
            [8993, -4497, 552, -552],
            id="once_only",
        ),
        pytest.param(
            "0000 006d 0000 0002 0156 00ab 0015 0015",
            0,
            [8993, -4497, 552, -552],
            id="repeat_only",
        ),
        pytest.param(
            "0000 006d 0001 0001 0156 00ab 0015 0015",
            0,
            [8993, -4497],
            id="once_and_repeat",
        ),
        pytest.param(
            "0000 006d 0001 0001 0156 00ab 0015 0015",
            2,
            [8993, -4497, 552, -552, 552, -552],
            id="once_and_repeat_with_repeats",
        ),
        pytest.param(
            "0000 006d 0000 0001 0015 0015",
            2,
            [552, -552, 552, -552, 552, -552],
            id="repeat_only_with_repeats",
        ),
    ],
)
def test_decode_pronto_hex_sequences(
    pronto_hex: str, repeat_count: int, expected_timings: list[int]
):
    pronto = ProntoCommand.from_pronto_hex(pronto_hex, repeat_count=repeat_count)
    assert pronto.modulation == TEST_DATA_KNOWN_GOOD_PRONTO_MODULATION
    assert pronto.repeat_count == repeat_count
    assert pronto.get_raw_timings() == expected_timings

def test_pronto_repeat_without_repeat_sequence():
    with pytest.raises(ValueError):
        ProntoCommand.from_pronto_hex(
            "0000 006d 0002 0000 0156 00ab 0015 0015", repeat_count=1
        )

@pytest.mark.parametrize(
    "pronto_hex",
    [
        pytest.param("0000 006d 0001 0000 0156 zzzz", id="non_hex_word"),
        pytest.param("0000 006d 0001 0000 0156 -001", id="negative_word"),
        pytest.param("0000 006d 0001 0000 0156 015", id="short_word"),
        pytest.param("0000 006d 0001 0000 0156 00015", id="long_word"),
    ],
)
def test_decode_pronto_hex_invalid_format(pronto_hex: str):
    with pytest.raises(ValueError):
        ProntoCommand.from_pronto_hex(pronto_hex)

@pytest.mark.parametrize(
    "pronto_data",
    [
        pytest.param(b"", id="empty"),
        pytest.param(b"\x00", id="odd_byte_count"),
        pytest.param(b"\x00\x00\x00\x6d\x00\x01", id="preamble_too_short"),
        pytest.param(
            b"\x01\x00\x00\x6d\x00\x01\x00\x00\x01\x56\x00\xab",
            id="unsupported_token",
        ),
        pytest.param(
            b"\x00\x00\x00\x00\x00\x01\x00\x00\x01\x56\x00\xab",
            id="zero_frequency",
        ),
        pytest.param(b"\x00\x00\x00\x6d\x00\x00\x00\x00", id="no_burst_pairs"),
        pytest.param(
            b"\x00\x00\x00\x6d\x00\x02\x00\x00\x01\x56\x00\xab",
            id="pair_count_mismatch",
        ),
        pytest.param(
            b"\x00\x00\x00\x6d\x00\x01\x00\x00\x01\x56\x00\x00",
            id="zero_timing_word",
        ),
    ],
)
def test_pronto_invalid_data(pronto_data: bytes):
    with pytest.raises(ValueError):
        ProntoCommand(pronto_data=pronto_data)
=======

def test_pronto_repeats() -> None:
    """Test that a ProntoCommand can be constructed with repeats."""
    # Repeats only work correctly if pronto is constructed using the default
    # constructor, not by using ProntoCommand.from_raw_timings.
    pronto = ProntoCommand(
        timing_data=TEST_DATA_KNOWN_GOOD_PRONTO,
        modulation=TEST_DATA_KNOWN_GOOD_MODULATION,
        repeat_count=2,
    )
    assert pronto.repeat_count == 2
    # 1 base + 2 repeats
    assert len(pronto.get_raw_timings()) == (1 + 2) * len(
        TEST_DATA_KNOWN_GOOD_RAW_TIMINGS
    )
    assert all(
        abs(calculated - expected)
        < 2 * ProntoCommand._time_base(modulation=pronto.modulation)
        for calculated, expected in zip(
            pronto.get_raw_timings(),
            TEST_DATA_KNOWN_GOOD_RAW_TIMINGS * (1 + 2),
            strict=True,
        )
    )
>>>>>>> origin/main
