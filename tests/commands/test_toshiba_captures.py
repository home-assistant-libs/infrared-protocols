"""Handheld Toshiba packets and model-specific state regressions."""

import json
from functools import reduce
from operator import xor
from pathlib import Path

import pytest

from infrared_protocols.commands.climate import ClimateFan, ClimateMode, ClimateState
from infrared_protocols.commands.toshiba import (
    ToshibaFan,
    ToshibaMotion,
    ToshibaPowerSelection,
    ToshibaPreset,
    ToshibaRas25j2kvsgNdCommand,
    ToshibaSeiyaCommand,
)
from infrared_protocols.commands.toshiba_48 import (
    Toshiba48Command,
    ToshibaRacCommand,
    ToshibaRas2819Command,
)

_CAPTURED = json.loads(
    (Path(__file__).parents[1] / "fixtures/toshiba_captures.json").read_text()
)["states"]
_CASES = [
    pytest.param(
        bytes.fromhex(case["data"]),
        ToshibaRas25j2kvsgNdCommand.climate(
            mode=ClimateMode(case["mode"]),
            temperature=case["temperature"],
            fan=ToshibaFan(case["fan"]),
            preset=ToshibaPreset(case["preset"]),
            power_selection=ToshibaPowerSelection(case["power_selection"]),
        ),
        ClimateMode(case["mode"]),
        None if case["mode"] == "fan_only" else case["temperature"],
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
    mode: ClimateMode,
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


@pytest.mark.parametrize(
    "action,packet,copies",
    [
        pytest.param(ToshibaMotion.VANE_STEP, "f20d01fe210021", 1, id="vane-step-once"),
        pytest.param(
            ToshibaMotion.SWING_TOGGLE, "f20d01fe210425", 2, id="swing-toggle-twice"
        ),
    ],
)
def test_motion_transmissions(action: ToshibaMotion, packet: str, copies: int) -> None:
    """A relative vane step must not be sent twice."""
    sent = ToshibaRas25j2kvsgNdCommand.motion(action=action)
    assert sent.data == bytes.fromhex(packet)
    assert len(sent.get_raw_timings()) == copies * (2 + 7 * 16 + 2)
    received = ToshibaRas25j2kvsgNdCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state == ClimateState()
    assert received.preset is None
    assert received.power_selection is None
    assert received.action == action


def test_silent_percentage_conflict() -> None:
    """A checksum-valid silent packet cannot also limit power to 75 percent."""
    packet = bytearray.fromhex("f20d04fb097063000218")
    packet[7] = 0x40
    packet[-1] = reduce(xor, packet[:-1], 0)
    with pytest.raises(ValueError, match="silent"):
        ToshibaRas25j2kvsgNdCommand(data=bytes(packet))


def test_dry_requires_auto_fan() -> None:
    """The RAS-25 dry program has no independently adjustable fan."""
    with pytest.raises(ValueError, match="dry"):
        ToshibaRas25j2kvsgNdCommand.climate(
            mode=ClimateMode.DRY, temperature=24, fan=ClimateFan.HIGH
        )


def test_seiya_off_fan_unknown() -> None:
    """Captured off frames carry no fan selection."""
    sent = ToshibaSeiyaCommand.climate(
        mode=ClimateMode.COOL, temperature=24, power=False
    )
    received = ToshibaSeiyaCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.power is False
    assert received.state.fan is None


def test_ras2819_dry25_collision() -> None:
    """DRY 25 shares E4 with fan-only; the fan byte resolves the collision."""
    sent = ToshibaRas2819Command.climate(mode=ClimateMode.DRY, temperature=25)
    assert sent.first == bytes.fromhex("c23d1fe0e41b")
    assert sent.second == bytes.fromhex("d5650000003a")
    received = ToshibaRas2819Command.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.mode == ClimateMode.DRY
    assert received.state.temperature == 25


def test_ras2819_low_temperature_cool() -> None:
    """The special 1F fan field also occurs in low-temperature COOL packets."""
    sent = ToshibaRas2819Command(
        first=bytes.fromhex("c23d1fe040bf"), second=bytes.fromhex("d5650000003a")
    )
    received = ToshibaRas2819Command.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.mode == ClimateMode.COOL


def test_public_raw48_decoder() -> None:
    """Raw 48-bit reception does not require a model-specific state parser."""
    received = Toshiba48Command.from_raw_timings(
        ToshibaRacCommand.power_off().get_raw_timings()
    )
    assert received is not None
    assert received.state == ClimateState()


def test_rac_native_fahrenheit() -> None:
    """Native Fahrenheit input reports exact Celsius in the normalized state."""
    sent = ToshibaRacCommand.climate(
        mode=ClimateMode.COOL, temperature=75, fahrenheit=True
    )
    received = ToshibaRacCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.temperature == pytest.approx((75 - 32) * 5 / 9)
    assert received.temperature == 75
    assert received.fahrenheit is True
