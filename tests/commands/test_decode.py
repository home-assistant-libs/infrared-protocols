"""Tests for decode protocol behavior."""

from collections.abc import Callable

import pytest

from infrared_protocols.commands import Command
from infrared_protocols.commands.marantz_extended import MarantzExtendedCommand
from infrared_protocols.commands.pioneer import PioneerCommand
from infrared_protocols.commands.rc5 import RC5Command
from infrared_protocols.commands.rc6 import RC6Command
from infrared_protocols.commands.samsung import Samsung32Command

Decoder = Callable[[list[int]], Command | None]


@pytest.mark.parametrize("factory", [Samsung32Command, PioneerCommand])
def test_intermediate_clipped_frame(
    factory: type[Samsung32Command] | type[PioneerCommand],
) -> None:
    """A damaged intermediate frame must not hide a later complete command."""
    raw = factory(address=7, command=2, repeat_count=2).get_raw_timings()
    raw[68:135] = raw[68:79]
    assert factory.from_raw_timings(raw) is None


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(RC5Command(address=0, command=0), id="rc5-zero"),
        pytest.param(RC5Command(address=31, command=127, toggle=1), id="rc5-ones"),
        pytest.param(RC6Command(address=0, command=0), id="rc6-zero"),
        pytest.param(RC6Command(address=0, command=0, toggle=1), id="rc6-wide-toggle"),
        pytest.param(
            MarantzExtendedCommand(address=0, command=63, extension=63), id="rc5x"
        ),
    ],
)
@pytest.mark.parametrize("bias", [-150, -100, -50, 50, 100, 150])
@pytest.mark.parametrize("scale", [0.92, 1, 1.08])
def test_manchester_clock_and_bias(
    command: RC5Command | RC6Command | MarantzExtendedCommand, bias: int, scale: float
) -> None:
    """Opposite edge bias must not masquerade as a different Manchester clock."""
    received = type(command).from_raw_timings(
        [round(t * scale) + bias for t in command.get_raw_timings()]
    )
    assert received is not None
    assert received.get_raw_timings() == command.get_raw_timings()


@pytest.mark.parametrize(
    "factory,decode",
    [
        (
            lambda: RC5Command(address=1, command=2, repeat_count=1),
            RC5Command.from_raw_timings,
        ),
        (
            lambda: RC6Command(address=1, command=2, repeat_count=1),
            RC6Command.from_raw_timings,
        ),
        (
            lambda: Samsung32Command(address=1, command=2, repeat_count=1),
            Samsung32Command.from_raw_timings,
        ),
    ],
    ids=["rc5", "rc6", "samsung32"],
)
def test_invalid_repeat_period(factory: Callable[[], Command], decode: Decoder) -> None:
    """An unrelated frame after a long pause is not a held-key repeat."""
    raw = factory().get_raw_timings()
    index = raw.index(min(raw))
    raw[index] *= 3
    assert decode(raw) is None
