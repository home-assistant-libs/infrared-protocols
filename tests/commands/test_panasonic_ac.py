"""Tests for the Panasonic air-conditioner IR commands."""

import pytest

from infrared_protocols.commands.panasonic_ac import (
    PanasonicAcCommand,
    PanasonicAcFanSpeed,
    PanasonicAcMode,
    PanasonicAcSwingAxis1,
    PanasonicAcSwingAxis2,
    PanasonicAcToggle,
    PanasonicAcToggleCommand,
)

# Known-good frames from the reverse-engineered protocol spec. Each frame
# includes its two leading Kaseikyo address bytes (0x02 0x20).
FULL_COOL_24_FRAMES: list[list[int]] = [
    [0x02, 0x20, 0xE0, 0x04, 0x00, 0x00, 0x00, 0x06],
    # fmt: off
    [
        0x02, 0x20, 0xE0, 0x04, 0x00, 0x31, 0x30, 0x80, 0xAF, 0x0D,
        0x00, 0x0E, 0xE0, 0x00, 0x00, 0x81, 0x00, 0x02, 0x14,
    ],
    # fmt: on
]
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
