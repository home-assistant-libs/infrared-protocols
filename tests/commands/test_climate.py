"""Tests for climate protocol behavior."""

import pytest

from infrared_protocols.commands._climate import ClimatePacket
from infrared_protocols.commands.airton import AirtonCommand
from infrared_protocols.commands.ballu import BalluCommand
from infrared_protocols.commands.climate import ClimateMode
from infrared_protocols.commands.daikin_arc import (
    DaikinArcCommand,
)
from infrared_protocols.commands.daikin_brc import (
    DaikinBrcCommand,
)
from infrared_protocols.commands.delonghi import DelonghiCommand
from infrared_protocols.commands.haier_tundra import (
    HaierTundraCommand,
)
from infrared_protocols.commands.hitachi import (
    HitachiAc344Command,
    HitachiAc424Command,
)
from infrared_protocols.commands.islandaire import IslandaireCommand
from infrared_protocols.commands.mistral import MistralCommand
from infrared_protocols.commands.noblex import NoblexCommand
from infrared_protocols.commands.pd_pioneer_climate import PdPioneerClimateCommand
from infrared_protocols.commands.tcl112 import Tcl112Command
from infrared_protocols.commands.whirlpool import (
    WhirlpoolCommand,
)
from infrared_protocols.commands.zhlt01 import Zhlt01Command


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(
            BalluCommand(mode=ClimateMode.HEAT, temperature=23, power=False), id="ballu"
        ),
        pytest.param(
            DaikinArcCommand(mode=ClimateMode.FAN_ONLY, temperature=18, power=False),
            id="arc",
        ),
        pytest.param(
            DaikinBrcCommand(mode=ClimateMode.COOL, temperature=23, power=False),
            id="brc",
        ),
        pytest.param(
            DelonghiCommand(mode=ClimateMode.HEAT, temperature=23, power=False),
            id="delonghi",
        ),
        pytest.param(
            HaierTundraCommand(mode=ClimateMode.HEAT, temperature=23, power=False),
            id="haier",
        ),
        pytest.param(
            IslandaireCommand(mode=ClimateMode.HEAT, temperature_f=72, power=False),
            id="islandaire",
        ),
        pytest.param(
            MistralCommand(mode=ClimateMode.HEAT, temperature=23, power=False),
            id="mistral",
        ),
        pytest.param(
            Zhlt01Command(mode=ClimateMode.HEAT, temperature=23, power=False), id="zhlt"
        ),
        pytest.param(
            WhirlpoolCommand(mode=ClimateMode.COOL, temperature=24, off_command=True),
            id="whirlpool",
        ),
    ],
)
def test_off_has_no_placeholder_mode(command: ClimatePacket) -> None:
    """Off frames must not turn zeroed mode bits into a reported operating mode."""
    received = type(command).from_raw_timings(command.get_raw_timings())
    assert received is not None
    assert received.state.mode is None


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(AirtonCommand(mode=ClimateMode.COOL, temperature=24), id="airton"),
        pytest.param(
            HitachiAc344Command(mode=ClimateMode.COOL, temperature=24), id="hitachi344"
        ),
        pytest.param(
            HitachiAc424Command(mode=ClimateMode.COOL, temperature=24), id="hitachi424"
        ),
    ],
)
def test_receiver_idle_shorter_than_sender_gap(command: ClimatePacket) -> None:
    """A receiver timeout can end the capture before the transmitter's next frame."""
    received = type(command).from_raw_timings(command.get_raw_timings()[:-1] + [-20000])
    assert received is not None
    assert received.state.mode == ClimateMode.COOL
    assert received.state.temperature == 24


@pytest.mark.parametrize("cls", [HaierTundraCommand, HitachiAc344Command])
def test_unknown_button_rejected(
    cls: type[HaierTundraCommand] | type[HitachiAc344Command],
) -> None:
    """A valid checksum cannot legitimize an unsupported action identifier."""
    with pytest.raises(ValueError):
        cls(mode=ClimateMode.COOL, temperature=24, button=255)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "sent,data",
    [
        pytest.param(
            HaierTundraCommand(mode=ClimateMode.COOL, temperature=24),
            bytes.fromhex("a682000040a0002000000000143c"),
            id="haier",
        ),
        pytest.param(
            HitachiAc344Command(mode=ClimateMode.COOL, temperature=24),
            bytes.fromhex(
                "01100040bfff00cc33926d22dd609f00ff00ff00ff00ff00ff53acf10e01fe01fe807f03fc00ff00ff00ff"
            ),
            id="hitachi",
        ),
    ],
)
def test_unknown_received_button(
    sent: HaierTundraCommand | HitachiAc344Command, data: bytes
) -> None:
    """Reject unknown button values before exposing an accessor that would fail."""
    sent.data = data
    assert type(sent).from_raw_timings(sent.get_raw_timings()) is None


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(
            NoblexCommand(mode=ClimateMode.HEAT, temperature=24, power=False),
            id="noblex",
        ),
        pytest.param(
            PdPioneerClimateCommand(mode=ClimateMode.COOL, temperature=24, power=False),
            id="pd-pioneer",
        ),
        pytest.param(
            Tcl112Command(mode=ClimateMode.HEAT, temperature=24, power=False),
            id="tcl112",
        ),
    ],
)
def test_off_mode(
    command: NoblexCommand | PdPioneerClimateCommand | Tcl112Command,
) -> None:
    """Fixed off templates do not identify the retained operating mode."""
    received = type(command).from_raw_timings(command.get_raw_timings())
    assert received is not None
    assert received.state.power is False
    assert received.state.mode is None
