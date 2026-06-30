"""Tests for the Samsung AC IR command encoders."""

import pytest

from infrared_protocols.codes.samsung.ac import (
    SamsungAC0292HvacMode,
    SamsungAC0292StateBuilder,
    SamsungACFanMode,
    SamsungACSwingMode,
)
from infrared_protocols.commands.samsung import SamsungAC0292Command


def _payload(hex_values: str) -> list[int]:
    return [int(byte, 16) for byte in hex_values.split()]

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
    ],
)
def test_samsung_ac_0292_state_builder(
    hvac_mode: SamsungAC0292HvacMode,
    target_temperature: int,
    fan_mode: SamsungACFanMode,
    swing_mode: SamsungACSwingMode,
    expected_payload: list[int],
) -> None:
    """Test Samsung AC 0292 state builder payloads and timings."""
    builder = SamsungAC0292StateBuilder(
        hvac_mode=hvac_mode,
        target_temperature=target_temperature,
        fan_mode=fan_mode,
        swing_mode=swing_mode,
    )

    command = builder.to_command()

    assert isinstance(command, SamsungAC0292Command)
    assert command.payload == expected_payload
    assert command.modulation == 38000
    assert command.get_raw_timings() == _compile_0292_timings(expected_payload)


def test_samsung_ac_0292_state_builder_off() -> None:
    """Test Samsung AC 0292 off state payload and timings."""
    expected_payload = _payload(
        "02 B2 0F 00 00 00 C0 01 D2 0F 00 00 00 00 01 02 FF 71 80 11 C0"
    )

    builder = SamsungAC0292StateBuilder(
        hvac_mode="off",
        target_temperature=24,
        fan_mode="auto",
    )
    command = builder.to_command()

    assert isinstance(command, SamsungAC0292Command)
    assert command.payload == expected_payload
    assert command.get_raw_timings() == _compile_0292_timings(expected_payload)


def test_samsung_ac_0292_command_rejects_invalid_payload_length() -> None:
    """Test Samsung AC 0292 payload length validation."""
    with pytest.raises(ValueError, match="exactly 21 bytes"):
        SamsungAC0292Command(payload=[0x00])


def _compile_0292_timings(payload: list[int]) -> list[int]:
    timings: list[int] = [690, -17844]
    for offset in range(0, len(payload), 7):
        timings.extend([3086, -8864])
        for byte in payload[offset : offset + 7]:
            for bit in range(8):
                timings.extend([586, -1432 if (byte >> bit) & 1 else -436])
        timings.extend([586, -30000 if offset + 7 >= len(payload) else -2886])
    return timings
