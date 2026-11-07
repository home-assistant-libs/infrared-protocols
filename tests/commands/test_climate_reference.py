"""Compare independent climate encoders against recorded reference waveforms."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, IntEnum
from functools import partial
from pathlib import Path
from typing import NamedTuple, Protocol

import pytest

from infrared_protocols.commands.airton import (
    AirtonCommand,
    AirtonDirection,
    AirtonFanSpeed,
    AirtonMode,
)
from infrared_protocols.commands.ballu import BalluCommand, BalluFanSpeed, BalluMode
from infrared_protocols.commands.daikin_arc import (
    DaikinAcFanSpeed,
    DaikinAcMode,
    DaikinArcCommand,
    DaikinHumidity,
)
from infrared_protocols.commands.daikin_brc import (
    DaikinBrcCommand,
    DaikinBrcFanSpeed,
    DaikinBrcMode,
)
from infrared_protocols.commands.delonghi import (
    DelonghiCommand,
    DelonghiFanSpeed,
    DelonghiMode,
)
from infrared_protocols.commands.emmeti import (
    EmmetiBlade,
    EmmetiCommand,
    EmmetiFanSpeed,
    EmmetiMode,
)
from infrared_protocols.commands.friedrich import (
    FriedrichButton,
    FriedrichCommand,
    FriedrichFanSpeed,
    FriedrichMode,
    FriedrichUtilityCommand,
)
from infrared_protocols.commands.gree_models import (
    GreeAcFanSpeed,
    GreeAcMode,
    GreeFeature,
    GreeModel,
    GreeModelCommand,
    GreeYx1ffFanSpeed,
)
from infrared_protocols.commands.haier_tundra import (
    HaierTundraCommand,
    HaierTundraFanSpeed,
    HaierTundraMode,
)
from infrared_protocols.commands.hitachi import (
    HitachiAc344Command,
    HitachiAc424Command,
    HitachiButton,
    HitachiFanSpeed,
    HitachiMode,
)
from infrared_protocols.commands.islandaire import (
    IslandaireCommand,
    IslandaireFanSpeed,
    IslandaireMode,
)
from infrared_protocols.commands.mistral import (
    MistralCommand,
    MistralFanSpeed,
    MistralMode,
)
from infrared_protocols.commands.mitsubishi import (
    MitsubishiCommand,
    MitsubishiFanSpeed,
    MitsubishiMode,
    MitsubishiPreset,
)
from infrared_protocols.commands.noblex import NoblexCommand, NoblexFanSpeed, NoblexMode
from infrared_protocols.commands.pd_pioneer_climate import (
    PdPioneerClimateCommand,
    PdPioneerClimateFanSpeed,
    PdPioneerClimateMode,
)
from infrared_protocols.commands.remko_ar715 import (
    RemkoAr715Command,
    RemkoAr715FanSpeed,
    RemkoAr715Mode,
)
from infrared_protocols.commands.tcl112 import Tcl112Command, Tcl112FanSpeed, Tcl112Mode
from infrared_protocols.commands.toshiba import (
    ToshibaCommand,
    ToshibaFanSpeed,
    ToshibaMode,
    ToshibaMotion,
    ToshibaPowerSelection,
    ToshibaPreset,
    ToshibaRas25j2kvsgNdCommand,
    ToshibaRasB10n3kv2Command,
    ToshibaSeiyaCommand,
    ToshibaSeiyaSwing,
)
from infrared_protocols.commands.toshiba_48 import (
    Toshiba48FanSpeed,
    Toshiba48Mode,
    ToshibaRacCommand,
    ToshibaRas2819Command,
)
from infrared_protocols.commands.whirlpool import (
    HisenseArgCommand,
    WhirlpoolCommand,
    WhirlpoolDg11j191Command,
    WhirlpoolFanSpeed,
    WhirlpoolMode,
)
from infrared_protocols.commands.whynter import (
    WhynterCommand,
    WhynterFanSpeed,
    WhynterMode,
)
from infrared_protocols.commands.zhlt01 import Zhlt01Command, Zhlt01FanSpeed, Zhlt01Mode


@dataclass(frozen=True, kw_only=True)
class _Arguments:
    mode: str = "COOL"
    fan: str = "AUTO"
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
    is_fahrenheit: bool = False
    fahrenheit_compatibility: bool = False
    model: GreeModel = GreeModel.GENERIC
    blade: int = 0
    enabled: bool = False
    send_temperature: bool = True
    preset: str = "none"
    sub_unit: int = 0
    mode_button: bool = False
    vertical_position: int = 0
    dual_vanes: bool = False
    direction: int = 0
    display: bool = True
    sleep: bool = False
    boost: bool = False
    features: int | None = None
    economy: bool = False
    power_selection: int = 0
    action: int = 0
    swing_toggle: bool = False


class _State(Protocol):
    """Native state fields compared with the external corpus."""

    @property
    def power(self) -> bool | None:
        """Return the decoded power."""
        ...

    @property
    def mode(self) -> IntEnum | None:
        """Return the decoded mode."""
        ...

    @property
    def temperature(self) -> float | None:
        """Return the decoded temperature."""
        ...

    @property
    def fan(self) -> Enum | None:
        """Return the decoded fan."""
        ...


class _ClimateCommand(Protocol):
    """The state projection shared by the reference-tested climate commands."""

    modulation: int

    @property
    def state(self) -> _State:
        """Return only state carried by the received packet."""
        ...

    def get_raw_timings(self) -> list[int]:
        """Encode the complete protocol command."""
        ...


class _Factory(NamedTuple):
    build: Callable[[_Arguments], _ClimateCommand]
    decode: Callable[[list[int]], _ClimateCommand | None]


_FACTORIES: dict[str, _Factory] = {
    "ToshibaRas25j2kvsgNdCommand.climate": _Factory(
        lambda a: ToshibaRas25j2kvsgNdCommand.climate(
            mode=ToshibaMode[a.mode],
            temperature=int(a.temperature),
            fan=ToshibaFanSpeed[a.fan],
            power=a.power,
            preset=ToshibaPreset(a.preset),
            power_selection=ToshibaPowerSelection(a.power_selection),
        ),
        ToshibaRas25j2kvsgNdCommand.from_raw_timings,
    ),
    "ToshibaRas25j2kvsgNdCommand.motion": _Factory(
        lambda a: ToshibaRas25j2kvsgNdCommand.motion(action=ToshibaMotion(a.action)),
        ToshibaRas25j2kvsgNdCommand.from_raw_timings,
    ),
    "ToshibaRacCommand.comfort_sense": _Factory(
        lambda a: ToshibaRacCommand.comfort_sense(
            mode=Toshiba48Mode[a.mode],
            temperature=int(a.temperature),
            enabled=a.enabled,
            send_temperature=a.send_temperature,
        ),
        ToshibaRacCommand.from_raw_timings,
    ),
    "ToshibaRas2819Command.swing_toggle": _Factory(
        lambda a: ToshibaRas2819Command.swing_toggle(),
        ToshibaRas2819Command.from_raw_timings,
    ),
    "ToshibaRacCommand.swing": _Factory(
        lambda a: ToshibaRacCommand.swing(enabled=a.enabled),
        ToshibaRacCommand.from_raw_timings,
    ),
    "BalluCommand": _Factory(
        lambda a: BalluCommand(
            mode=BalluMode[a.mode],
            temperature=int(a.temperature),
            power=a.power,
            fan=BalluFanSpeed[a.fan],
            swing_v=a.swing_v,
            swing_h=a.swing_h,
        ),
        BalluCommand.from_raw_timings,
    ),
    "DelonghiCommand": _Factory(
        lambda a: DelonghiCommand(
            mode=DelonghiMode[a.mode],
            temperature=int(a.temperature),
            power=a.power,
            fan=DelonghiFanSpeed[a.fan],
        ),
        DelonghiCommand.from_raw_timings,
    ),
    "Tcl112Command": _Factory(
        lambda a: Tcl112Command(
            mode=Tcl112Mode[a.mode],
            temperature=a.temperature,
            power=a.power,
            fan=Tcl112FanSpeed[a.fan],
            swing_v=a.swing_v,
        ),
        Tcl112Command.from_raw_timings,
    ),
    "Zhlt01Command": _Factory(
        lambda a: Zhlt01Command(
            mode=Zhlt01Mode[a.mode],
            temperature=int(a.temperature),
            power=a.power,
            fan=Zhlt01FanSpeed[a.fan],
            swing_v=a.swing_v,
            swing_h=a.swing_h,
            boost=a.boost,
        ),
        Zhlt01Command.from_raw_timings,
    ),
    "WhynterCommand": _Factory(
        lambda a: WhynterCommand(
            mode=WhynterMode[a.mode],
            temperature=int(a.temperature),
            power=a.power,
            fan=WhynterFanSpeed[a.fan],
            is_fahrenheit=a.is_fahrenheit,
        ),
        WhynterCommand.from_raw_timings,
    ),
    "RemkoAr715Command": _Factory(
        lambda a: RemkoAr715Command(
            mode=RemkoAr715Mode[a.mode],
            temperature=int(a.temperature),
            power=a.power,
            fan=RemkoAr715FanSpeed[a.fan],
            swing_v=a.swing_v,
        ),
        RemkoAr715Command.from_raw_timings,
    ),
    "IslandaireCommand": _Factory(
        lambda a: IslandaireCommand(
            mode=IslandaireMode[a.mode],
            temperature=int(a.temperature),
            power=a.power,
            fan=IslandaireFanSpeed[a.fan],
        ),
        IslandaireCommand.from_raw_timings,
    ),
    "MistralCommand": _Factory(
        lambda a: MistralCommand(
            mode=MistralMode[a.mode],
            temperature=int(a.temperature),
            power=a.power,
            fan=MistralFanSpeed[a.fan],
        ),
        MistralCommand.from_raw_timings,
    ),
    "DaikinArcCommand": _Factory(
        lambda a: DaikinArcCommand(
            mode=DaikinAcMode[a.mode],
            temperature=a.temperature,
            power=a.power,
            fan=DaikinAcFanSpeed[a.fan],
            swing_v=a.swing_v,
            swing_h=a.swing_h,
            humidity=DaikinHumidity(a.humidity),
            humidity_changed=a.humidity_changed,
        ),
        DaikinArcCommand.from_raw_timings,
    ),
    "DaikinBrcCommand": _Factory(
        lambda a: DaikinBrcCommand(
            is_fahrenheit=a.is_fahrenheit,
            mode=DaikinBrcMode[a.mode],
            temperature=int(a.temperature),
            power=a.power,
            fan=DaikinBrcFanSpeed[a.fan],
            swing=a.swing,
            sub_unit=a.sub_unit,
            mode_button=a.mode_button,
        ),
        DaikinBrcCommand.from_raw_timings,
    ),
    "HaierTundraCommand": _Factory(
        lambda a: HaierTundraCommand(
            mode=HaierTundraMode[a.mode],
            temperature=int(a.temperature),
            power=a.power,
            fan=HaierTundraFanSpeed[a.fan],
            swing_v=a.swing_v,
            swing_h=a.swing_h,
        ),
        HaierTundraCommand.from_raw_timings,
    ),
    "AirtonCommand": _Factory(
        lambda a: AirtonCommand(
            mode=AirtonMode[a.mode],
            temperature=int(a.temperature),
            power=a.power,
            fan=AirtonFanSpeed[a.fan],
            direction=AirtonDirection(a.direction),
            display=a.display,
            sleep=a.sleep,
        ),
        AirtonCommand.from_raw_timings,
    ),
    "FriedrichCommand": _Factory(
        lambda a: FriedrichCommand(
            mode=FriedrichMode[a.mode],
            temperature=int(a.temperature),
            fan=FriedrichFanSpeed[a.fan],
            swing_v=a.swing_v,
        ),
        FriedrichCommand.from_raw_timings,
    ),
    "FriedrichUtilityCommand": _Factory(
        lambda a: FriedrichUtilityCommand(button=FriedrichButton(a.button)),
        FriedrichUtilityCommand.from_raw_timings,
    ),
    "MitsubishiCommand": _Factory(
        lambda a: MitsubishiCommand(
            mode=MitsubishiMode[a.mode],
            temperature=a.temperature,
            power=a.power,
            fan=MitsubishiFanSpeed[a.fan],
            preset=MitsubishiPreset(a.preset),
            fahrenheit_compatibility=a.fahrenheit_compatibility,
            vertical_position=a.vertical_position,
            horizontal_position=a.horizontal_position,
            dual_vanes=a.dual_vanes,
            swing_v=a.swing_v,
            swing_h=a.swing_h,
        ),
        MitsubishiCommand.from_raw_timings,
    ),
    "WhirlpoolCommand": _Factory(
        lambda a: WhirlpoolCommand(
            mode=WhirlpoolMode[a.mode],
            temperature=int(a.temperature),
            fan=WhirlpoolFanSpeed[a.fan],
            power_toggle=a.power_toggle,
            off_command=a.off_command,
            swing_toggle=a.swing_toggle,
        ),
        WhirlpoolCommand.from_raw_timings,
    ),
    "HitachiAc344Command": _Factory(
        lambda a: HitachiAc344Command(
            mode=HitachiMode[a.mode],
            temperature=int(a.temperature),
            power=a.power,
            fan=HitachiFanSpeed[a.fan],
            swing_v=a.swing_v,
            horizontal_position=a.horizontal_position,
            button=HitachiButton(a.button),
        ),
        HitachiAc344Command.from_raw_timings,
    ),
    "HitachiAc424Command": _Factory(
        lambda a: HitachiAc424Command(
            mode=HitachiMode[a.mode],
            temperature=int(a.temperature),
            power=a.power,
            fan=HitachiFanSpeed[a.fan],
            swing_v=a.swing_v,
            horizontal_position=a.horizontal_position,
        ),
        HitachiAc424Command.from_raw_timings,
    ),
    "NoblexCommand": _Factory(
        lambda a: NoblexCommand(
            mode=NoblexMode[a.mode],
            temperature=int(a.temperature),
            power=a.power,
            fan=NoblexFanSpeed[a.fan],
            swing_v=a.swing_v,
        ),
        NoblexCommand.from_raw_timings,
    ),
    "EmmetiCommand": _Factory(
        lambda a: EmmetiCommand(
            mode=EmmetiMode[a.mode],
            temperature=int(a.temperature),
            power=a.power,
            fan=EmmetiFanSpeed[a.fan],
            blade=EmmetiBlade(a.blade),
        ),
        EmmetiCommand.from_raw_timings,
    ),
    "PdPioneerClimateCommand": _Factory(
        lambda a: PdPioneerClimateCommand(
            mode=PdPioneerClimateMode[a.mode],
            temperature=a.temperature,
            power=a.power,
            fan=PdPioneerClimateFanSpeed[a.fan],
            swing_v=a.swing_v,
            swing_h=a.swing_h,
            economy=a.economy,
        ),
        PdPioneerClimateCommand.from_raw_timings,
    ),
    "ToshibaCommand.climate": _Factory(
        lambda a: ToshibaCommand.climate(
            mode=ToshibaMode[a.mode],
            temperature=int(a.temperature),
            power=a.power,
            fan=ToshibaFanSpeed[a.fan],
        ),
        ToshibaCommand.from_raw_timings,
    ),
    "ToshibaRasB10n3kv2Command.climate": _Factory(
        lambda a: ToshibaRasB10n3kv2Command.climate(
            mode=ToshibaMode[a.mode],
            temperature=int(a.temperature),
            power=a.power,
            fan=ToshibaFanSpeed[a.fan],
        ),
        ToshibaRasB10n3kv2Command.from_raw_timings,
    ),
    "ToshibaSeiyaCommand.climate": _Factory(
        lambda a: ToshibaSeiyaCommand.climate(
            mode=ToshibaMode[a.mode],
            temperature=int(a.temperature),
            power=a.power,
            fan=ToshibaFanSpeed[a.fan],
            swing=ToshibaSeiyaSwing(a.swing_code),
        ),
        ToshibaSeiyaCommand.from_raw_timings,
    ),
    "ToshibaRacCommand.climate": _Factory(
        lambda a: ToshibaRacCommand.climate(
            mode=Toshiba48Mode[a.mode],
            temperature=int(a.temperature),
            fan=Toshiba48FanSpeed[a.fan],
            is_fahrenheit=a.is_fahrenheit,
        ),
        ToshibaRacCommand.from_raw_timings,
    ),
    "ToshibaRas2819Command.climate": _Factory(
        lambda a: ToshibaRas2819Command.climate(
            mode=Toshiba48Mode[a.mode],
            temperature=int(a.temperature),
            fan=Toshiba48FanSpeed[a.fan],
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
    fan_type = GreeYx1ffFanSpeed if model == GreeModel.YX1FF else GreeAcFanSpeed
    return _Factory(
        lambda a: GreeModelCommand(
            model=model,
            mode=GreeAcMode[a.mode],
            temperature=a.temperature,
            power=a.power,
            fan=fan_type[a.fan],
            swing_v=a.swing_v,
            swing_h=a.swing_h,
            is_fahrenheit=a.is_fahrenheit,
            sleep=a.sleep,
            features=GreeFeature(a.features) if a.features is not None else None,
        ),
        partial(GreeModelCommand.from_raw_timings, model=model),
    )


def _whirlpool_factory(cls: type[WhirlpoolCommand]) -> _Factory:
    return _Factory(
        lambda a: cls(
            mode=WhirlpoolMode[a.mode],
            temperature=int(a.temperature),
            fan=WhirlpoolFanSpeed[a.fan],
            power_toggle=a.power_toggle,
            off_command=a.off_command,
            swing_toggle=a.swing_toggle,
            swing_v=a.swing_v if cls.HISENSE else None,
        ),
        cls.from_raw_timings,
    )


for _whirlpool_class in (WhirlpoolDg11j191Command, HisenseArgCommand):
    _FACTORIES[_whirlpool_class.__name__] = _whirlpool_factory(_whirlpool_class)


for _model in GreeModel:
    _FACTORIES[f"GreeModelCommand.{_model}"] = _gree_factory(_model)


class _Case(NamedTuple):
    command: _ClimateCommand
    decoder: Callable[[list[int]], _ClimateCommand | None]
    timings: list[int]
    expected_state: dict[str, object]


_CORPUS = json.loads(
    (Path(__file__).parents[1] / "fixtures/esphome_climate.json").read_text()
)
_CASES: list[_Case] = []
_IDS: list[str] = []
for _case in _CORPUS["cases"]:
    _raw_args = _case["arguments"].copy()
    _args = _Arguments(
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
            _case["expected_state"],
        )
    )
    _IDS.append(_case["key"])


def _assert_reference_state(state: _State, expected: dict[str, object]) -> None:
    """Compare exactly the fields and native enum names exposed by this family."""
    assert {
        name: getattr(value, "name", value) for name, value in vars(state).items()
    } == expected


@pytest.mark.parametrize("case", _CASES, ids=_IDS)
def test_climate_reference(case: _Case) -> None:
    """Match upstream generated pulses and decode every transmitted section."""
    assert case.command.modulation == 38000
    timings = case.command.get_raw_timings()
    assert timings == case.timings
    received = case.decoder(timings)
    assert received is not None
    assert received.get_raw_timings() == timings
    assert type(received.state) is type(case.command.state)
    assert type(received.state.mode) is type(case.command.state.mode)
    assert type(received.state.fan) is type(case.command.state.fan)
    _assert_reference_state(received.state, case.expected_state)


# Framing depends on the decoder and model, not every state permutation.
_FRAMING = {}
for _case, _id in zip(_CASES, _IDS, strict=True):
    _FRAMING.setdefault(
        (_case.decoder, len(_case.timings), _case.expected_state["power"]), (_case, _id)
    )
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
