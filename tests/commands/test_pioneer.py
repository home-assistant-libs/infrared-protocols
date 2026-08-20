"""Tests for the Pioneer IR command encoder."""

import pytest

from infrared_protocols.commands.nec import NECCommand
from infrared_protocols.commands.pioneer import (
    PIONEER_FRAME_PERIOD_US,
    PioneerCommand,
)

# An NEC frame, and therefore a Pioneer frame, is 67 timing entries.
FRAME_ENTRIES = 67


def _nec_frame(address: int, command: int) -> list[int]:
    """Build the NEC frame a Pioneer frame is expected to match."""
    return NECCommand(address=address, command=command).get_raw_timings()


def test_pioneer_command_single_frame() -> None:
    """A command without a preamble is one NEC frame at Pioneer's carrier.

    Pioneer receivers such as the SX-Q180 address their buttons directly, with
    no preamble frame.
    """
    command = PioneerCommand(address=0xA6, command=0x01)
    timings = command.get_raw_timings()
    assert timings == _nec_frame(0xA6, 0x01)
    assert len(timings) == FRAME_ENTRIES
    assert command.modulation == 40000


def test_pioneer_command_two_part() -> None:
    """A two-part command sends its preamble frame, a gap, then the button.

    These values are a power press captured from a Pioneer CU-MJO11 MiniDisc
    remote: preamble 0xA3/0x91 selects the command set, 0xAF/0x60 is power.
    """
    preamble_frame = _nec_frame(0xA3, 0x91)
    command_frame = _nec_frame(0xAF, 0x60)
    gap = PIONEER_FRAME_PERIOD_US - sum(abs(t) for t in preamble_frame)

    command = PioneerCommand(
        address=0xAF,
        command=0x60,
        preamble_address=0xA3,
        preamble_command=0x91,
    )
    assert command.get_raw_timings() == [*preamble_frame, -gap, *command_frame]


def test_pioneer_command_frame_period() -> None:
    """Each frame plus the gap that follows it must span the frame period."""
    timings = PioneerCommand(
        address=0xAF,
        command=0x60,
        preamble_address=0xA3,
        preamble_command=0x91,
    ).get_raw_timings()
    first_frame = timings[:FRAME_ENTRIES]
    gap = timings[FRAME_ENTRIES]
    assert sum(abs(t) for t in first_frame) + abs(gap) == PIONEER_FRAME_PERIOD_US


def test_pioneer_command_repeat_resends_the_whole_command() -> None:
    """Repeating a two-part command resends the preamble as well.

    Captures of held keys show the preamble and button frames alternating,
    not the button frame repeating on its own.
    """
    preamble_frame = _nec_frame(0xA3, 0x91)
    timings = PioneerCommand(
        address=0xAF,
        command=0x60,
        preamble_address=0xA3,
        preamble_command=0x91,
        repeat_count=1,
    ).get_raw_timings()

    # Four frames of 67 entries, separated by three gaps.
    assert len(timings) == 4 * FRAME_ENTRIES + 3
    assert timings[:FRAME_ENTRIES] == preamble_frame
    third_frame_start = 2 * (FRAME_ENTRIES + 1)
    assert timings[third_frame_start : third_frame_start + FRAME_ENTRIES] == (
        preamble_frame
    )


def test_pioneer_command_repeat_without_preamble() -> None:
    """Repeating a single-frame command resends just that frame."""
    timings = PioneerCommand(
        address=0xA6, command=0x01, repeat_count=2
    ).get_raw_timings()
    assert len(timings) == 3 * FRAME_ENTRIES + 2


@pytest.mark.parametrize(
    ("preamble_address", "preamble_command"),
    [
        pytest.param(0xA3, None, id="address_without_command"),
        pytest.param(None, 0x91, id="command_without_address"),
    ],
)
def test_pioneer_command_rejects_half_a_preamble(
    preamble_address: int | None, preamble_command: int | None
) -> None:
    """A preamble needs both of its fields, since it is a whole frame."""
    with pytest.raises(ValueError):
        PioneerCommand(
            address=0xAF,
            command=0x60,
            preamble_address=preamble_address,
            preamble_command=preamble_command,
        )


@pytest.mark.parametrize(
    ("kwargs"),
    [
        pytest.param({"address": -1, "command": 0x00}, id="address_negative"),
        pytest.param({"address": 0x100, "command": 0x00}, id="address_too_large"),
        pytest.param({"address": 0xA6, "command": -1}, id="command_negative"),
        pytest.param({"address": 0xA6, "command": 0x100}, id="command_too_large"),
        pytest.param(
            {
                "address": 0xAF,
                "command": 0x60,
                "preamble_address": 0x100,
                "preamble_command": 0x91,
            },
            id="preamble_address_too_large",
        ),
        pytest.param(
            {
                "address": 0xAF,
                "command": 0x60,
                "preamble_address": 0xA3,
                "preamble_command": 0x100,
            },
            id="preamble_command_too_large",
        ),
    ],
)
def test_pioneer_command_rejects_out_of_range(kwargs: dict[str, int]) -> None:
    """Pioneer addresses and commands are all 8-bit."""
    with pytest.raises(ValueError):
        PioneerCommand(**kwargs)
