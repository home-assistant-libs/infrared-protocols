"""Tests for toshiba protocol behavior."""

import pytest

from infrared_protocols.commands._timing import byte_bits
from infrared_protocols.commands.climate import ClimateMode, ClimateState
from infrared_protocols.commands.toshiba import (
    ToshibaCommand,
    ToshibaFan,
    ToshibaMotion,
    ToshibaPowerSelection,
    ToshibaPreset,
    ToshibaRas25j2kvsgNdCommand,
    ToshibaRasB10n3kv2Command,
    ToshibaSeiyaCommand,
)
from infrared_protocols.commands.toshiba_48 import (
    ToshibaRacCommand,
    ToshibaRas2819Command,
)
from infrared_protocols.commands.toshiba_ac import ToshibaAcPacketCommand


@pytest.mark.parametrize(
    "preset,temperature",
    [
        pytest.param(
            preset,
            10 if preset == ToshibaPreset.FROST_PROTECTION else 24,
            id=preset.value,
        )
        for preset in ToshibaPreset
    ],
)
def test_toshiba_presets(preset: ToshibaPreset, temperature: int) -> None:
    """Every preset selects a validated packet layout that decodes losslessly."""
    command = ToshibaRas25j2kvsgNdCommand.climate(
        mode=ClimateMode.HEAT,
        temperature=temperature,
        preset=preset,
    )
    result = ToshibaRas25j2kvsgNdCommand.from_raw_timings(command.get_raw_timings())
    assert result is not None
    assert result.data == command.data
    assert result.state == command.state
    assert result.preset == preset


@pytest.mark.parametrize("power_selection", list(ToshibaPowerSelection))
def test_toshiba_power_selection(power_selection: ToshibaPowerSelection) -> None:
    """Power limiting and compressor silent settings preserve their payloads."""
    command = ToshibaRas25j2kvsgNdCommand.climate(
        mode=ClimateMode.COOL, temperature=24, power_selection=power_selection
    )
    result = ToshibaRas25j2kvsgNdCommand.from_raw_timings(command.get_raw_timings())
    assert result is not None
    assert result.data == command.data
    assert result.power_selection == power_selection


@pytest.mark.parametrize("action", list(ToshibaMotion))
def test_toshiba_motion(action: ToshibaMotion) -> None:
    """Motion packets carry an action and no invented absolute state."""
    command = ToshibaRas25j2kvsgNdCommand.motion(action=action)
    result = ToshibaRas25j2kvsgNdCommand.from_raw_timings(command.get_raw_timings())
    assert result is not None
    assert result.state == ClimateState()
    assert result.action == action


def test_toshiba_invalid_auxiliary_field() -> None:
    """A correct XOR checksum does not make an unknown Seiya action valid."""
    data = bytearray(
        ToshibaSeiyaCommand.climate(mode=ClimateMode.COOL, temperature=24).data
    )
    data[-1] ^= data[9] ^ 0xFF
    data[9] = 0xFF
    with pytest.raises(ValueError):
        ToshibaSeiyaCommand(data=bytes(data))


@pytest.mark.parametrize("fan", list(ToshibaFan))
def test_toshiba_native_fan(fan: ToshibaFan) -> None:
    """Every decoded native fan is accepted directly by the state factory."""
    sent = ToshibaRas25j2kvsgNdCommand.climate(
        mode=ClimateMode.COOL, temperature=24, fan=fan
    )
    received = ToshibaRas25j2kvsgNdCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.fan == fan


def test_toshiba_shared_transport() -> None:
    """Model-specific and raw APIs expose the same two 48-bit payloads."""
    sent = ToshibaRas2819Command.climate(mode=ClimateMode.COOL, temperature=24)
    received = ToshibaAcPacketCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.rc_code_1 == int.from_bytes(sent.first)
    assert sent.second is not None
    assert received.rc_code_2 == int.from_bytes(sent.second)


@pytest.mark.parametrize(
    "first",
    [
        pytest.param("c23d9f6048b7", id="auto-with-low-fan"),
        pytest.param("c23d9f60649b", id="dry-with-low-fan"),
    ],
)
def test_ras2819_rejects_manual_auto_dry_fan(first: str) -> None:
    """A mode's automatic extension must agree with the first packet's fan."""
    with pytest.raises(ValueError, match="automatic fan"):
        ToshibaRas2819Command(
            first=bytes.fromhex(first), second=bytes.fromhex("d5650000003a")
        )


@pytest.mark.parametrize("cls", [ToshibaCommand, ToshibaRasB10n3kv2Command])
def test_generic_motion_is_not_climate(cls: type[ToshibaCommand]) -> None:
    """A valid checksum cannot make a motion command into a climate packet."""
    data = bytes.fromhex("f20d03fc0270010073")
    with pytest.raises(ValueError, match="climate command"):
        cls(data=data)
    raw = [*cls.HEADER, *cls.TIMING.encode(byte_bits(data, lsb=False)), cls.TIMING.mark]
    assert cls.from_raw_timings(raw) is None


@pytest.mark.parametrize(
    "enabled,report,temperature",
    [
        pytest.param(False, False, None, id="disable"),
        pytest.param(True, False, None, id="enable"),
        pytest.param(True, True, 26, id="temperature-report"),
    ],
)
def test_comfort_sense_native_fields(
    enabled: bool, report: bool, temperature: int | None
) -> None:
    """Sensor reports expose ambient temperature without inventing a set point."""
    sent = ToshibaRacCommand.comfort_sense(
        mode=ClimateMode.COOL, temperature=26, enabled=enabled, send_temperature=report
    )
    received = ToshibaRacCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.room_temperature == temperature
    assert received.comfort_sense_enabled is enabled
    assert received.comfort_sense_reports_temperature is report
    assert received.comfort_sense_mode is ClimateMode.COOL
    assert received.state.temperature is None
