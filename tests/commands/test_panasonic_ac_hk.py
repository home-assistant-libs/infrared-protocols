"""Tests for the Hong Kong / Macau Panasonic A/C IR command."""

import pytest

from infrared_protocols.commands.panasonic_ac import state_to_timings
from infrared_protocols.commands.panasonic_ac_hk import (
    PanasonicAcHkCommand,
    build_full_frame,
    build_short_frame,
    checksum,
)

# Full frame: cool 24 °C, fan auto, swing auto, power on, nanoeX off.
FULL_FRAME_COOL_24: list[int] = [
    0x02,
    0x20,
    0xE0,
    0x04,
    0x00,
    0x00,
    0x00,
    0x06,
    0x02,
    0x20,
    0xE0,
    0x04,
    0x00,
    0x31,
    0x30,
    0x80,
    0xAF,
    0x0D,
    0x00,
    0x0E,
    0xE0,
    0x00,
    0x00,
    0x81,
    0x00,
    0x02,
    0x14,
]

QUIET_SHORT_FRAME: list[int] = [
    0x02,
    0x20,
    0xE0,
    0x04,
    0x00,
    0x00,
    0x00,
    0x06,
    0x02,
    0x20,
    0xE0,
    0x04,
    0x80,
    0x81,
    0x33,
    0x3A,
]

POWERFUL_SHORT_FRAME: list[int] = [
    0x02,
    0x20,
    0xE0,
    0x04,
    0x00,
    0x00,
    0x00,
    0x06,
    0x02,
    0x20,
    0xE0,
    0x04,
    0x80,
    0x86,
    0x35,
    0x41,
]


def test_checksum_frame2() -> None:
    """Test checksum over frame 2 bytes matches the trailing checksum byte."""
    state = build_full_frame(
        off=False,
        mode="cool",
        temp=24.0,
        fan="auto",
        swing="auto",
        nanoex=False,
    )
    assert checksum(state, 8, 25) == state[26]


def test_build_full_frame_cool_24() -> None:
    """Test a known full state frame payload."""
    assert (
        build_full_frame(
            off=False,
            mode="cool",
            temp=24.0,
            fan="auto",
            swing="auto",
            nanoex=False,
        )
        == FULL_FRAME_COOL_24
    )


def test_build_full_frame_off_sets_power_nibble() -> None:
    """Test the off flag clears the power bit in byte 13."""
    on = build_full_frame(
        off=False,
        mode="heat",
        temp=20.0,
        fan="low",
        swing="fixed",
        nanoex=False,
    )
    off = build_full_frame(
        off=True,
        mode="heat",
        temp=20.0,
        fan="low",
        swing="fixed",
        nanoex=False,
    )
    assert on[13] & 0x0F == 1
    assert off[13] & 0x0F == 0


def test_build_full_frame_nanoex() -> None:
    """Test nanoeX sets bit 2 in byte 25."""
    without = build_full_frame(
        off=False,
        mode="auto",
        temp=26.0,
        fan="medium",
        swing="auto",
        nanoex=False,
    )
    with_nanoex = build_full_frame(
        off=False,
        mode="auto",
        temp=26.0,
        fan="medium",
        swing="auto",
        nanoex=True,
    )
    assert without[25] == 0x02
    assert with_nanoex[25] == 0x06


def test_build_short_frame_quiet() -> None:
    """Test the Quiet short-frame payload and checksum."""
    assert build_short_frame("quiet") == QUIET_SHORT_FRAME


def test_build_short_frame_powerful() -> None:
    """Test the Powerful short-frame payload and checksum."""
    assert build_short_frame("powerful") == POWERFUL_SHORT_FRAME


def test_build_short_frame_rejects_unknown_kind() -> None:
    """Test an unknown short-frame kind raises a descriptive ValueError."""
    with pytest.raises(ValueError, match="unknown short-frame kind: 'bogus'"):
        build_short_frame("bogus")  # type: ignore[arg-type]


def test_command_full_get_raw_timings() -> None:
    """Test the full command encodes via the generic framing."""
    command = PanasonicAcHkCommand.full(
        off=False,
        mode="cool",
        temp=24.0,
        fan="auto",
        swing="auto",
        nanoex=False,
    )
    assert command.modulation == 38000
    assert command.repeat_count == 0
    assert command.get_raw_timings() == state_to_timings(FULL_FRAME_COOL_24)


def test_command_short_get_raw_timings() -> None:
    """Test the short command encodes via the generic framing."""
    command = PanasonicAcHkCommand.short(kind="quiet")
    assert command.get_raw_timings() == state_to_timings(QUIET_SHORT_FRAME)
