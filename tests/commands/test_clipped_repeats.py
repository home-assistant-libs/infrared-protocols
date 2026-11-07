"""Check every available pulse in incomplete full-frame repeats."""

import pytest

from infrared_protocols.commands.pioneer import PioneerCommand
from infrared_protocols.commands.samsung import Samsung32Command

_COMMANDS = [
    pytest.param(PioneerCommand(address=7, command=2, repeat_count=2), id="pioneer"),
    pytest.param(
        PioneerCommand(
            address=7, command=2, preamble_address=1, preamble_command=3, repeat_count=1
        ),
        id="pioneer-two-part",
    ),
    pytest.param(Samsung32Command(address=7, command=2, repeat_count=2), id="samsung"),
]


@pytest.mark.parametrize("command", _COMMANDS)
@pytest.mark.parametrize("length", range(1, 67))
def test_matching_prefix(
    command: PioneerCommand | Samsung32Command, length: int
) -> None:
    """A cut at any pulse boundary still leaves the complete earlier command."""
    raw = command.get_raw_timings()
    received = type(command).from_raw_timings(raw[:-67] + raw[-67:][:length])
    assert received is not None
    assert received.address == command.address
    assert received.command == command.command


@pytest.mark.parametrize("command", _COMMANDS)
@pytest.mark.parametrize(
    "index,value",
    [
        pytest.param(0, 2000, id="leader-mark"),
        pytest.param(1, -2000, id="leader-space"),
        pytest.param(2, 1500, id="final-mark"),
        pytest.param(3, -560, id="conflicting-first-bit"),
    ],
)
def test_conflicting_prefix(
    command: PioneerCommand | Samsung32Command, index: int, value: int
) -> None:
    """A cadence-correct trailing burst must match both the leader and payload."""
    raw = command.get_raw_timings()
    prefix = raw[-67:][: index + 1]
    prefix[index] = value
    assert type(command).from_raw_timings(raw[:-67] + prefix) is None


@pytest.mark.parametrize(
    "length", [pytest.param(4, id="first-bit"), pytest.param(50, id="payload")]
)
def test_pioneer_alternation(length: int) -> None:
    """A clipped preamble cannot replace the button part of the next repeat."""
    command = PioneerCommand(
        address=7, command=2, preamble_address=2, preamble_command=3, repeat_count=1
    )
    raw = command.get_raw_timings()
    assert PioneerCommand.from_raw_timings(raw[:-67] + raw[:length]) is None
