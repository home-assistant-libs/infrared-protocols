"""Tests for gree models protocol behavior."""

import pytest

from infrared_protocols.commands.climate import ClimateFan, ClimateMode
from infrared_protocols.commands.gree_models import (
    GreeFeature,
    GreeModel,
    GreeModelCommand,
)


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


def test_gree_horizontal_only_yac() -> None:
    """YAC horizontal motion is independent of the primary vertical enable bit."""
    sent = GreeModelCommand(
        model=GreeModel.YAC, mode=ClimateMode.COOL, temperature=24, swing_h=True
    )
    received = GreeModelCommand.from_raw_timings(
        sent.get_raw_timings(), model=GreeModel.YAC
    )
    assert received is not None
    assert received.state.swing_h is True
    assert received.state.swing_v is False


def test_gree_yaw_followup() -> None:
    """The fixed second YAW1F packet has no independent climate state."""
    sent = GreeModelCommand(
        model=GreeModel.YAW1F, mode=ClimateMode.COOL, temperature=24
    )
    raw = sent.get_raw_timings()
    assert (
        GreeModelCommand.from_raw_timings(
            raw[raw.index(-40000) + 1 :], model=GreeModel.YAW1F
        )
        is None
    )


@pytest.mark.parametrize("model", [GreeModel.YAA, GreeModel.YAC1FB9, GreeModel.GENERIC])
def test_gree_no_swing_fields(model: GreeModel) -> None:
    """No enable bit and no vane position means no vertical motion."""
    sent = GreeModelCommand(
        model=GreeModel.YAA, mode=ClimateMode.COOL, temperature=24, swing_v=True
    )
    data = bytearray(sent.data)
    data[0] &= ~0x40
    # The swing-enable bit is not included in this checksum.
    sent.data = bytes(data)
    received = GreeModelCommand.from_raw_timings(sent.get_raw_timings(), model=model)
    assert received is not None
    assert received.state.swing_v is False


def test_gree_yan_model_semantics() -> None:
    """YAN's vane nibble carries motion even without the other models' enable bit."""
    sent = GreeModelCommand(
        model=GreeModel.YAN,
        mode=ClimateMode.COOL,
        temperature=24,
        swing_v=True,
        modulation=36000,
    )
    received = GreeModelCommand.from_raw_timings(
        sent.get_raw_timings(), model=GreeModel.YAN
    )
    assert received is not None
    assert received.state.swing_v is True
    assert sent.modulation == 36000


def test_gree_yac_rejects_followup() -> None:
    """The YAC follow-up packet is not an ordinary YAC state."""
    sent = GreeModelCommand(model=GreeModel.YAC, mode=ClimateMode.COOL, temperature=24)
    sent.data = bytes.fromhex("09082070002020f0")
    assert (
        GreeModelCommand.from_raw_timings(sent.get_raw_timings(), model=GreeModel.YAC)
        is None
    )


def test_gree_yx_vertical_only() -> None:
    """YX1FF has one vane axis; a horizontal-only request cannot be encoded."""
    with pytest.raises(ValueError, match="horizontal"):
        GreeModelCommand(
            model=GreeModel.YX1FF, mode=ClimateMode.COOL, temperature=24, swing_h=True
        )
    sent = GreeModelCommand(
        model=GreeModel.YX1FF, mode=ClimateMode.COOL, temperature=24, swing_v=True
    )
    assert sent.state.swing_v is True
    assert sent.state.swing_h is None


@pytest.mark.parametrize("model", list(GreeModel))
@pytest.mark.parametrize("temperature", [60, 72, 86])
def test_gree_native_fahrenheit(model: GreeModel, temperature: int) -> None:
    """Fahrenheit input and received native units match the display's truncation."""
    command = GreeModelCommand(
        model=model, mode=ClimateMode.COOL, temperature=temperature, fahrenheit=True
    )
    received = GreeModelCommand.from_raw_timings(command.get_raw_timings(), model=model)
    assert received is not None
    assert received.fahrenheit
    assert received.temperature == temperature
    assert received.state.temperature == (temperature - 32) * 5 / 9


@pytest.mark.parametrize(
    "model",
    [
        GreeModel.YAC,
        GreeModel.YAG,
        GreeModel.YAW1F,
        GreeModel.GENERIC,
        GreeModel.YAA,
        GreeModel.YAC1FB9,
    ],
)
def test_gree_vane_without_enable_bit(model: GreeModel) -> None:
    """These model layouts retain an absolute vane indication with bit 6 clear."""
    command = GreeModelCommand(model=model, mode=ClimateMode.COOL, temperature=24)
    command.data = bytes.fromhex("09082050012020f0")
    received = GreeModelCommand.from_raw_timings(command.get_raw_timings(), model=model)
    assert received is not None
    assert received.state.swing_v is True


@pytest.mark.parametrize(
    "model,packet",
    [
        pytest.param(GreeModel.YX1FF, "19087050002000d0", id="turbo-with-low-fan"),
        pytest.param(GreeModel.YX1FF, "49086a5011200080", id="timer-ones"),
        pytest.param(GreeModel.YX1FF, "49686050112000e0", id="timer-tens"),
        pytest.param(GreeModel.YX1FF, "49086051112000f0", id="byte-three"),
        pytest.param(GreeModel.YX1FF, "49086050122000e0", id="vane-while-swinging"),
        pytest.param(GreeModel.YX1FF, "49086050012000d0", id="missing-horizontal-vane"),
        pytest.param(GreeModel.YX1FF, "49086050110000c0", id="byte-five"),
        pytest.param(GreeModel.YX1FF, "4908605011202000", id="byte-six"),
        pytest.param(GreeModel.YX1FF, "49086050112000e1", id="checksum-low-nibble"),
        pytest.param(GreeModel.YX1FF, "4958645011200020", id="timer-over-24h"),
        pytest.param(GreeModel.YB1FA, "09082050002000d0", id="missing-model-a-power"),
    ],
)
def test_gree_model_a_validation(model: GreeModel, packet: str) -> None:
    """Correct checksums do not make incompatible model-A fields valid."""
    command = GreeModelCommand(model=model, mode=ClimateMode.COOL, temperature=24)
    command.data = bytes.fromhex(packet)
    assert (
        GreeModelCommand.from_raw_timings(command.get_raw_timings(), model=model)
        is None
    )


@pytest.mark.parametrize("model", [GreeModel.YB1FA, GreeModel.YX1FF])
def test_gree_power_is_not_health(model: GreeModel) -> None:
    """The model-A power flag is excluded from independent feature bits."""
    command = GreeModelCommand(
        model=model, mode=ClimateMode.COOL, temperature=24, features=GreeFeature.NONE
    )
    assert command.data[2] & 64
    assert command.features == GreeFeature.NONE


@pytest.mark.parametrize("model", [GreeModel.YX1FF, GreeModel.YAC1FB9])
def test_gree_sleep_light_features(model: GreeModel) -> None:
    """Supported sleep and light flags survive receiving a state."""
    sent = GreeModelCommand(
        model=model, mode=ClimateMode.COOL, temperature=24, sleep=True
    )
    received = GreeModelCommand.from_raw_timings(sent.get_raw_timings(), model=model)
    assert received is not None
    assert received.sleep is True
    assert received.features == GreeFeature.LIGHT


def test_gree_health_xfan() -> None:
    """Legacy independent features are readable without interpreting raw bytes."""
    sent = GreeModelCommand(
        model=GreeModel.YAN,
        mode=ClimateMode.COOL,
        temperature=24,
        features=GreeFeature.HEALTH | GreeFeature.XFAN,
    )
    assert sent.features == GreeFeature.HEALTH | GreeFeature.XFAN
    assert sent.data[2] == 0xC0


def test_gree_yx_rejects_horizontal_swing() -> None:
    """The duplicated vane nibble is a vertical-only control."""
    with pytest.raises(ValueError, match="horizontal swing"):
        GreeModelCommand(
            model=GreeModel.YX1FF,
            mode=ClimateMode.COOL,
            temperature=24,
            swing_v=True,
            swing_h=True,
        )


def test_gree_unsupported_features() -> None:
    """Model-specific power bits cannot be requested as health features."""
    with pytest.raises(ValueError, match="unsupported Gree feature"):
        GreeModelCommand(
            model=GreeModel.YB1FA,
            mode=ClimateMode.COOL,
            temperature=24,
            features=GreeFeature.HEALTH,
        )


def test_yb_turbo_overrides_received_fan() -> None:
    """YB1FA's turbo flag overrides a lower ordinary fan field."""
    command = GreeModelCommand(
        model=GreeModel.YB1FA, mode=ClimateMode.COOL, temperature=24
    )
    command.data = bytes.fromhex("19087050002000d0")
    received = GreeModelCommand.from_raw_timings(
        command.get_raw_timings(), model=GreeModel.YB1FA
    )
    assert received is not None
    assert received.state.fan is ClimateFan.HIGH
