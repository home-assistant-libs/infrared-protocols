"""Tests for the Panasonic air-conditioner IR commands."""

import pytest

from infrared_protocols.commands.panasonic_ac import (
    PanasonicAcCommand,
    PanasonicAcFanSpeed,
    PanasonicAcMode,
    PanasonicAcModel,
    PanasonicAcSwingAxis1,
    PanasonicAcSwingAxis2,
    PanasonicAcToggle,
    PanasonicAcToggleCommand,
)

# Known-good frames from the reverse-engineered protocol spec. Each frame
# includes its two leading Kaseikyo address bytes (0x02 0x20).
FULL_COOL_24_FRAMES: list[list[int]] = [
    [0x02, 0x20, 0xE0, 0x04, 0x00, 0x00, 0x00, 0x06],
    [
        0x02, 0x20, 0xE0, 0x04, 0x00, 0x31, 0x30, 0x80, 0xAF, 0x0D,
        0x00, 0x0E, 0xE0, 0x00, 0x00, 0x81, 0x00, 0x02, 0x14,
    ],
]  # fmt: skip
QUIET_FRAMES: list[list[int]] = [
    [0x02, 0x20, 0xE0, 0x04, 0x00, 0x00, 0x00, 0x06],
    [0x02, 0x20, 0xE0, 0x04, 0x80, 0x81, 0x33, 0x3A],
]


def _decode_frames(timings: list[int]) -> list[list[int]]:
    """Decode raw Kaseikyo timings back into per-frame byte lists.

    Splits on the inter-frame gap, drops each frame's leader and trailing end
    pulse, then packs the LSB-first bits into bytes. A bit is a 1 when its space
    is clearly longer than the bit mark, so decoding is independent of the exact
    base-unit timings. The decoded bytes include each frame's address bytes.
    """
    frames: list[list[int]] = [[]]
    for value in timings:
        if value == -10000:
            frames.append([])
        else:
            frames[-1].append(value)

    decoded: list[list[int]] = []
    for frame in frames:
        body = frame[2:-1]
        mark = body[0]
        bits = [1 if -body[i + 1] > 2 * mark else 0 for i in range(0, len(body), 2)]
        decoded.append(
            [sum(bits[i + k] << k for k in range(8)) for i in range(0, len(bits), 8)]
        )
    return decoded


def test_full_command_frames() -> None:
    """Test the full state command encodes to the expected frame bytes."""
    command = PanasonicAcCommand(mode=PanasonicAcMode.COOL, temperature=24.0)
    assert _decode_frames(command.get_raw_timings()) == FULL_COOL_24_FRAMES
    assert command.modulation == 38000
    assert command.repeat_count == 0


def test_toggle_command_frames() -> None:
    """Test the Quiet toggle command encodes to the expected frame bytes."""
    command = PanasonicAcToggleCommand(toggle=PanasonicAcToggle.QUIET)
    assert _decode_frames(command.get_raw_timings()) == QUIET_FRAMES


def test_power_off_clears_power_bit() -> None:
    """Test power=False clears bit 0 of byte 13."""
    on = PanasonicAcCommand(mode=PanasonicAcMode.HEAT, temperature=20.0)
    off = PanasonicAcCommand(mode=PanasonicAcMode.HEAT, temperature=20.0, power=False)
    assert _decode_frames(on.get_raw_timings())[1][5] & 0x0F == 1
    assert _decode_frames(off.get_raw_timings())[1][5] & 0x0F == 0


def test_nanoex_sets_feature_bit() -> None:
    """Test nanoeX flips bit 0x04 of byte 25."""
    without = PanasonicAcCommand(mode=PanasonicAcMode.AUTO, temperature=26.0)
    with_nanoex = PanasonicAcCommand(
        mode=PanasonicAcMode.AUTO, temperature=26.0, nanoex=True
    )
    assert _decode_frames(without.get_raw_timings())[1][17] == 0x02
    assert _decode_frames(with_nanoex.get_raw_timings())[1][17] == 0x06


def test_swing_axes_land_in_expected_nibbles() -> None:
    """Test the two swing axes encode into bytes 16 and 17."""
    command = PanasonicAcCommand(
        mode=PanasonicAcMode.COOL,
        temperature=24.0,
        fan=PanasonicAcFanSpeed.HIGH,
        swing_axis1=PanasonicAcSwingAxis1.LOWEST,
        swing_axis2=PanasonicAcSwingAxis2.FULL_LEFT,
    )
    frame2 = _decode_frames(command.get_raw_timings())[1]
    assert frame2[8] == (PanasonicAcFanSpeed.HIGH << 4) | PanasonicAcSwingAxis1.LOWEST
    assert frame2[9] == PanasonicAcSwingAxis2.FULL_LEFT


@pytest.mark.parametrize("temperature", [15.0, 30.5, 31.0])
def test_temperature_out_of_range_raises(temperature: float) -> None:
    """Test an out-of-range temperature raises ValueError."""
    with pytest.raises(ValueError, match="out of range"):
        PanasonicAcCommand(mode=PanasonicAcMode.COOL, temperature=temperature)


# CS-NE9PKE remote recordings, including checksums, from ESPHome PR #21631:
# tests/components/panasonic_ir/test_panasonic_ir.cpp,
# commit 5f5a81434df4d47c3b9fb8d3927f11791a5bcbf6.
@pytest.mark.parametrize(
    ("temperature", "fan", "payload"),
    [
        (16, PanasonicAcFanSpeed.HIGH, "0220e004004920807f00000ee00000810000dd"),
        (30, PanasonicAcFanSpeed.HIGH, "0220e00400493c807f00000ee00000810000f9"),
        (19, PanasonicAcFanSpeed.AUTO, "0220e00400492680af00000ee0000081000013"),
        (20, PanasonicAcFanSpeed.AUTO, "0220e00400492880af00000ee0000081000015"),
    ],
)
def test_pke_recorded_heat_frames(
    temperature: int, fan: PanasonicAcFanSpeed, payload: str
) -> None:
    """Match complete payloads recorded from the physical remote."""
    command = PanasonicAcCommand(
        model=PanasonicAcModel.PKE,
        mode=PanasonicAcMode.HEAT,
        temperature=temperature,
        fan=fan,
    )
    assert _decode_frames(command.get_raw_timings()) == [
        FULL_COOL_24_FRAMES[0],
        list(bytes.fromhex(payload)),
    ]
    assert command.modulation == 36700
    assert command.repeat_count == 0


def test_pke_recorded_fixed_vane_frame() -> None:
    """Match the remote's cooling frame with a fixed middle vane."""
    command = PanasonicAcCommand(
        model=PanasonicAcModel.PKE,
        mode=PanasonicAcMode.COOL,
        temperature=24,
        swing_axis1=PanasonicAcSwingAxis1.MIDDLE,
    )
    assert _decode_frames(command.get_raw_timings())[1] == list(
        bytes.fromhex("0220e00400393080a300000ee0000081000001")
    )


def test_pke_recorded_frost_protection_frame() -> None:
    """Frost protection overrides remembered temperature, fan and vane settings."""
    command = PanasonicAcCommand(
        model=PanasonicAcModel.PKE,
        mode=PanasonicAcMode.HEAT,
        temperature=24,
        fan=PanasonicAcFanSpeed.LOW,
        swing_axis1=PanasonicAcSwingAxis1.LOWEST,
        frost_protection=True,
    )
    assert _decode_frames(command.get_raw_timings())[1] == list(
        bytes.fromhex("0220e004004914807f00000ee00000810000d1")
    )


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (PanasonicAcModel.DKE, "0220e00400412880af06000ee0000001000699"),
        (PanasonicAcModel.JKE, "0220e00400412880af00000ee000008100000d"),
        (PanasonicAcModel.LKE, "0220e00400432880af06000ee0000081000015"),
        (PanasonicAcModel.NKE, "0220e00400412880af06000ee0000081000013"),
        (PanasonicAcModel.RKR, "0220e00400492880af06000ee0000089000023"),
        (PanasonicAcModel.PKE, "0220e00400492880af00000ee0000081000015"),
    ],
)
def test_model_frames(model: PanasonicAcModel, payload: str) -> None:
    """Match the ESPHome encoder's model layouts for heat at 20 degrees."""
    command = PanasonicAcCommand(model=model, mode=PanasonicAcMode.HEAT, temperature=20)
    assert _decode_frames(command.get_raw_timings())[1] == list(bytes.fromhex(payload))


@pytest.mark.parametrize(
    "toggle, power_byte, checksum", [(False, 0x40, 0x9C), (True, 0x41, 0x9D)]
)
def test_ckp_power_toggle(toggle: bool, power_byte: int, checksum: int) -> None:
    """CKP must explicitly request a toggle or leave power unchanged."""
    command = PanasonicAcCommand(
        model=PanasonicAcModel.CKP,
        mode=PanasonicAcMode.HEAT,
        temperature=20,
        power_toggle=toggle,
    )
    assert _decode_frames(command.get_raw_timings())[1] == [
        0x02, 0x20, 0xE0, 0x04, 0x00, power_byte, 0x28, 0x80, 0xAF, 0x00,
        0x00, 0x0E, 0xE0, 0x10, 0x00, 0x01, 0x00, 0x00, checksum,
    ]  # fmt: skip


@pytest.mark.parametrize("temperature", [16, 20, 30])
def test_fan_only_fixed_temperature(temperature: int) -> None:
    """Fan-only sends the protocol's fixed temperature, not the set point."""
    command = PanasonicAcCommand(
        model=PanasonicAcModel.PKE,
        mode=PanasonicAcMode.FAN_ONLY,
        temperature=temperature,
    )
    assert _decode_frames(command.get_raw_timings())[1] == list(
        bytes.fromhex("0220e00400693680af00000ee0000081000043")
    )


@pytest.mark.parametrize("model", [PanasonicAcModel.DKE, PanasonicAcModel.RKR])
def test_named_model_horizontal_vane(model: PanasonicAcModel) -> None:
    """Models with a horizontal vane accept explicit positions."""
    command = PanasonicAcCommand(
        model=model,
        mode=PanasonicAcMode.COOL,
        temperature=24,
        swing_axis2=PanasonicAcSwingAxis2.LEFT,
    )
    frame = _decode_frames(command.get_raw_timings())[1]
    assert frame[9] == 0x0A
    assert frame[-1] == sum(frame[:-1]) % 256


@pytest.mark.parametrize("modulation", [36700, 38000, 40000])
def test_named_model_timings(modulation: int) -> None:
    """Carrier overrides do not change the recorded pulse durations."""
    command = PanasonicAcCommand(
        model=PanasonicAcModel.PKE,
        mode=PanasonicAcMode.COOL,
        temperature=24,
        modulation=modulation,
    )
    timings = command.get_raw_timings()
    assert command.modulation == modulation
    assert len(timings) == 439
    assert timings[:6] == [3456, -1728, 432, -432, 432, -1296]
    assert timings[130:134] == [432, -10000, 3456, -1728]
    assert timings[-1] == 432


@pytest.mark.parametrize("power", [False, True])
def test_named_model_power(power: bool) -> None:
    """Switching off preserves the PKE model flag, including in frost mode."""
    command = PanasonicAcCommand(
        model=PanasonicAcModel.PKE,
        mode=PanasonicAcMode.HEAT,
        temperature=20,
        power=power,
        frost_protection=True,
    )
    frame = _decode_frames(command.get_raw_timings())[1]
    assert frame[5] == 0x48 | power
    assert frame[-1] == sum(frame[:-1]) % 256


def test_original_half_degree_encoding() -> None:
    """Existing callers retain half-degree temperature encoding and timing."""
    command = PanasonicAcCommand(mode=PanasonicAcMode.COOL, temperature=24.5)
    assert _decode_frames(command.get_raw_timings())[1][6] == 49
    assert command.get_raw_timings()[:2] == [3368, -1684]


@pytest.mark.parametrize("model", list(PanasonicAcModel))
def test_named_model_rejects_half_degree(model: PanasonicAcModel) -> None:
    """Named models cannot transmit fractional set points."""
    with pytest.raises(ValueError, match="whole degree"):
        PanasonicAcCommand(model=model, mode=PanasonicAcMode.HEAT, temperature=20.5)


@pytest.mark.parametrize("power", [None, True, False])
def test_ckp_requires_explicit_toggle(power: bool | None) -> None:
    """A declarative power state cannot safely drive a CKP power toggle."""
    with pytest.raises(ValueError, match="CKP requires power_toggle"):
        PanasonicAcCommand(
            model=PanasonicAcModel.CKP,
            mode=PanasonicAcMode.HEAT,
            temperature=20,
            power=power,
        )


def test_ckp_rejects_conflicting_power_arguments() -> None:
    """The caller must choose toggle semantics for CKP."""
    with pytest.raises(ValueError, match="CKP requires power_toggle"):
        PanasonicAcCommand(
            model=PanasonicAcModel.CKP,
            mode=PanasonicAcMode.HEAT,
            temperature=20,
            power=True,
            power_toggle=True,
        )


def test_other_models_reject_power_toggle() -> None:
    """Other variants have declarative power."""
    with pytest.raises(ValueError, match="only supported for CKP"):
        PanasonicAcCommand(
            model=PanasonicAcModel.PKE,
            mode=PanasonicAcMode.HEAT,
            temperature=20,
            power_toggle=True,
        )


@pytest.mark.parametrize(
    "model",
    [
        PanasonicAcModel.JKE,
        PanasonicAcModel.LKE,
        PanasonicAcModel.NKE,
        PanasonicAcModel.PKE,
    ],
)
def test_unsupported_horizontal_vane(model: PanasonicAcModel) -> None:
    """Do not send unsupported axis commands or silently ignore them."""
    with pytest.raises(ValueError, match="swing_axis2 is not supported"):
        PanasonicAcCommand(
            model=model,
            mode=PanasonicAcMode.COOL,
            temperature=24,
            swing_axis2=PanasonicAcSwingAxis2.AUTO,
        )


def test_named_model_rejects_nanoex() -> None:
    """The original nanoeX bit is not valid for the new model layouts."""
    with pytest.raises(ValueError, match="nanoex is not supported"):
        PanasonicAcCommand(
            model=PanasonicAcModel.PKE,
            mode=PanasonicAcMode.COOL,
            temperature=24,
            nanoex=True,
        )


@pytest.mark.parametrize(
    ("model", "mode"),
    [(None, PanasonicAcMode.HEAT), (PanasonicAcModel.PKE, PanasonicAcMode.COOL)],
)
def test_invalid_frost_protection(
    model: PanasonicAcModel | None, mode: PanasonicAcMode
) -> None:
    """Frost protection needs a compatible frame layout and heating mode."""
    with pytest.raises(ValueError, match="frost_protection requires"):
        PanasonicAcCommand(
            model=model, mode=mode, temperature=24, frost_protection=True
        )
