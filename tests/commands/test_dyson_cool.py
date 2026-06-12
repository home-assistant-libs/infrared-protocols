"""Tests for Dyson Cool command."""

import pytest

from infrared_protocols.commands.dyson import DysonCoolCommand


def test_dyson_cool_command_initialization() -> None:
    """Verify DysonCoolCommand initializes with default and custom values."""
    cmd = DysonCoolCommand(payload=0x1234)
    assert cmd.payload == 0x1234
    assert cmd.modulation == 38000
    assert cmd.repeat_count == 1

    cmd_custom = DysonCoolCommand(payload=0x7FFF, modulation=36000, repeat_count=3)
    assert cmd_custom.payload == 0x7FFF
    assert cmd_custom.modulation == 36000
    assert cmd_custom.repeat_count == 3


def test_dyson_cool_command_invalid_payload() -> None:
    """Ensure DysonCoolCommand raises ValueError for invalid payloads.

    The Dyson payload must fit in 15 bits (0 to 0x7FFF). This test checks
    that negative values and values >= 0x8000 raise the expected error.
    """
    msg = "Dyson payload must be a valid 15-bit integer"

    with pytest.raises(ValueError, match=msg):
        DysonCoolCommand(payload=-1)

    with pytest.raises(ValueError, match=msg):
        DysonCoolCommand(payload=0x8000)


def test_dyson_cool_command_get_raw_timings() -> None:
    """Verify get_raw_timings produces expected timing sequences.

    This test checks the base timings for a given payload and ensures that
    repeat_count values of 0, 1, and 2 produce the correct concatenated
    timing sequences including the inter-command gap.
    """
    expected_raw_timings = [
        2440,
        870,
        850,
        1660,
        850,
        850,
        850,
        850,
        850,
        850,
        850,
        850,
        850,
        850,
        850,
        850,
        850,
        850,
        850,
        850,
        850,
        850,
        850,
        850,
        850,
        850,
        850,
        850,
        850,
        850,
        850,
        1660,
        850,
    ]

    command = DysonCoolCommand(payload=0x4001, repeat_count=0)
    timings = command.get_raw_timings()

    assert timings == expected_raw_timings
    assert command.modulation == 38000

    command_with_repeats = DysonCoolCommand(
        payload=command.payload,
        repeat_count=1,
    )
    timings_with_repeats = command_with_repeats.get_raw_timings()

    assert timings_with_repeats == [
        *expected_raw_timings,
        108000,
        *expected_raw_timings,
    ]

    command_with_double_repeats = DysonCoolCommand(
        payload=command.payload,
        repeat_count=2,
    )
    timings_with_double_repeats = command_with_double_repeats.get_raw_timings()

    assert timings_with_double_repeats == [
        *expected_raw_timings,
        108000,
        *expected_raw_timings,
        108000,
        *expected_raw_timings,
    ]
