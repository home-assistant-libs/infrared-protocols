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


@pytest.mark.parametrize("trim", [1, 2, 10, 32])
def test_clipped_last_repeat(trim: int) -> None:
    """A clipped final repeat preserves the word and the preceding complete repeat."""
    raw = JvcCommand(data=0xC2D0, repeat_count=2).get_raw_timings()[:-trim]
    received = JvcCommand.from_raw_timings(raw)
    assert received is not None
    assert (received.data, received.repeat_count) == (0xC2D0, 1)


def test_clipped_intermediate_repeat_rejected() -> None:
    """A broken repeat followed by another frame is not a clipped capture ending."""
    raw = JvcCommand(data=0xC2D0, repeat_count=2).get_raw_timings()
    del raw[45:60]
    assert JvcCommand.from_raw_timings(raw) is None


@pytest.mark.parametrize("gap", [-10000, -200000], ids=["too-short", "too-long"])
def test_repeat_cadence(gap: int) -> None:
    """Repeated words must belong to one held key on the 60-ms period."""
    raw = JvcCommand(data=0xC2D0, repeat_count=1).get_raw_timings()
    raw[raw.index(-22875)] = gap
    assert JvcCommand.from_raw_timings(raw) is None


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(0xC2D0, id="mixed"),
        pytest.param(0x0000, id="zeros"),
        pytest.param(0xFFFF, id="ones"),
    ],
)
@pytest.mark.parametrize("scale", [0.9, 1.0, 1.1], ids=["fast", "nominal", "slow"])
def test_fixed_repeat_gap(data: int, scale: float) -> None:
    """Fixed 45-unit spaces also identify matching headerless repeats."""
    first = JvcCommand(data=data).get_raw_timings()
    raw = first + [-23625, *first[2:]] * 3
    received = JvcCommand.from_raw_timings([round(t * scale) for t in raw])
    assert received is not None
    assert (received.data, received.repeat_count) == (data, 3)
