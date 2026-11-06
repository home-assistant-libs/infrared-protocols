"""Tests for timing protocol behavior."""

from collections.abc import Callable

import pytest

from infrared_protocols.commands import Command
from infrared_protocols.commands.climate import ClimateMode
from infrared_protocols.commands.friedrich import FriedrichCommand
from infrared_protocols.commands.kaseikyo import KaseikyoCommand
from infrared_protocols.commands.magiquest import (
    MagiQuestCommand,
)
from infrared_protocols.commands.mistral import MistralCommand
from infrared_protocols.commands.mitsubishi import MitsubishiCommand
from infrared_protocols.commands.pioneer import PioneerCommand
from infrared_protocols.commands.roomba import RoombaCommand
from infrared_protocols.commands.samsung import Samsung32Command


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(
            KaseikyoCommand(address=0x2002, data=b"\xa0\x01\xff"), id="kaseikyo"
        ),
        pytest.param(
            MitsubishiCommand(mode=ClimateMode.COOL, temperature=23), id="mitsubishi"
        ),
        pytest.param(
            FriedrichCommand(mode=ClimateMode.COOL, temperature_f=72),
            id="friedrich-aeha",
        ),
        pytest.param(
            MistralCommand(mode=ClimateMode.COOL, temperature=23), id="mistral-aeha"
        ),
        pytest.param(Samsung32Command(address=7, command=2), id="samsung"),
        pytest.param(PioneerCommand(address=7, command=2), id="pioneer"),
    ],
)
@pytest.mark.parametrize("skew", [-100, 100, 150, 200])
def test_receiver_mark_space_bias(
    command: KaseikyoCommand
    | MitsubishiCommand
    | FriedrichCommand
    | MistralCommand
    | Samsung32Command
    | PioneerCommand,
    skew: int,
) -> None:
    """A demodulator adds time to marks and removes the same time from spaces."""
    received = type(command).from_raw_timings(
        [t + skew for t in command.get_raw_timings()]
    )
    assert received is not None
    assert received.get_raw_timings() == command.get_raw_timings()


@pytest.mark.parametrize(
    "command,decoder",
    [
        pytest.param(
            RoombaCommand(data=0x88), RoombaCommand.from_raw_timings, id="roomba"
        ),
        pytest.param(
            MagiQuestCommand(wand_id=0x12345678, magnitude=0x123),
            MagiQuestCommand.from_raw_timings,
            id="magiquest",
        ),
    ],
)
def test_last_bit_space_merges_idle(
    command: Command, decoder: Callable[[list[int]], Command | None]
) -> None:
    """The final bit is determined by its mark, not the capture's idle timeout."""
    received = decoder(command.get_raw_timings()[:-1] + [-20000])
    assert received is not None
    assert received.get_raw_timings() == command.get_raw_timings()
