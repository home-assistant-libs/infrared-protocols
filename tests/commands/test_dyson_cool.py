"""Tests for Dyson Cool command."""

import pytest

from infrared_protocols.commands.dyson import DysonCoolCommand


def test_dyson_cool_command_initialization() -> None:
    """Verify DysonCoolCommand initializes with default and custom values."""
    cmd = DysonCoolCommand(payload=0x4801)
    assert cmd.payload == 0x4801
    assert cmd.modulation == 38000

    cmd_custom = DysonCoolCommand(payload=0x48FF, modulation=36000)
    assert cmd_custom.payload == 0x48FF
    assert cmd_custom.modulation == 36000


def test_dyson_cool_command_invalid_payload_range() -> None:
    """Ensure DysonCoolCommand raises ValueError for out-of-range payloads.

    The Dyson payload must fit in 15 bits (0 to 0x7FFF). This test checks
    that negative values and values >= 0x8000 raise the expected error.
    """
    msg = "Dyson payload must be a valid 15-bit integer"

    with pytest.raises(ValueError, match=msg):
        DysonCoolCommand(payload=-1)

    with pytest.raises(ValueError, match=msg):
        DysonCoolCommand(payload=0x8000)


def test_dyson_cool_command_invalid_payload_preamble() -> None:
    """Ensure DysonCoolCommand rejects payloads with the wrong preamble.

    Every real Dyson code has its upper 7 bits fixed to 0b1001000
    (0x48xx). Payloads that fit in 15 bits but don't start with that
    preamble are not valid Dyson frames and must be rejected.
    """
    msg = "Dyson payload must start with the 0b1001000 preamble"

    with pytest.raises(ValueError, match=msg):
        DysonCoolCommand(payload=0x1234)

    with pytest.raises(ValueError, match=msg):
        DysonCoolCommand(payload=0x7FFF)


def test_dyson_cool_command_get_raw_timings() -> None:
    """Verify get_raw_timings produces the expected single-frame sequence.

    Timings alternate positive (mark) / negative (space) values.
    """
    expected_raw_timings = [
        2440,
        -870,
        850,
        -1660,
        850,
        -850,
        850,
        -850,
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

    command = DysonCoolCommand(payload=0x4801)
    timings = command.get_raw_timings()

    assert timings == expected_raw_timings
    assert command.modulation == 38000
