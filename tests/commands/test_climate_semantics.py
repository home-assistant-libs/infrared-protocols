"""State semantics, variant actions, and malformed climate packets."""

from itertools import product

import pytest

from infrared_protocols.codes.coolix.climate import CoolixCode
from infrared_protocols.codes.midea.climate import MideaSpecialCode
from infrared_protocols.commands.climate import ClimateFan, ClimateMode, ClimateState
from infrared_protocols.commands.coolix import CoolixCommand
from infrared_protocols.commands.gree_models import (
    GreeFeature,
    GreeModel,
    GreeModelCommand,
)
from infrared_protocols.commands.midea import MideaCommand
from infrared_protocols.commands.mitsubishi import MitsubishiCommand, MitsubishiPreset
from infrared_protocols.commands.noblex import NoblexCommand
from infrared_protocols.commands.toshiba import (
    ToshibaMotion,
    ToshibaPowerSelection,
    ToshibaPreset,
    ToshibaRas25j2kvsgNdCommand,
    ToshibaSeiyaCommand,
)
from infrared_protocols.commands.whirlpool import HisenseArgCommand, WhirlpoolCommand


@pytest.mark.parametrize(
    "mode,temperature,expected,fan",
    [
        pytest.param(
            mode,
            temp,
            None if mode == ClimateMode.FAN_ONLY else temp,
            fan,
            id=f"{mode}-{temp}-{fan}",
        )
        for mode, temp, fan in product(
            ClimateMode,
            [17, 24, 30],
            [ClimateFan.AUTO, ClimateFan.LOW, ClimateFan.MEDIUM, ClimateFan.HIGH],
        )
        if fan == ClimateFan.AUTO or mode not in (ClimateMode.AUTO, ClimateMode.DRY)
    ],
)
def test_coolix_state(
    mode: ClimateMode, temperature: int, expected: int | None, fan: ClimateFan
) -> None:
    """Fan-only has no set point; other modes recover the requested state."""
    command = CoolixCommand.climate(mode=mode, temperature=temperature, fan=fan)
    result = CoolixCommand.from_raw_timings(command.get_raw_timings())
    assert result is not None
    assert result.state == ClimateState(
        power=True,
        mode=mode,
        fan=fan,
        temperature=expected,
    )


@pytest.mark.parametrize("code", list(CoolixCode))
def test_coolix_buttons(code: CoolixCode) -> None:
    """Known button actions retain their complete command word."""
    command = code.to_command()
    result = CoolixCommand.from_raw_timings(command.get_raw_timings())
    assert result is not None
    assert result.first == code.value


@pytest.mark.parametrize("power", [False, True])
@pytest.mark.parametrize(
    "mode,fahrenheit,temperature,expected",
    [
        pytest.param(
            mode,
            fahrenheit,
            temp,
            None if mode == ClimateMode.FAN_ONLY else expected,
            id=f"{mode}-{temp}-fahrenheit{fahrenheit}",
        )
        for mode, (fahrenheit, temp, expected) in product(
            ClimateMode, [(False, 21, 21), (True, 68, 20)]
        )
    ],
)
def test_midea_state(
    mode: ClimateMode,
    power: bool,
    fahrenheit: bool,
    temperature: int,
    expected: float | None,
) -> None:
    """Native Fahrenheit codes decode to Celsius and off remains explicit."""
    command = MideaCommand.climate(
        mode=mode, temperature=temperature, power=power, fahrenheit=fahrenheit
    )
    assert command.state == ClimateState(
        power=power,
        mode=mode,
        temperature=expected,
        fan=ClimateFan.AUTO,
    )


@pytest.mark.parametrize("code", list(MideaSpecialCode))
def test_midea_buttons(code: MideaSpecialCode) -> None:
    """Button packets never masquerade as an absolute climate state."""
    command = code.to_command()
    result = MideaCommand.from_raw_timings(command.get_raw_timings())
    assert result is not None
    assert result.state is None
    assert result.data == command.data


def test_midea_follow_me() -> None:
    """The sensor report's temperature and beeper fields have fixed positions."""
    command = MideaCommand.follow_me(temperature=23, beeper=True)
    assert command.data == bytes.fromhex("a48248ff18")
    assert command.state is None


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


@pytest.mark.parametrize("power_selection", list(ToshibaPowerSelection))
def test_toshiba_power_selection(power_selection: ToshibaPowerSelection) -> None:
    """Power limiting and compressor silent settings preserve their payloads."""
    command = ToshibaRas25j2kvsgNdCommand.climate(
        mode=ClimateMode.COOL, temperature=24, power_selection=power_selection
    )
    result = ToshibaRas25j2kvsgNdCommand.from_raw_timings(command.get_raw_timings())
    assert result is not None
    assert result.data == command.data


@pytest.mark.parametrize("action", list(ToshibaMotion))
def test_toshiba_motion(action: ToshibaMotion) -> None:
    """Motion packets carry an action and no invented absolute state."""
    command = ToshibaRas25j2kvsgNdCommand.motion(action=action)
    result = ToshibaRas25j2kvsgNdCommand.from_raw_timings(command.get_raw_timings())
    assert result is not None
    assert result.state == ClimateState()
    assert result.data[5] == action


def test_toshiba_invalid_auxiliary_field() -> None:
    """A correct XOR checksum does not make an unknown Seiya action valid."""
    data = bytearray(
        ToshibaSeiyaCommand.climate(mode=ClimateMode.COOL, temperature=24).data
    )
    data[-1] ^= data[9] ^ 0xFF
    data[9] = 0xFF
    with pytest.raises(ValueError):
        ToshibaSeiyaCommand(data=bytes(data))


@pytest.mark.parametrize("preset", list(MitsubishiPreset))
def test_mitsubishi_presets(preset: MitsubishiPreset) -> None:
    """Preset and dual-vane bits survive decoding alongside basic state."""
    command = MitsubishiCommand(
        mode=ClimateMode.COOL,
        temperature=24,
        preset=preset,
        swing_v=True,
        dual_vanes=True,
    )
    result = MitsubishiCommand.from_raw_timings(command.get_raw_timings())
    assert result is not None
    assert result.data == command.data


@pytest.mark.parametrize(
    "temperature,wire_celsius", [(61, 16), (62, 16.5), (67, 19), (68, 20), (88, 31)]
)
def test_mitsubishi_fahrenheit(temperature: int, wire_celsius: float) -> None:
    """Fahrenheit uses the remote lookup table, not arithmetic rounding."""
    command = MitsubishiCommand(
        mode=ClimateMode.COOL, temperature=temperature, fahrenheit=True
    )
    assert command.state.temperature == wire_celsius


@pytest.mark.parametrize(
    "temperature,candidates,decoded",
    [
        (16, tuple(range(16, 22)), None),
        (22, (22,), 22),
        (24, (24,), 24),
        (30, (23, 25, 26, 27, 28, 29, 30), None),
    ],
)
def test_hisense_ambiguous_auto(
    temperature: int, candidates: tuple[int, ...], decoded: int | None
) -> None:
    """Auto range codes expose ambiguity instead of guessing an exact target."""
    command = HisenseArgCommand(mode=ClimateMode.AUTO, temperature=temperature)
    result = HisenseArgCommand.from_raw_timings(command.get_raw_timings())
    assert result is not None
    assert result.state.temperature == decoded
    assert result.temperature_candidates == candidates


def test_whirlpool_toggle_semantics() -> None:
    """Power and swing toggles must not be presented as absolute on states."""
    command = WhirlpoolCommand(
        mode=ClimateMode.COOL, temperature=24, power_toggle=True, swing_toggle=True
    )
    assert command.state.power is None
    assert command.state.swing_v is None
    assert command.power_toggle
    assert command.swing_toggle


def test_gree_turbo_fan() -> None:
    """YB1FA turbo selects high speed even with a lower ordinary setting."""
    command = GreeModelCommand(
        model=GreeModel.YB1FA,
        mode=ClimateMode.COOL,
        temperature=24,
        fan=ClimateFan.LOW,
        features=GreeFeature.TURBO,
    )
    assert command.state.fan == ClimateFan.HIGH


@pytest.mark.parametrize("mode", list(ClimateMode))
def test_noblex_mode_field(mode: ClimateMode) -> None:
    """Mode assignment avoids the upstream cool-template OR bug."""
    command = NoblexCommand(mode=mode, temperature=24)
    assert command.state.mode == mode


def test_mitsubishi_checksum_corruption() -> None:
    """A changed payload with its old checksum must not decode."""
    command = MitsubishiCommand(mode=ClimateMode.COOL, temperature=24)
    command.data = command.data[:7] + bytes([command.data[7] ^ 1]) + command.data[8:]
    assert MitsubishiCommand.from_raw_timings(command.get_raw_timings()) is None
