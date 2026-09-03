"""Tests for Dyson commands."""

import pytest

from infrared_protocols.commands.dyson import (
    DysonAm09Command,
    DysonCoolCommand,
    _DysonFanCommand,
)

_COOL_RAW_TIMINGS = [
    2440, -870, 850, -1660, 850, -850, 850, -850, 850, -1660, 850, -850, 850, -850,
    850, -850, 850, -850, 850, -850, 850, -850, 850, -850, 850, -850, 850, -850,
    850, -850, 850, -1660, 850,
]  # fmt: skip

_AM09_RAW_TIMINGS = [
    2440, -870, 850, -850, 850, -850, 850, -1660, 850, -1660, 850, -850, 850, -850,
    850, -850, 850, -850, 850, -850, 850, -850, 850, -850, 850, -850, 850, -850,
    850, -850, 850, -1660, 850,
]  # fmt: skip


@pytest.mark.parametrize(
    "command_class",
    [
        pytest.param(DysonCoolCommand, id="cool"),
        pytest.param(DysonAm09Command, id="am09"),
    ],
)
def test_dyson_command_initialization(
    command_class: type[_DysonFanCommand],
) -> None:
    """Verify Dyson commands initialize with default and custom values."""
    cmd = command_class(code=0x01)
    assert cmd.code == 0x01
    assert cmd.modulation == 38000

    cmd_custom = command_class(code=0xFF, modulation=36000)
    assert cmd_custom.code == 0xFF
    assert cmd_custom.modulation == 36000


@pytest.mark.parametrize(
    "command_class",
    [
        pytest.param(DysonCoolCommand, id="cool"),
        pytest.param(DysonAm09Command, id="am09"),
    ],
)
@pytest.mark.parametrize(
    "code",
    [
        pytest.param(-1, id="negative"),
        pytest.param(0x100, id="too_large"),
    ],
)
def test_dyson_command_invalid_code_range(
    command_class: type[_DysonFanCommand], code: int
) -> None:
    """Ensure Dyson commands raise ValueError for out-of-range codes.

    The command code must fit in 8 bits (0 to 0xFF); the device preamble that
    completes the 15-bit frame is supplied by the command class.
    """
    with pytest.raises(ValueError, match="Dyson command code must be a valid 8-bit"):
        command_class(code=code)


@pytest.mark.parametrize(
    ("command_class", "expected_raw_timings"),
    [
        pytest.param(DysonCoolCommand, _COOL_RAW_TIMINGS, id="cool"),
        pytest.param(DysonAm09Command, _AM09_RAW_TIMINGS, id="am09"),
    ],
)
def test_dyson_command_get_raw_timings(
    command_class: type[_DysonFanCommand], expected_raw_timings: list[int]
) -> None:
    """Verify get_raw_timings produces the expected single-frame sequence.

    Each class prepends its own fixed preamble to the same command code, so the
    two sequences differ only in the first seven bits. Timings alternate
    positive (mark) / negative (space) values.
    """
    command = command_class(code=0x01)
    timings = command.get_raw_timings()

    assert timings == expected_raw_timings
    assert command.modulation == 38000
