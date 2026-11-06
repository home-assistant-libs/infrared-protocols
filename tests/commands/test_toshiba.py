"""Tests for toshiba protocol behavior."""

from functools import reduce
from operator import xor

import pytest

from infrared_protocols.commands._timing import byte_bits
from infrared_protocols.commands.climate import ClimateFan, ClimateMode, ClimateState
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
    Toshiba48Command,
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


@pytest.mark.parametrize(
    "cls",
    [
        pytest.param(ToshibaCommand, id="generic"),
        pytest.param(ToshibaRasB10n3kv2Command, id="ras-b10"),
        pytest.param(ToshibaSeiyaCommand, id="seiya"),
    ],
)
@pytest.mark.parametrize("fan", list(ToshibaFan))
def test_generic_native_fan_round_trip(
    cls: type[ToshibaCommand], fan: ToshibaFan
) -> None:
    """Every decoded native fan, including intermediate speeds, can be sent again."""
    sent = cls.climate(mode=ClimateMode.HEAT, temperature=20, fan=fan)
    received = cls.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.fan is fan
    assert isinstance(received.state.fan, ToshibaFan)
    assert (
        cls.climate(mode=ClimateMode.HEAT, temperature=20, fan=received.state.fan).data
        == sent.data
    )


def test_raw48_missing_compulsory_copy() -> None:
    """A partial first Toshiba raw frame cannot stand in for its full transmission."""
    raw = ToshibaAcPacketCommand(rc_code_1=1).get_raw_timings()[:99]
    assert ToshibaAcPacketCommand.from_raw_timings(raw) is None
