"""Independent WH-TA15PE handheld captures."""

import json
from pathlib import Path

import pytest

from infrared_protocols.commands.toshiba import (
    ToshibaFan,
    ToshibaMode,
    ToshibaPowerSelection,
    ToshibaPreset,
    ToshibaRas25j2kvsgNdCommand,
)

_CAPTURED = json.loads(
    (Path(__file__).parents[1] / "fixtures/toshiba_captures.json").read_text()
)["states"]
_CASES = [
    pytest.param(
        bytes.fromhex(case["data"]),
        ToshibaRas25j2kvsgNdCommand.climate(
            mode=ToshibaMode[case["mode"].upper()],
            temperature=case["temperature"],
            fan=ToshibaFan(case["fan"]),
            preset=ToshibaPreset(case["preset"]),
            power_selection=ToshibaPowerSelection(case["power_selection"]),
        ),
        ToshibaMode[case["mode"].upper()],
        case["temperature"],
        ToshibaFan(case["fan"]),
        ToshibaPreset(case["preset"]),
        ToshibaPowerSelection(case["power_selection"]),
        id=f"{case['mode']}-{case['temperature']}-fan{case['fan']}-{case['preset']}-power{case['power_selection']}",
    )
    for case in _CAPTURED
]


@pytest.mark.parametrize("packet,command,mode,temperature,fan,preset,power", _CASES)
def test_handheld_state(
    packet: bytes,
    command: ToshibaRas25j2kvsgNdCommand,
    mode: ToshibaMode,
    temperature: int | None,
    fan: ToshibaFan,
    preset: ToshibaPreset,
    power: ToshibaPowerSelection,
) -> None:
    """Independent captured bytes verify both the encoder and native state accessors."""
    assert command.data == packet
    received = ToshibaRas25j2kvsgNdCommand.from_raw_timings(
        ToshibaRas25j2kvsgNdCommand(data=packet).get_raw_timings()
    )
    assert received is not None
    assert received.state.mode == mode
    assert received.state.temperature == temperature
    assert received.fan == fan
    assert received.preset == preset
    assert received.power_selection == power
