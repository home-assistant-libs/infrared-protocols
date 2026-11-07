"""Tests for mitsubishi protocol behavior."""

import pytest

from infrared_protocols.commands.mitsubishi import (
    MitsubishiCommand,
    MitsubishiFan,
    MitsubishiMode,
    MitsubishiPreset,
)


@pytest.mark.parametrize("fan", list(MitsubishiFan))
@pytest.mark.parametrize("temperature", [16, 16.5, 30.5, 31])
def test_mitsubishi_native_fields(fan: MitsubishiFan, temperature: float) -> None:
    """Intermediate speeds, both vanes and half degrees remain observable."""
    sent = MitsubishiCommand(
        mode=MitsubishiMode.COOL,
        temperature=temperature,
        fan=fan,
        preset=MitsubishiPreset.ECONO_COOL,
        vertical_position=3,
        horizontal_position=5,
        dual_vanes=True,
    )
    received = MitsubishiCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.fan == fan
    assert received.state.fan is not None
    assert received.state.temperature == temperature
    assert received.preset == MitsubishiPreset.ECONO_COOL
    assert received.vertical_position == 3
    assert received.horizontal_position == 5
    assert received.dual_vanes


@pytest.mark.parametrize(
    "preset,swing_v,dual_vanes",
    [
        pytest.param(
            preset,
            preset != MitsubishiPreset.NIGHT,
            True if preset != MitsubishiPreset.NIGHT else None,
            id=preset.value,
        )
        for preset in MitsubishiPreset
    ],
)
def test_mitsubishi_presets(
    preset: MitsubishiPreset, swing_v: bool, dual_vanes: bool | None
) -> None:
    """Preset and dual-vane bits survive decoding alongside basic state."""
    command = MitsubishiCommand(
        mode=MitsubishiMode.COOL,
        temperature=24,
        preset=preset,
        swing_v=True,
        dual_vanes=True,
    )
    result = MitsubishiCommand.from_raw_timings(command.get_raw_timings())
    assert result is not None
    assert result.data == command.data
    assert result.preset == preset
    assert result.state.swing_v == swing_v
    assert result.dual_vanes == dual_vanes


@pytest.mark.parametrize(
    "temperature,wire_celsius",
    [
        pytest.param(61, 16, id="minimum"),
        pytest.param(62, 16.5, id="half-degree"),
        pytest.param(67, 19, id="below-lookup-jump"),
        pytest.param(68, 20, id="above-lookup-jump"),
        pytest.param(88, 31, id="maximum"),
    ],
)
def test_mitsubishi_fahrenheit(temperature: int, wire_celsius: float) -> None:
    """Fahrenheit uses the remote lookup table, not arithmetic rounding."""
    command = MitsubishiCommand(
        mode=MitsubishiMode.COOL, temperature=temperature, is_fahrenheit=True
    )
    assert command.state.temperature == wire_celsius
    received = MitsubishiCommand.from_raw_timings(command.get_raw_timings())
    assert received is not None
    assert received.temperature == wire_celsius
    assert received.is_fahrenheit is False
    assert received.state.is_fahrenheit is False


def test_mitsubishi_checksum_corruption() -> None:
    """A changed payload with its old checksum must not decode."""
    command = MitsubishiCommand(mode=MitsubishiMode.COOL, temperature=24)
    command.data = command.data[:7] + bytes([command.data[7] ^ 1]) + command.data[8:]
    assert MitsubishiCommand.from_raw_timings(command.get_raw_timings()) is None


@pytest.mark.parametrize("length", [291, 292])
def test_mitsubishi_single_copy(length: int) -> None:
    """A default ten-millisecond receiver delivers one complete copy."""
    sent = MitsubishiCommand(mode=MitsubishiMode.COOL, temperature=23)
    received = MitsubishiCommand.from_raw_timings(sent.get_raw_timings()[:length])
    assert received is not None
    assert received.state.mode == MitsubishiMode.COOL
    assert received.state.temperature == 23


def test_mitsubishi_different_copies() -> None:
    """Conflicting copies cannot be combined into a single state."""
    first = MitsubishiCommand(
        mode=MitsubishiMode.COOL, temperature=23
    ).get_raw_timings()
    second = MitsubishiCommand(
        mode=MitsubishiMode.HEAT, temperature=25
    ).get_raw_timings()
    assert MitsubishiCommand.from_raw_timings(first[:292] + second[:291]) is None


@pytest.mark.parametrize("temperature", [16, 30])
def test_dry_temperature_is_not_a_setpoint(temperature: int) -> None:
    """The fixed dry-mode temperature byte does not reveal a requested set point."""
    sent = MitsubishiCommand(mode=MitsubishiMode.DRY, temperature=temperature)
    received = MitsubishiCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.data[7] == 8
    assert received.state.temperature is None
    assert received.temperature is None


@pytest.mark.parametrize("fan", list(MitsubishiFan))
def test_all_fan_levels_use_native_enum(fan: MitsubishiFan) -> None:
    """A family does not switch fan enum types when its level changes."""
    command = MitsubishiCommand(mode=MitsubishiMode.COOL, temperature=24, fan=fan)
    assert command.state.fan is fan
