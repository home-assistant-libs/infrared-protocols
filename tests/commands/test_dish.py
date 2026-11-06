"""Tests for dish commands."""

import pytest

from infrared_protocols.commands.dish import DishCommand


@pytest.mark.parametrize("length", [35, 36])
def test_single_complete_frame(length: int) -> None:
    """Accept a single complete Dish copy, with or without its idle gap."""
    sent = DishCommand(address=4, command=37)
    result = DishCommand.from_raw_timings(sent.get_raw_timings()[:length])
    assert result is not None
    assert (result.address, result.command) == (4, 37)


def test_conflicting_second_frame() -> None:
    """Reject a press containing two different Dish commands."""
    first = DishCommand(address=4, command=37).get_raw_timings()[:36]
    second = DishCommand(address=4, command=38).get_raw_timings()[2:36]
    assert DishCommand.from_raw_timings(first + second) is None
