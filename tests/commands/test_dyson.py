"""Tests for Dyson commands."""

from collections.abc import Callable
from itertools import product

import pytest

from infrared_protocols.commands.dyson import (
    DysonAm09Command,
    DysonCommand,
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


_DECODE_CASES = [
    pytest.param(cls(code=c), id=f"{cls.__name__}-{c:#04x}")
    for cls, c in product((DysonCoolCommand, DysonAm09Command), (0, 1, 255))
]


@pytest.mark.parametrize("factory", [DysonCoolCommand, DysonAm09Command, DysonCommand])
def test_writable_dyson_button(
    factory: type[DysonCoolCommand] | type[DysonAm09Command] | type[DysonCommand],
) -> None:
    """Changing the public button also changes the transmitted payload."""
    sent = factory(code=1)
    sent.code = 2
    received = factory.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.code == 2
    assert received.button_code == sent.button_code
    assert received.index == sent.index


@pytest.mark.parametrize(
    "sent,decoder",
    [
        pytest.param(
            DysonCoolCommand(code=0x12),
            DysonAm09Command.from_raw_timings,
            id="cool-not-am09",
        ),
        pytest.param(
            DysonAm09Command(code=0x12),
            DysonCoolCommand.from_raw_timings,
            id="am09-not-cool",
        ),
    ],
)
def test_dyson_family_prefix(
    sent: DysonCoolCommand | DysonAm09Command,
    decoder: Callable[[list[int]], DysonCoolCommand | DysonAm09Command | None],
) -> None:
    """A known payload from the other Dyson family is rejected."""
    assert decoder(sent.get_raw_timings()) is None


def test_dyson_shared_payload() -> None:
    """Legacy button tables and the indexed API share one payload decoder."""
    old = DysonCoolCommand(code=0x12)
    received = DysonCommand.from_raw_timings(old.get_raw_timings())
    assert received is not None
    assert (received.button_code, received.index) == (old.button_code, old.index)
    assert (received.code, received.index) == (0x1204, 2)
    assert DysonCommand(code=0x1204, index=2, modulation=38000).modulation == 38000


@pytest.mark.parametrize("command", _DECODE_CASES)
def test_decoder_round_trip_fields(
    command: DysonCoolCommand | DysonAm09Command,
) -> None:
    """Decode edge-valued fields and preserve their protocol meaning."""
    raw = command.get_raw_timings()
    result = type(command).from_raw_timings(raw)
    assert result is not None
    assert result.get_raw_timings() == raw
    assert result.code == command.code


@pytest.mark.parametrize("command", _DECODE_CASES)
@pytest.mark.parametrize("prefix", [0, 1, 5])
def test_decoder_truncated(
    command: DysonCoolCommand | DysonAm09Command, prefix: int
) -> None:
    """A partial leader or payload cannot be a complete command."""
    assert type(command).from_raw_timings(command.get_raw_timings()[:prefix]) is None
