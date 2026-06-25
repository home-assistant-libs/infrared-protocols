"""Tests for the GE AC IR command protocol."""

import pytest

from infrared_protocols.commands.general_electric import GEACCommand

# GE YAE1K2 POWER command: address=0xEB (11101011), command=0xD0 (11010000)
ADDRESS = 0xEB
COMMAND = 0xD0

# Expected frame for ADDRESS=0xEB, COMMAND=0xD0.
# Bits are transmitted MSB first; mid-frame gap separates address from command.
#
# 0xEB = 11101011 → 1,1,1,0,1,0,1,1
# 0xD0 = 11010000 → 1,1,0,1,0,0,0,0
POWER_FRAME: list[int] = [
    9000,
    -4500,
    # address byte (MSB first): 1,1,1,0,1,0,1,1
    562,
    -1687,
    562,
    -1687,
    562,
    -1687,
    562,
    -562,
    562,
    -1687,
    562,
    -562,
    562,
    -1687,
    562,
    -1687,
    # mid-frame stop + gap
    562,
    -4500,
    # command byte (MSB first): 1,1,0,1,0,0,0,0
    562,
    -1687,
    562,
    -1687,
    562,
    -562,
    562,
    -1687,
    562,
    -562,
    562,
    -562,
    562,
    -562,
    562,
    -562,
    # stop pulse
    562,
]


def test_ge_ac_command_get_raw_timings() -> None:
    """Test GE AC command raw timings generation."""
    command = GEACCommand(address=ADDRESS, command=COMMAND)
    timings = command.get_raw_timings()
    assert timings == POWER_FRAME
    assert len(timings) == 37
    assert command.modulation == 38000
    assert command.repeat_count == 0


def test_ge_ac_command_from_raw_timings() -> None:
    """Test decoding raw timings into a GEACCommand."""
    command = GEACCommand.from_raw_timings(POWER_FRAME)
    assert command is not None
    assert command.address == ADDRESS
    assert command.command == COMMAND
    assert command.modulation == 38000


def test_ge_ac_command_roundtrip() -> None:
    """Test that encoding then decoding returns the original values."""
    original = GEACCommand(address=ADDRESS, command=COMMAND)
    decoded = GEACCommand.from_raw_timings(original.get_raw_timings())
    assert decoded is not None
    assert decoded.address == original.address
    assert decoded.command == original.command


@pytest.mark.parametrize(
    ("address", "command"),
    [
        pytest.param(0x00, 0x00, id="all_zeros"),
        pytest.param(0xFF, 0xFF, id="all_ones"),
        pytest.param(0xEB, 0x00, id="cool_mode"),
        pytest.param(0xEB, 0x20, id="temp_up"),
        pytest.param(0xEB, 0xA0, id="temp_down"),
        pytest.param(0xEB, 0x40, id="high"),
        pytest.param(0xEB, 0x50, id="med"),
        pytest.param(0xEB, 0x90, id="low"),
        pytest.param(0xEB, 0x80, id="fan_mode"),
        pytest.param(0xEB, 0xD0, id="power"),
    ],
)
def test_ge_ac_command_roundtrip_all_codes(address: int, command: int) -> None:
    """Test roundtrip encode/decode for all YAE1K2 command codes."""
    original = GEACCommand(address=address, command=command)
    decoded = GEACCommand.from_raw_timings(original.get_raw_timings())
    assert decoded is not None
    assert decoded.address == address
    assert decoded.command == command


def test_ge_ac_command_from_raw_timings_within_tolerance() -> None:
    """Test decoding succeeds when timings deviate within the 40% tolerance."""
    skewed = [
        int(t * 1.2) if i % 2 == 0 else int(t * 0.8)
        for i, t in enumerate(POWER_FRAME)
    ]
    command = GEACCommand.from_raw_timings(skewed)
    assert command is not None
    assert command.address == ADDRESS
    assert command.command == COMMAND


@pytest.mark.parametrize(
    "timings",
    [
        pytest.param([], id="empty"),
        pytest.param([9000, -4500, 562], id="too_short"),
        pytest.param([1000, *POWER_FRAME[1:]], id="invalid_leader_high"),
        pytest.param([POWER_FRAME[0], -100, *POWER_FRAME[2:]], id="invalid_leader_low"),
        # First address bit's space set well outside both 0 and 1 ranges.
        pytest.param([*POWER_FRAME[:3], -3000, *POWER_FRAME[4:]], id="invalid_bit"),
        # Mid-frame gap (index 19) replaced with a short space — not a valid gap.
        pytest.param(
            [*POWER_FRAME[:19], -562, *POWER_FRAME[20:]], id="invalid_mid_frame_gap"
        ),
        # Stop pulse (index 36) too long to be a 562µs pulse.
        pytest.param([*POWER_FRAME[:36], 5000], id="invalid_stop_pulse"),
    ],
)
def test_ge_ac_command_from_raw_timings_invalid(timings: list[int]) -> None:
    """Test that invalid timings return None."""
    assert GEACCommand.from_raw_timings(timings) is None
