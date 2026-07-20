"""Tests for the Samsung AC IR command encoders."""

import pytest

from infrared_protocols.commands.samsung import (
    SamsungAC0292Command,
    SamsungAC0292HvacMode,
    SamsungACFanMode,
    SamsungACSwingMode,
    _apply_checksum,
)


def _payload(hex_values: str) -> list[int]:
    return [int(byte, 16) for byte in hex_values.split()]


def _compile_0292_timings(payload: list[int]) -> list[int]:
    timings: list[int] = [690, -17844]
    for offset in range(0, len(payload), 7):
        timings.extend([3086, -8864])
        for byte in payload[offset : offset + 7]:
            for bit in range(8):
                timings.extend([586, -1432 if (byte >> bit) & 1 else -436])
        timings.extend([586, -30000 if offset + 7 >= len(payload) else -2886])
    return timings


@pytest.mark.parametrize(
    (
        "hvac_mode",
        "target_temperature",
        "fan_mode",
        "swing_mode",
        "expected_payload",
    ),
    [
        pytest.param(
            "cool",
            16,
            "auto",
            "off",
            _payload("02 92 0F 00 00 00 F0 01 D2 0F 00 00 00 00 01 F2 FE 71 00 11 F0"),
            id="cool-16-auto-off",
        ),
        pytest.param(
            "cool",
            23,
            "auto",
            "off",
            _payload("02 92 0F 00 00 00 F0 01 D2 0F 00 00 00 00 01 C2 FE 71 70 11 F0"),
            id="cool-23-auto-off",
        ),
        pytest.param(
            "cool",
            24,
            "auto",
            "off",
            _payload("02 92 0F 00 00 00 F0 01 D2 0F 00 00 00 00 01 E2 FE 71 80 11 F0"),
            id="cool-24-auto-off",
        ),
        pytest.param(
            "cool",
            25,
            "auto",
            "off",
            _payload("02 92 0F 00 00 00 F0 01 D2 0F 00 00 00 00 01 D2 FE 71 90 11 F0"),
            id="cool-25-auto-off",
        ),
        pytest.param(
            "cool",
            26,
            "auto",
            "off",
            _payload("02 92 0F 00 00 00 F0 01 D2 0F 00 00 00 00 01 D2 FE 71 A0 11 F0"),
            id="cool-26-auto-off",
        ),
        pytest.param(
            "cool",
            27,
            "auto",
            "off",
            _payload("02 92 0F 00 00 00 F0 01 D2 0F 00 00 00 00 01 C2 FE 71 B0 11 F0"),
            id="cool-27-auto-off",
        ),
        pytest.param(
            "cool",
            30,
            "auto",
            "off",
            _payload("02 92 0F 00 00 00 F0 01 D2 0F 00 00 00 00 01 C2 FE 71 E0 11 F0"),
            id="cool-30-auto-off",
        ),
        pytest.param(
            "cool",
            24,
            "low",
            "off",
            _payload("02 92 0F 00 00 00 F0 01 D2 0F 00 00 00 00 01 D2 FE 71 80 15 F0"),
            id="cool-24-low-off",
        ),
        pytest.param(
            "cool",
            24,
            "medium",
            "off",
            _payload("02 92 0F 00 00 00 F0 01 D2 0F 00 00 00 00 01 D2 FE 71 80 19 F0"),
            id="cool-24-medium-off",
        ),
        pytest.param(
            "cool",
            24,
            "high",
            "off",
            _payload("02 92 0F 00 00 00 F0 01 D2 0F 00 00 00 00 01 C2 FE 71 80 1B F0"),
            id="cool-24-high-off",
        ),
        pytest.param(
            "heat",
            24,
            "auto",
            "off",
            _payload("02 92 0F 00 00 00 F0 01 D2 0F 00 00 00 00 01 E2 FE 71 80 41 F0"),
            id="heat-24-auto-off",
        ),
        pytest.param(
            "dry",
            24,
            "auto",
            "off",
            _payload("02 92 0F 00 00 00 F0 01 D2 0F 00 00 00 00 01 E2 FE 71 80 21 F0"),
            id="dry-24-auto-off",
        ),
        pytest.param(
            "fan_only",
            24,
            "auto",
            "off",
            _payload("02 92 0F 00 00 00 F0 01 D2 0F 00 00 00 00 01 D2 FE 71 80 31 F0"),
            id="fan-only-24-auto-off",
        ),
        pytest.param(
            "cool",
            25,
            "medium",
            "vertical",
            _payload("02 92 0F 00 00 00 F0 01 D2 0F 00 00 00 00 01 E2 AE 71 90 19 F0"),
            id="cool-25-medium-vertical",
        ),
        pytest.param(
            "auto",
            24,
            "auto",
            "off",
            _payload("02 92 0F 00 00 00 F0 01 D2 0F 00 00 00 00 01 D2 FE 71 80 0D F0"),
            id="auto-24-auto-off",
        ),
    ],
)
def test_samsung_ac_0292_command(
    hvac_mode: SamsungAC0292HvacMode,
    target_temperature: int,
    fan_mode: SamsungACFanMode,
    swing_mode: SamsungACSwingMode,
    expected_payload: list[int],
) -> None:
    """Test Samsung AC 0292 command raw timings."""
    command = SamsungAC0292Command(
        hvac_mode=hvac_mode,
        target_temperature=target_temperature,
        fan_mode=fan_mode,
        swing_mode=swing_mode,
    )

    assert command.modulation == 38000
    assert command.get_raw_timings() == _compile_0292_timings(expected_payload)


def test_samsung_ac_0292_command_off() -> None:
    """Test Samsung AC 0292 off command raw timings."""
    expected_payload = _payload(
        "02 B2 0F 00 00 00 C0 01 D2 0F 00 00 00 00 01 02 FF 71 80 11 C0"
    )

    command = SamsungAC0292Command(hvac_mode="off")

    assert command.get_raw_timings() == _compile_0292_timings(expected_payload)


def test_samsung_ac_0292_command_off_ignores_temperature_and_fan() -> None:
    """Test that off mode drops target_temperature and fan_mode after construction."""
    command = SamsungAC0292Command(
        hvac_mode="off", target_temperature=24, fan_mode="high"
    )

    assert command.target_temperature is None
    assert command.fan_mode is None


def test_samsung_ac_0292_command_auto_drops_fan_mode() -> None:
    """Test that auto mode drops the requested fan_mode (frame encodes a fixed fan)."""
    command = SamsungAC0292Command(
        hvac_mode="auto", target_temperature=24, fan_mode="high"
    )

    assert command.fan_mode is None


def test_samsung_ac_0292_command_requires_temperature() -> None:
    """Test that a non-off mode without target_temperature raises."""
    with pytest.raises(ValueError, match="target_temperature is required"):
        SamsungAC0292Command(hvac_mode="cool")


@pytest.mark.parametrize("target_temperature", [15, 31])
def test_samsung_ac_0292_command_rejects_temperature_out_of_range(
    target_temperature: int,
) -> None:
    """Test that target_temperature outside 16..30 raises."""
    with pytest.raises(ValueError, match="out of range"):
        SamsungAC0292Command(hvac_mode="cool", target_temperature=target_temperature)


def test_samsung_ac_0292_from_raw_timings_off() -> None:
    """Test decoding the off command's raw timings."""
    command = SamsungAC0292Command(hvac_mode="off")

    decoded = SamsungAC0292Command.from_raw_timings(command.get_raw_timings())

    assert decoded is not None
    assert decoded.hvac_mode == "off"
    assert decoded.target_temperature is None
    assert decoded.fan_mode is None


@pytest.mark.parametrize(
    ("hvac_mode", "target_temperature", "fan_mode", "swing_mode"),
    [
        ("cool", 16, "auto", "off"),
        ("cool", 23, "auto", "off"),
        ("cool", 24, "auto", "off"),
        ("cool", 25, "auto", "off"),
        ("cool", 26, "auto", "off"),
        ("cool", 27, "auto", "off"),
        ("cool", 30, "auto", "off"),
        ("cool", 24, "low", "off"),
        ("cool", 24, "medium", "off"),
        ("cool", 24, "high", "off"),
        ("heat", 24, "auto", "off"),
        ("dry", 24, "auto", "off"),
        ("fan_only", 24, "auto", "off"),
        ("cool", 25, "medium", "vertical"),
        ("auto", 24, "auto", "off"),
    ],
)
def test_samsung_ac_0292_roundtrip(
    hvac_mode: SamsungAC0292HvacMode,
    target_temperature: int,
    fan_mode: SamsungACFanMode,
    swing_mode: SamsungACSwingMode,
) -> None:
    """Test that encoding then decoding a command reproduces the original state."""
    command = SamsungAC0292Command(
        hvac_mode=hvac_mode,
        target_temperature=target_temperature,
        fan_mode=fan_mode,
        swing_mode=swing_mode,
    )

    decoded = SamsungAC0292Command.from_raw_timings(command.get_raw_timings())

    assert decoded is not None
    assert decoded.hvac_mode == command.hvac_mode
    assert decoded.target_temperature == command.target_temperature
    assert decoded.fan_mode == command.fan_mode
    assert decoded.swing_mode == command.swing_mode


def test_samsung_ac_0292_from_raw_timings_rejects_wrong_length() -> None:
    """Test that timings of the wrong length are rejected."""
    command = SamsungAC0292Command(hvac_mode="cool", target_temperature=24)
    timings = command.get_raw_timings()[:-1]

    assert SamsungAC0292Command.from_raw_timings(timings) is None


def test_samsung_ac_0292_from_raw_timings_rejects_bad_header() -> None:
    """Test that a malformed header mark/space is rejected."""
    command = SamsungAC0292Command(hvac_mode="cool", target_temperature=24)
    timings = command.get_raw_timings()
    timings[0] = 100  # nowhere near _HDR_MARK

    assert SamsungAC0292Command.from_raw_timings(timings) is None


def test_samsung_ac_0292_from_raw_timings_rejects_bad_bit_timing() -> None:
    """Test that a mark/space pair matching neither bit value is rejected."""
    command = SamsungAC0292Command(hvac_mode="cool", target_temperature=24)
    timings = command.get_raw_timings()
    # First data bit's space, forced to a value that decodes to neither 0 nor 1.
    timings[3] = -1000

    assert SamsungAC0292Command.from_raw_timings(timings) is None


def test_samsung_ac_0292_from_raw_timings_rejects_invalid_checksum() -> None:
    """Test that a payload with a corrupted checksum nibble is rejected."""
    command = SamsungAC0292Command(hvac_mode="cool", target_temperature=24)
    payload = command._build_payload()
    payload[1] ^= 0xF0  # flip the checksum nibble embedded in section1[1]

    timings = _compile_0292_timings(payload)

    assert SamsungAC0292Command.from_raw_timings(timings) is None


def test_samsung_ac_0292_from_raw_timings_rejects_altered_fixed_field() -> None:
    """Test that a payload with valid checksums but an altered fixed field is rejected.

    Checksum validity alone doesn't confirm this is a frame the encoder would
    produce, since the checksum only covers bit-count consistency, not the fixed
    section headers and reserved bytes.
    """
    command = SamsungAC0292Command(hvac_mode="cool", target_temperature=24)
    payload = command._build_payload()

    # Corrupt a reserved/fixed byte (section3[3], always 0x71) and recompute its
    # section's checksum so the checksum check alone would otherwise pass.
    section3 = list(payload[14:21])
    section3[3] = 0x70
    payload[14:21] = _apply_checksum(section3)

    timings = _compile_0292_timings(payload)

    assert SamsungAC0292Command.from_raw_timings(timings) is None


def test_samsung_ac_0292_from_raw_timings_rejects_auto_with_wrong_fan_nibble() -> None:
    """Test that an auto-mode frame with a non-6 fan nibble is rejected.

    The encoder always forces fan code 6 for auto mode; a frame claiming auto with
    a different fan nibble isn't one this library would produce, even though it
    would otherwise decode to a plausible fan_mode via _FAN_MODE_BY_VALUE.
    """
    command = SamsungAC0292Command(hvac_mode="auto", target_temperature=24)
    payload = command._build_payload()

    section3 = list(payload[14:21])
    section3[5] = 0x01 | (2 << 1) | (0 << 4)
    payload[14:21] = _apply_checksum(section3)

    timings = _compile_0292_timings(payload)

    assert SamsungAC0292Command.from_raw_timings(timings) is None
