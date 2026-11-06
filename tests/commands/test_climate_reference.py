"""Compare independent climate encoders against recorded reference waveforms."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import NamedTuple

import pytest

from infrared_protocols.commands import Command
from infrared_protocols.commands.airton import AirtonCommand
from infrared_protocols.commands.ballu import BalluCommand
from infrared_protocols.commands.climate import ClimateFan, ClimateMode
from infrared_protocols.commands.daikin_arc import DaikinArcCommand, DaikinHumidity
from infrared_protocols.commands.daikin_brc import DaikinBrcCommand
from infrared_protocols.commands.delonghi import DelonghiCommand
from infrared_protocols.commands.emmeti import EmmetiBlade, EmmetiCommand
from infrared_protocols.commands.friedrich import (
    FriedrichButton,
    FriedrichCommand,
    FriedrichUtilityCommand,
)
from infrared_protocols.commands.gree_models import GreeModel, GreeModelCommand
from infrared_protocols.commands.haier_tundra import HaierTundraCommand
from infrared_protocols.commands.hitachi import (
    HitachiAc344Command,
    HitachiAc424Command,
    HitachiButton,
)
from infrared_protocols.commands.islandaire import IslandaireCommand
from infrared_protocols.commands.mistral import MistralCommand
from infrared_protocols.commands.mitsubishi import MitsubishiCommand, MitsubishiFan
from infrared_protocols.commands.noblex import NoblexCommand
from infrared_protocols.commands.pd_pioneer_climate import PdPioneerClimateCommand
from infrared_protocols.commands.remko_ar715 import RemkoAr715Command
from infrared_protocols.commands.tcl112 import Tcl112Command
from infrared_protocols.commands.toshiba import (
    ToshibaCommand,
    ToshibaRasB10n3kv2Command,
    ToshibaSeiyaCommand,
    ToshibaSeiyaSwing,
)
from infrared_protocols.commands.toshiba_48 import (
    ToshibaRacCommand,
    ToshibaRas2819Command,
)
from infrared_protocols.commands.whirlpool import WhirlpoolCommand
from infrared_protocols.commands.whynter import WhynterCommand
from infrared_protocols.commands.zhlt01 import Zhlt01Command


@dataclass(frozen=True, kw_only=True)
class _Arguments:
    mode: ClimateMode = ClimateMode.COOL
    fan: ClimateFan = ClimateFan.AUTO
    temperature: float = 24
    power: bool = True
    swing_v: bool = False
    swing_h: bool = False
    swing: bool = False
    swing_code: int = 23
    native_fan: int = 0
    horizontal_position: int = 3
    button: int = 19
    humidity: int = 40
    humidity_changed: bool = False
    power_toggle: bool = False
    off_command: bool = False
    fahrenheit: bool = False
    model: GreeModel = GreeModel.GENERIC
    blade: int = 0


class _Factory(NamedTuple):
    build: Callable[[_Arguments], Command]
    decode: Callable[[list[int]], Command | None]


_FACTORIES: dict[str, _Factory] = {
    "BalluCommand": _Factory(
        lambda a: BalluCommand(
            mode=a.mode,
            temperature=a.temperature,
            power=a.power,
            fan=a.fan,
            swing_v=a.swing_v,
            swing_h=a.swing_h,
        ),
        BalluCommand.from_raw_timings,
    ),
    "DelonghiCommand": _Factory(
        lambda a: DelonghiCommand(
            mode=a.mode, temperature=a.temperature, power=a.power, fan=a.fan
        ),
        DelonghiCommand.from_raw_timings,
    ),
    "Tcl112Command": _Factory(
        lambda a: Tcl112Command(
            mode=a.mode,
            temperature=a.temperature,
            power=a.power,
            fan=a.fan,
            swing_v=a.swing_v,
        ),
        Tcl112Command.from_raw_timings,
    ),
    "Zhlt01Command": _Factory(
        lambda a: Zhlt01Command(
            mode=a.mode,
            temperature=a.temperature,
            power=a.power,
            fan=a.fan,
            swing_v=a.swing_v,
            swing_h=a.swing_h,
        ),
        Zhlt01Command.from_raw_timings,
    ),
    "WhynterCommand": _Factory(
        lambda a: WhynterCommand(
            mode=a.mode, temperature=int(a.temperature), power=a.power, fan=a.fan
        ),
        WhynterCommand.from_raw_timings,
    ),
    "RemkoAr715Command": _Factory(
        lambda a: RemkoAr715Command(
            mode=a.mode,
            temperature=int(a.temperature),
            power=a.power,
            fan=a.fan,
            swing_v=a.swing_v,
        ),
        RemkoAr715Command.from_raw_timings,
    ),
    "IslandaireCommand": _Factory(
        lambda a: IslandaireCommand(
            mode=a.mode, temperature_f=int(a.temperature), power=a.power, fan=a.fan
        ),
        IslandaireCommand.from_raw_timings,
    ),
    "MistralCommand": _Factory(
        lambda a: MistralCommand(
            mode=a.mode, temperature=a.temperature, power=a.power, fan=a.fan
        ),
        MistralCommand.from_raw_timings,
    ),
    "DaikinArcCommand": _Factory(
        lambda a: DaikinArcCommand(
            mode=a.mode,
            temperature=a.temperature,
            power=a.power,
            fan=a.fan,
            swing_v=a.swing_v,
            swing_h=a.swing_h,
            humidity=DaikinHumidity(a.humidity),
            humidity_changed=a.humidity_changed,
        ),
        DaikinArcCommand.from_raw_timings,
    ),
    "DaikinBrcCommand": _Factory(
        lambda a: DaikinBrcCommand(
            mode=a.mode,
            temperature=int(a.temperature),
            power=a.power,
            fan=a.fan,
            swing=a.swing,
        ),
        DaikinBrcCommand.from_raw_timings,
    ),
    "HaierTundraCommand": _Factory(
        lambda a: HaierTundraCommand(
            mode=a.mode,
            temperature=a.temperature,
            power=a.power,
            fan=a.fan,
            swing_v=a.swing_v,
            swing_h=a.swing_h,
        ),
        HaierTundraCommand.from_raw_timings,
    ),
    "AirtonCommand": _Factory(
        lambda a: AirtonCommand(
            mode=a.mode, temperature=a.temperature, power=a.power, fan=a.fan
        ),
        AirtonCommand.from_raw_timings,
    ),
    "FriedrichCommand": _Factory(
        lambda a: FriedrichCommand(
            mode=a.mode, temperature_f=int(a.temperature), fan=a.fan, swing_v=a.swing_v
        ),
        FriedrichCommand.from_raw_timings,
    ),
    "FriedrichUtilityCommand": _Factory(
        lambda a: FriedrichUtilityCommand(button=FriedrichButton(a.button)),
        FriedrichUtilityCommand.from_raw_timings,
    ),
    "MitsubishiCommand": _Factory(
        lambda a: MitsubishiCommand(
            mode=a.mode,
            temperature=a.temperature,
            power=a.power,
            fan=MitsubishiFan(a.native_fan),
            swing_v=a.swing_v,
            swing_h=a.swing_h,
        ),
        MitsubishiCommand.from_raw_timings,
    ),
    "WhirlpoolCommand": _Factory(
        lambda a: WhirlpoolCommand(
            mode=a.mode,
            temperature=int(a.temperature),
            fan=a.fan,
            power_toggle=a.power_toggle,
            off_command=a.off_command,
        ),
        WhirlpoolCommand.from_raw_timings,
    ),
    "HitachiAc344Command": _Factory(
        lambda a: HitachiAc344Command(
            mode=a.mode,
            temperature=int(a.temperature),
            power=a.power,
            fan=a.fan,
            swing_v=a.swing_v,
            horizontal_position=a.horizontal_position,
            button=HitachiButton(a.button),
        ),
        HitachiAc344Command.from_raw_timings,
    ),
    "HitachiAc424Command": _Factory(
        lambda a: HitachiAc424Command(
            mode=a.mode,
            temperature=int(a.temperature),
            power=a.power,
            fan=a.fan,
            swing_v=a.swing_v,
            horizontal_position=a.horizontal_position,
        ),
        HitachiAc424Command.from_raw_timings,
    ),
    "NoblexCommand": _Factory(
        lambda a: NoblexCommand(
            mode=a.mode,
            temperature=int(a.temperature),
            power=a.power,
            fan=a.fan,
            swing_v=a.swing_v,
        ),
        NoblexCommand.from_raw_timings,
    ),
    "EmmetiCommand": _Factory(
        lambda a: EmmetiCommand(
            mode=a.mode,
            temperature=int(a.temperature),
            power=a.power,
            fan=a.fan,
            blade=EmmetiBlade(a.blade),
        ),
        EmmetiCommand.from_raw_timings,
    ),
    "PdPioneerClimateCommand": _Factory(
        lambda a: PdPioneerClimateCommand(
            mode=a.mode,
            temperature=a.temperature,
            power=a.power,
            fan=a.fan,
            swing_v=a.swing_v,
            swing_h=a.swing_h,
        ),
        PdPioneerClimateCommand.from_raw_timings,
    ),
    "ToshibaCommand.climate": _Factory(
        lambda a: ToshibaCommand.climate(
            mode=a.mode, temperature=int(a.temperature), power=a.power, fan=a.fan
        ),
        ToshibaCommand.from_raw_timings,
    ),
    "ToshibaRasB10n3kv2Command.climate": _Factory(
        lambda a: ToshibaRasB10n3kv2Command.climate(
            mode=a.mode, temperature=int(a.temperature), power=a.power, fan=a.fan
        ),
        ToshibaRasB10n3kv2Command.from_raw_timings,
    ),
    "ToshibaSeiyaCommand.climate": _Factory(
        lambda a: ToshibaSeiyaCommand.climate(
            mode=a.mode,
            temperature=int(a.temperature),
            power=a.power,
            fan=a.fan,
            swing=ToshibaSeiyaSwing(a.swing_code),
        ),
        ToshibaSeiyaCommand.from_raw_timings,
    ),
    "ToshibaRacCommand.climate": _Factory(
        lambda a: ToshibaRacCommand.climate(
            mode=a.mode,
            temperature=int(a.temperature),
            fan=a.fan,
            fahrenheit=a.fahrenheit,
        ),
        ToshibaRacCommand.from_raw_timings,
    ),
    "ToshibaRas2819Command.climate": _Factory(
        lambda a: ToshibaRas2819Command.climate(
            mode=a.mode, temperature=int(a.temperature), fan=a.fan
        ),
        ToshibaRas2819Command.from_raw_timings,
    ),
    "ToshibaRacCommand.power_off": _Factory(
        lambda a: ToshibaRacCommand.power_off(), ToshibaRacCommand.from_raw_timings
    ),
    "ToshibaRas2819Command.power_off": _Factory(
        lambda a: ToshibaRas2819Command.power_off(),
        ToshibaRas2819Command.from_raw_timings,
    ),
}


def _gree_factory(model: GreeModel) -> _Factory:
    return _Factory(
        lambda a: GreeModelCommand(
            model=model,
            mode=a.mode,
            temperature=a.temperature,
            power=a.power,
            fan=a.fan,
            swing_v=a.swing_v,
            swing_h=a.swing_h,
        ),
        partial(GreeModelCommand.from_raw_timings, model=model),
    )


for _model in GreeModel:
    _FACTORIES[f"GreeModelCommand.{_model}"] = _gree_factory(_model)


class _Case(NamedTuple):
    command: Command
    decoder: Callable[[list[int]], Command | None]
    timings: list[int]


_CORPUS = json.loads(
    (Path(__file__).parents[1] / "fixtures/esphome_climate.json").read_text()
)
_CASES: list[_Case] = []
_IDS: list[str] = []
for _case in _CORPUS["cases"]:
    _raw_args = _case["arguments"].copy()
    _args = _Arguments(
        mode=ClimateMode(_raw_args.pop("mode", "cool")),
        fan=ClimateFan(_raw_args.pop("fan", "auto")),
        model=GreeModel(_raw_args.pop("model", "generic")),
        **_raw_args,
    )
    _tag = _case["factory"]
    _factory = _FACTORIES.get(_tag) or _FACTORIES[f"{_tag}.{_args.model}"]
    _CASES.append(
        _Case(
            _factory.build(_args),
            _factory.decode,
            [_case["palette"][int(c, 36)] for c in _case["timings"]],
        )
    )
    _IDS.append(
        _case["factory"]
        + "-"
        + "-".join(f"{key}={value}" for key, value in _case["arguments"].items())
    )


@pytest.mark.parametrize("case", _CASES, ids=_IDS)
def test_climate_reference(case: _Case) -> None:
    """Match upstream generated pulses and decode every transmitted section."""
    assert case.command.modulation == 38000
    timings = case.command.get_raw_timings()
    assert timings == case.timings
    received = case.decoder(timings)
    assert received is not None
    assert received.get_raw_timings() == timings


# Framing depends on the decoder and model, not every state permutation.
_FRAMING = {}
for _case, _id in zip(_CASES, _IDS, strict=True):
    _FRAMING.setdefault((_case.decoder, "power=False" in _id), (_case, _id))
_FRAME_CASES = [entry[0] for entry in _FRAMING.values()]
_FRAME_IDS = [entry[1] for entry in _FRAMING.values()]


@pytest.mark.parametrize("case", _FRAME_CASES, ids=_FRAME_IDS)
@pytest.mark.parametrize("length", [0, 1, 5, 17])
def test_climate_truncated(case: _Case, length: int) -> None:
    """Incomplete sections must never be interpreted as full state."""
    assert case.decoder(case.command.get_raw_timings()[:length]) is None


@pytest.mark.parametrize("case", _FRAME_CASES, ids=_FRAME_IDS)
@pytest.mark.parametrize(
    "scale,bias",
    [
        pytest.param(0.92, 0, id="shorter"),
        pytest.param(1.08, 0, id="longer"),
        pytest.param(1, 100, id="stretched-marks"),
        pytest.param(1, -100, id="shortened-marks"),
    ],
)
def test_climate_jitter(case: _Case, scale: float, bias: int) -> None:
    """Accept receiver timing variation without changing decoded state bytes."""
    received = case.decoder(
        [round(t * scale) + bias for t in case.command.get_raw_timings()]
    )
    assert received is not None
    assert received.get_raw_timings() == case.command.get_raw_timings()
