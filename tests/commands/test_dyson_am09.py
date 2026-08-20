"""Tests for Dyson AM09 command."""

import pytest

from infrared_protocols.commands.dyson import DysonAm09Command


def test_dyson_am09_command_initialization() -> None:
    """Verify DysonAm09Command initializes with default and custom values."""
    cmd = DysonAm09Command(payload=0x1801)
    assert cmd.payload == 0x1801
    assert cmd.modulation == 38000

    cmd_custom = DysonAm09Command(payload=0x18FF, modulation=36000)
    assert cmd_custom.payload == 0x18FF
    assert cmd_custom.modulation == 36000


def test_dyson_am09_command_invalid_payload_range() -> None:
    """Ensure DysonAm09Command raises ValueError for out-of-range payloads.

    The Dyson payload must fit in 15 bits (0 to 0x7FFF). This test checks
    that negative values and values >= 0x8000 raise the expected error.
    """
    msg = "Dyson payload must be a valid 15-bit integer"

    with pytest.raises(ValueError, match=msg):
        DysonAm09Command(payload=-1)

    with pytest.raises(ValueError, match=msg):
        DysonAm09Command(payload=0x8000)


def test_dyson_am09_command_invalid_payload_preamble() -> None:
    """Ensure DysonAm09Command rejects payloads with the wrong preamble.

    Every real AM09 code has its upper 7 bits fixed to 0b0011000
    (0x18xx). Payloads that fit in 15 bits but don't start with that
    preamble are not valid AM09 frames and must be rejected.
    """
    msg = "Dyson payload must start with the 0b0011000 preamble"

    with pytest.raises(ValueError, match=msg):
        DysonAm09Command(payload=0x1234)

    with pytest.raises(ValueError, match=msg):
        DysonAm09Command(payload=0x7FFF)


def test_dyson_am09_command_get_raw_timings() -> None:
    """Verify get_raw_timings produces the expected single-frame sequence.

    Timings alternate positive (mark) / negative (space) values.
    """
    expected_raw_timings = [
        2440,
        -870,
        850,
        -850,
        850,
        -850,
        850,
        -1660,
        850,
        -1660,
        850,
        -850,
        850,
        -850,
        850,
        -850,
        850,
        -850,
        850,
        -850,
        850,
        -850,
        850,
        -850,
        850,
        -850,
        850,
        -850,
        850,
        -850,
        850,
        -1660,
        850,
    ]

    command = DysonAm09Command(payload=0x1801)
    timings = command.get_raw_timings()

    assert timings == expected_raw_timings
    assert command.modulation == 38000
