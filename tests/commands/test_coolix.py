"""Tests for coolix protocol behavior."""

from itertools import product

import pytest

from infrared_protocols.commands.coolix import (
    CoolixCommand,
    CoolixFanSpeed,
    CoolixMode,
    CoolixState,
)


@pytest.mark.parametrize(
    "mode,temperature,expected,fan",
    [
        pytest.param(
            mode,
            temp,
            None if mode == CoolixMode.FAN_ONLY else temp,
            fan,
            id=f"{mode.name}-{temp}-{fan.name}",
        )
        for mode, temp, fan in product(
            CoolixMode,
            [17, 24, 30],
            CoolixFanSpeed,
        )
        if not (
            mode in (CoolixMode.AUTO, CoolixMode.DRY)
            and fan == CoolixFanSpeed.AUTO
            or mode not in (CoolixMode.AUTO, CoolixMode.DRY)
            and fan == CoolixFanSpeed.AUTO_ALT
        )
    ],
)
def test_coolix_state(
    mode: CoolixMode, temperature: int, expected: int | None, fan: CoolixFanSpeed
) -> None:
    """Fan-only has no set point; other modes recover the requested state."""
    command = CoolixCommand.climate(mode=mode, temperature=temperature, fan=fan)
    result = CoolixCommand.from_raw_timings(command.get_raw_timings())
    assert result is not None
    assert result.state == CoolixState(
        power=True,
        mode=mode,
        fan=fan,
        temperature=expected,
        zone_follow=False,
    )


@pytest.mark.parametrize(
    "mode,temperature,fan,word",
    [
        pytest.param(
            CoolixMode.COOL, 24, CoolixFanSpeed.LOW, 0xB29F40, id="cool24-low"
        ),
        pytest.param(
            CoolixMode.HEAT, 30, CoolixFanSpeed.HIGH, 0xB23FBC, id="heat30-high"
        ),
        pytest.param(
            CoolixMode.COOL, 17, CoolixFanSpeed.MEDIUM, 0xB25F00, id="cool17-medium"
        ),
        pytest.param(
            CoolixMode.COOL, 24, CoolixFanSpeed.AUTO, 0xB2BF40, id="cool24-auto"
        ),
        pytest.param(
            CoolixMode.AUTO, 24, CoolixFanSpeed.AUTO_ALT, 0xB21F48, id="auto24"
        ),
        pytest.param(CoolixMode.DRY, 24, CoolixFanSpeed.AUTO_ALT, 0xB21F44, id="dry24"),
        pytest.param(
            CoolixMode.FAN_ONLY, 24, CoolixFanSpeed.AUTO, 0xB2BFE4, id="fan-only"
        ),
    ],
)
def test_coolix_control_bytes(
    mode: CoolixMode, temperature: int, fan: CoolixFanSpeed, word: int
) -> None:
    """The three-byte word is verified independently of the round trip."""
    command = CoolixCommand.climate(mode=mode, temperature=temperature, fan=fan)
    assert command.first == command.second == word


def test_coolix_unknown_state() -> None:
    """Unknown raw control fields remain raw data without raising on state access."""
    sent = CoolixCommand(first=0xB2FFF0)
    assert sent.state is None


@pytest.mark.parametrize(
    "fan",
    [fan for fan in CoolixFanSpeed if fan != CoolixFanSpeed.AUTO_ALT],
    ids=lambda fan: fan.name,
)
def test_native_fan_rebuild(fan: CoolixFanSpeed) -> None:
    """Distinct fan nibbles survive state readback and rebuilding."""
    word = 0xB21F40 | int(fan) << 13
    received = CoolixCommand(first=word, second=word)
    state = received.state
    assert state is not None
    assert state.fan is fan
    assert state.mode is not None
    assert state.temperature is not None
    rebuilt = CoolixCommand.climate(
        mode=state.mode, temperature=int(state.temperature), fan=state.fan
    )
    assert rebuilt.first == rebuilt.second == word


@pytest.mark.parametrize("mode", [CoolixMode.AUTO, CoolixMode.DRY])
def test_native_default_fan(mode: CoolixMode) -> None:
    """The default auto/dry fan is the remote's alternate automatic code."""
    sent = CoolixCommand.climate(mode=mode, temperature=24)
    assert sent.state is not None
    assert sent.state.fan is CoolixFanSpeed.AUTO_ALT


@pytest.mark.parametrize(
    "word,sensor_temperature",
    [
        pytest.param(0xBAC042, 0, id="sensor-0"),
        pytest.param(0xBACF42, 15, id="sensor-15"),
        pytest.param(0xBAD042, 16, id="sensor-16"),
        pytest.param(0xBADE42, 30, id="sensor-30"),
        pytest.param(0xBADF42, None, id="sensor-absent"),
    ],
)
def test_zone_follow_sensor(word: int, sensor_temperature: int | None) -> None:
    """The fifth sensor bit must not become part of the native fan value."""
    sent = CoolixCommand(first=word, second=word)
    received = CoolixCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    state = received.state
    assert state is not None
    assert state.fan is CoolixFanSpeed.ZONE_FOLLOW
    assert state.sensor_temperature == sensor_temperature
    assert state.zone_follow is True
    assert state.mode is CoolixMode.COOL
    assert state.temperature == 24
    rebuilt = CoolixCommand.climate(
        mode=state.mode,
        temperature=state.temperature,
        fan=state.fan,
        sensor_temperature=state.sensor_temperature,
        zone_follow=state.zone_follow,
    )
    assert rebuilt.first == rebuilt.second == word


@pytest.mark.parametrize("word", [0xB2DF42, 0xBADF40])
def test_inconsistent_zone_flags(word: int) -> None:
    """A single zone-follow flag is not a recognized climate state."""
    assert CoolixCommand(first=word).state is None


@pytest.mark.parametrize(
    "mode,fan",
    [
        pytest.param(CoolixMode.AUTO, CoolixFanSpeed.AUTO, id="auto-wrong-auto"),
        pytest.param(CoolixMode.DRY, CoolixFanSpeed.AUTO, id="dry-wrong-auto"),
        pytest.param(CoolixMode.COOL, CoolixFanSpeed.AUTO_ALT, id="cool-alternate"),
        pytest.param(CoolixMode.HEAT, CoolixFanSpeed.AUTO_ALT, id="heat-alternate"),
        pytest.param(CoolixMode.FAN_ONLY, CoolixFanSpeed.AUTO_ALT, id="fan-alternate"),
    ],
)
def test_automatic_fan_mode_mismatch(mode: CoolixMode, fan: CoolixFanSpeed) -> None:
    """Encoding rejects automatic fan codes the remote changes for this mode."""
    with pytest.raises(ValueError, match="AUTO_ALT"):
        CoolixCommand.climate(mode=mode, temperature=24, fan=fan)


def test_receive_alternate_auto_cool() -> None:
    """Received native codes remain readable even when the encoder limits them."""
    command = CoolixCommand(first=0xB21F40)
    assert command.state is not None
    assert command.state.fan is CoolixFanSpeed.AUTO_ALT
    assert command.state.mode is CoolixMode.COOL


def test_placeholder_state_rebuild() -> None:
    """Fan-only can be rebuilt from its absent setpoint."""
    sent = CoolixCommand.climate(mode=CoolixMode.FAN_ONLY)
    state = sent.state
    assert state is not None
    assert state.mode is not None
    assert state.temperature is None
    rebuilt = CoolixCommand.climate(
        mode=state.mode, temperature=state.temperature, fan=state.fan
    )
    assert rebuilt.get_raw_timings() == sent.get_raw_timings()


@pytest.mark.parametrize("temperature", [0, 99])
def test_invalid_placeholder_temperature(temperature: int) -> None:
    """An omitted target is valid, but an explicitly invalid target still fails."""
    with pytest.raises(ValueError, match="temperature"):
        CoolixCommand.climate(mode=CoolixMode.FAN_ONLY, temperature=temperature)
