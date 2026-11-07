"""Cross-family tests for decoded climate settings."""

import pytest

from infrared_protocols.commands._climate import ClimatePacket
from infrared_protocols.commands.airton import AirtonCommand, AirtonMode
from infrared_protocols.commands.ballu import BalluCommand, BalluMode
from infrared_protocols.commands.daikin_arc import (
    DaikinAcMode,
    DaikinArcCommand,
)
from infrared_protocols.commands.daikin_brc import (
    DaikinBrcCommand,
    DaikinBrcMode,
)
from infrared_protocols.commands.delonghi import DelonghiCommand, DelonghiMode
from infrared_protocols.commands.haier_tundra import (
    HaierTundraCommand,
    HaierTundraMode,
)
from infrared_protocols.commands.hitachi import (
    HitachiAc344Command,
    HitachiAc424Command,
    HitachiMode,
)
from infrared_protocols.commands.islandaire import IslandaireCommand, IslandaireMode
from infrared_protocols.commands.mistral import MistralCommand, MistralMode
from infrared_protocols.commands.noblex import NoblexCommand, NoblexMode
from infrared_protocols.commands.pd_pioneer_climate import (
    PdPioneerClimateCommand,
    PdPioneerClimateMode,
)
from infrared_protocols.commands.tcl112 import Tcl112Command, Tcl112Mode
from infrared_protocols.commands.whirlpool import (
    WhirlpoolCommand,
    WhirlpoolMode,
)
from infrared_protocols.commands.zhlt01 import Zhlt01Command, Zhlt01Mode


@pytest.mark.parametrize(
    "command,expected_power",
    [
        pytest.param(
            BalluCommand(mode=BalluMode.HEAT, temperature=23, power=False),
            False,
            id="ballu",
        ),
        pytest.param(
            DaikinArcCommand(mode=DaikinAcMode.FAN_ONLY, temperature=18, power=False),
            False,
            id="arc",
        ),
        pytest.param(
            DaikinBrcCommand(mode=DaikinBrcMode.COOL, temperature=23, power=False),
            False,
            id="brc",
        ),
        pytest.param(
            DelonghiCommand(mode=DelonghiMode.HEAT, temperature=23, power=False),
            False,
            id="delonghi",
        ),
        pytest.param(
            HaierTundraCommand(mode=HaierTundraMode.HEAT, temperature=23, power=False),
            False,
            id="haier",
        ),
        pytest.param(
            IslandaireCommand(mode=IslandaireMode.HEAT, temperature=72, power=False),
            False,
            id="islandaire",
        ),
        pytest.param(
            MistralCommand(mode=MistralMode.HEAT, temperature=23, power=False),
            False,
            id="mistral",
        ),
        pytest.param(
            Zhlt01Command(mode=Zhlt01Mode.HEAT, temperature=23, power=False),
            False,
            id="zhlt",
        ),
        pytest.param(
            WhirlpoolCommand(mode=WhirlpoolMode.COOL, temperature=24, off_command=True),
            None,
            id="whirlpool",
        ),
        pytest.param(
            NoblexCommand(mode=NoblexMode.HEAT, temperature=24, power=False),
            False,
            id="noblex",
        ),
        pytest.param(
            PdPioneerClimateCommand(
                mode=PdPioneerClimateMode.COOL, temperature=24, power=False
            ),
            False,
            id="pd-pioneer",
        ),
        pytest.param(
            Tcl112Command(mode=Tcl112Mode.HEAT, temperature=24, power=False),
            False,
            id="tcl112",
        ),
    ],
)
def test_off_has_no_placeholder_mode(
    command: ClimatePacket | NoblexCommand, expected_power: bool | None
) -> None:
    """Off frames must not turn zeroed mode bits into a reported operating mode."""
    received = type(command).from_raw_timings(command.get_raw_timings())
    assert received is not None
    assert received.state.mode is None
    assert received.state.power is expected_power


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(AirtonCommand(mode=AirtonMode.COOL, temperature=24), id="airton"),
        pytest.param(
            HitachiAc344Command(mode=HitachiMode.COOL, temperature=24), id="hitachi344"
        ),
        pytest.param(
            HitachiAc424Command(mode=HitachiMode.COOL, temperature=24), id="hitachi424"
        ),
    ],
)
def test_receiver_idle_shorter_than_sender_gap(command: ClimatePacket) -> None:
    """A receiver timeout can end the capture before the transmitter's next frame."""
    received = type(command).from_raw_timings(command.get_raw_timings()[:-1] + [-20000])
    assert received is not None
    assert received.state.mode is not None
    assert received.state.mode.name == "COOL"
    assert received.state.temperature == 24
