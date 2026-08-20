"""Tests for the Proton IR command encoder."""

import pytest

from infrared_protocols.commands.proton import (
    MID_FRAME_GAP,
    ONE_LOW,
    ZERO_LOW,
    ProtonCommand,
)

# A power press captured from an NEC RU-M124 projector remote, which a second
# NEC television remote agrees on.
NEC_DISPLAY_POWER_TIMINGS: list[int] = [
    8000, -4000, 500, -500, 500, -500, 500, -1500, 500, -500,
    500, -1500, 500, -1500, 500, -1500, 500, -1500, 500, -4000,
    500, -500, 500, -1500, 500, -500, 500, -500, 500, -1500,
    500, -500, 500, -1500, 500, -500, 500,
]  # fmt: skip

# Leader (2) + 8 address pairs (16) + mid-frame (2) + 8 command pairs (16) + stop.
FRAME_ENTRIES = 37


def test_proton_command_get_raw_timings_nec_display_power() -> None:
    """Test Proton timings for an NEC display power press."""
    command = ProtonCommand(address=0xF4, command=0x52)
    assert command.get_raw_timings() == NEC_DISPLAY_POWER_TIMINGS
    assert command.modulation == 38500


def test_proton_command_frame_shape() -> None:
    """The frame carries a mid-frame gap as long as the leader's space."""
    timings = ProtonCommand(address=0x00, command=0x00).get_raw_timings()
    assert len(timings) == FRAME_ENTRIES
    assert timings[18] == 500
    assert timings[19] == -MID_FRAME_GAP


@pytest.mark.parametrize(
    ("address", "expected_space"),
    [
        pytest.param(0x01, -ONE_LOW, id="lsb_set"),
        pytest.param(0x80, -ZERO_LOW, id="msb_set"),
    ],
)
def test_proton_command_is_lsb_first(address: int, expected_space: int) -> None:
    """Fields go out least significant bit first.

    This is what separates Proton from the same frame shape in
    ``GEACCommand``, which sends its bits the other way round.
    """
    timings = ProtonCommand(address=address, command=0x00).get_raw_timings()
    assert timings[3] == expected_space


@pytest.mark.parametrize(
    ("address", "command"),
    [
        pytest.param(0x00, 0x00, id="all_clear"),
        pytest.param(0xFF, 0xFF, id="all_set"),
        pytest.param(0xF4, 0x52, id="nec_display_power"),
        pytest.param(0x01, 0x80, id="opposite_ends"),
    ],
)
def test_proton_command_round_trip(address: int, command: int) -> None:
    """Encoding then decoding must return the original fields."""
    timings = ProtonCommand(address=address, command=command).get_raw_timings()
    decoded = ProtonCommand.from_raw_timings(timings)
    assert decoded is not None
    assert decoded.address == address
    assert decoded.command == command


def test_proton_command_from_raw_timings_accepts_receiver_jitter() -> None:
    """A captured frame decodes despite its timings drifting from the ideal."""
    captured = [
        8108, -4054, 490, -512, 490, -512, 490, -1535, 490, -512,
        490, -1535, 490, -1535, 490, -1535, 490, -1535, 490, -4063,
        490, -512, 490, -1535, 490, -512, 490, -512, 490, -1535,
        490, -512, 490, -1535, 490, -512, 490,
    ]  # fmt: skip
    decoded = ProtonCommand.from_raw_timings(captured)
    assert decoded is not None
    assert (decoded.address, decoded.command) == (0xF4, 0x52)


@pytest.mark.parametrize(
    ("timings", "reason"),
    [
        pytest.param([], "empty", id="empty"),
        pytest.param([8000, -4000, 500], "too short", id="too_short"),
        pytest.param(
            [1000, *NEC_DISPLAY_POWER_TIMINGS[1:]], "bad leader mark", id="bad_leader"
        ),
        pytest.param(
            [*NEC_DISPLAY_POWER_TIMINGS[:19], -500, *NEC_DISPLAY_POWER_TIMINGS[20:]],
            "mid-frame gap too short",
            id="bad_mid_frame_gap",
        ),
        pytest.param(
            [*NEC_DISPLAY_POWER_TIMINGS[:36], 9000],
            "stop mark too long",
            id="bad_stop",
        ),
    ],
)
def test_proton_command_from_raw_timings_rejects(
    timings: list[int], reason: str
) -> None:
    """Timings that are not a Proton frame decode to None."""
    assert ProtonCommand.from_raw_timings(timings) is None, reason


@pytest.mark.parametrize(
    ("address", "command"),
    [
        (-1, 0x00),
        (0x100, 0x00),
        (0x00, -1),
        (0x00, 0x100),
    ],
)
def test_proton_command_rejects_out_of_range(address: int, command: int) -> None:
    """Proton addresses and commands are both 8-bit."""
    with pytest.raises(ValueError):
        ProtonCommand(address=address, command=command)
