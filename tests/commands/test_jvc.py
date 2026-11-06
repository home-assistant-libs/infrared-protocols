"""Tests for jvc commands."""

import pytest

from infrared_protocols.commands.jvc import JvcCommand


@pytest.mark.parametrize(
    "repeats,gaps",
    [
        pytest.param(0, [], id="single"),
        pytest.param(1, [22875], id="one-repeat"),
        pytest.param(3, [22875, 35475, 35475], id="three-repeats"),
    ],
)
def test_headerless_repeats(repeats: int, gaps: list[int]) -> None:
    """JVC repeats omit the leader and retain the word on a 60-ms period."""
    first = JvcCommand(data=0xC2D0).get_raw_timings()
    repeated = JvcCommand(data=0xC2D0, repeat_count=repeats)
    expected = first + [value for gap in gaps for value in [-gap, *first[2:]]]
    assert repeated.get_raw_timings() == expected
    result = JvcCommand.from_raw_timings(expected)
    assert result is not None
    assert (result.data, result.repeat_count) == (0xC2D0, repeats)


def test_different_headerless_word_rejected() -> None:
    """A JVC repeat must carry the original word."""
    first = JvcCommand(data=0xC2D0).get_raw_timings()
    second = JvcCommand(data=0xC2D1).get_raw_timings()
    assert JvcCommand.from_raw_timings(first + [-22875] + second[2:]) is None
