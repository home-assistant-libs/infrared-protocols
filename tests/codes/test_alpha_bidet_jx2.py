"""Tests for the Alpha Bidet JX-2 command codes."""

import pytest

from infrared_protocols.codes.alpha_bidet.jx2 import (
    ALPHA_BIDET_ADDRESS,
    MAX_LEVEL,
    AlphaBidetJX2Code,
    AlphaBidetJX2Setting,
)
from infrared_protocols.commands import Command
from infrared_protocols.commands.kaseikyo import KaseikyoCommand

# Payloads learned from the physical remote, checksum included.
CAPTURED_CODES = {
    AlphaBidetJX2Code.STOP: "10 d0 04 95 20",
    AlphaBidetJX2Code.STOP_HOLD: "10 d0 44 26 1e",
    AlphaBidetJX2Code.REAR: "10 d0 05 92 1e",
    AlphaBidetJX2Code.FRONT: "10 d0 06 92 1f",
    AlphaBidetJX2Code.DRY: "10 d0 07 21 18",
    AlphaBidetJX2Code.WASH_AND_DRY: "10 d0 36 12 1a",
    AlphaBidetJX2Code.EASY_WASH: "10 d0 77 92 27",
    AlphaBidetJX2Code.WATER_DRY_UP: "10 d0 11 22 14",
    AlphaBidetJX2Code.WATER_DRY_DOWN: "10 d0 01 21 12",
    AlphaBidetJX2Code.NOZZLE_UP: "00 d0 18 16",
    AlphaBidetJX2Code.NOZZLE_DOWN: "00 d0 08 15",
}
CAPTURED_SETTINGS = {
    (AlphaBidetJX2Setting.SEAT_TEMP, 0): "10 d0 09 20 19",
    (AlphaBidetJX2Setting.SEAT_TEMP, 1): "10 d0 09 21 1a",
    (AlphaBidetJX2Setting.SEAT_TEMP, 2): "10 d0 09 22 1b",
    (AlphaBidetJX2Setting.SEAT_TEMP, 3): "10 d0 09 23 1c",
    (AlphaBidetJX2Setting.WATER_TEMP, 0): "10 d0 19 20 1a",
    (AlphaBidetJX2Setting.WATER_TEMP, 1): "10 d0 19 21 1b",
    (AlphaBidetJX2Setting.WATER_TEMP, 2): "10 d0 19 22 1c",
    (AlphaBidetJX2Setting.WATER_TEMP, 3): "10 d0 19 23 1d",
}


def captured_frames(command: Command) -> list[str]:
    """Return each frame as the remote sends it after the address, checksum included."""
    assert isinstance(command, KaseikyoCommand)
    assert isinstance(command.data, list)
    assert command.error_correction is not None
    address = ALPHA_BIDET_ADDRESS.to_bytes(2, "little")
    frames: list[str] = []
    for frame in command.data:
        # The checksum covers the frame as transmitted, with the address in front.
        checksum = command.error_correction(address + frame)
        frames.append((frame + checksum).hex(" "))
    return frames


def test_alpha_bidet_jx2_codes_are_unique() -> None:
    """Every code must be distinct, since duplicates become silent aliases."""
    members = AlphaBidetJX2Code.__members__
    assert len(members) == len(set(members.values()))


def test_alpha_bidet_jx2_code_get_raw_timings_stop() -> None:
    """Test the encoded waveform for a stop press against the captured remote.

    37 kHz is pinned because the carrier also sets the Kaseikyo base unit, so the 38 kHz
    default would shift every mark and space away from the captured timings.
    """
    expected_raw_timings = [
        3459, -1730, 432, -432, 432, -432, 432, -432, 432, -432, 432, -432, 432, -432,
        432, -1297, 432, -432, 432, -432, 432, -432, 432, -432, 432, -432, 432, -432,
        432, -432, 432, -432, 432, -432, 432, -432, 432, -432, 432, -1297, 432, -432,
        432, -1297, 432, -432, 432, -432, 432, -432, 432, -432, 432, -432, 432, -432,
        432, -432, 432, -1297, 432, -432, 432, -1297, 432, -1297, 432, -432, 432, -432,
        432, -1297, 432, -432, 432, -432, 432, -432, 432, -432, 432, -432, 432, -1297,
        432, -432, 432, -1297, 432, -432, 432, -1297, 432, -432, 432, -432, 432, -1297,
        432, -432, 432, -432, 432, -432, 432, -432, 432, -432, 432, -1297, 432, -432,
        432, -432, 432,
        # The encoder's fixed inter-frame gap; the captured remote leaves ~54 ms here.
        -10000,
        3459, -1730, 432, -432, 432, -432, 432, -432, 432, -432, 432, -432, 432, -432,
        432, -1297, 432, -432, 432, -432, 432, -432, 432, -432, 432, -432, 432, -432,
        432, -432, 432, -432, 432, -432, 432, -432, 432, -432, 432, -1297, 432, -432,
        432, -1297, 432, -432, 432, -432, 432, -432, 432, -432, 432, -432, 432, -432,
        432, -432, 432, -1297, 432, -432, 432, -1297, 432, -1297, 432, -432, 432, -432,
        432, -1297, 432, -432, 432, -432, 432, -432, 432, -432, 432, -432, 432, -1297,
        432, -432, 432, -1297, 432, -432, 432, -1297, 432, -432, 432, -432, 432, -1297,
        432, -432, 432, -432, 432, -432, 432, -432, 432, -432, 432, -1297, 432, -432,
        432, -432, 432,
    ]  # fmt: skip
    command = AlphaBidetJX2Code.STOP.to_command()
    assert command.get_raw_timings() == expected_raw_timings
    assert command.modulation == 37000


@pytest.mark.parametrize(
    ("code", "captured"),
    [
        pytest.param(code, captured, id=code.name.lower())
        for code, captured in CAPTURED_CODES.items()
    ],
)
def test_code_sends_the_captured_payload_twice(
    code: AlphaBidetJX2Code, captured: str
) -> None:
    """Each press is two identical frames matching the remote's capture."""
    assert captured_frames(code.to_command()) == [captured, captured]


def test_every_code_and_level_is_covered_by_a_capture() -> None:
    """A code or level added without a capture would ship an unverified payload."""
    assert set(CAPTURED_CODES) == set(AlphaBidetJX2Code)
    assert set(CAPTURED_SETTINGS) == {
        (setting, level)
        for setting in AlphaBidetJX2Setting
        for level in range(MAX_LEVEL + 1)
    }


@pytest.mark.parametrize(
    ("setting", "level", "captured"),
    [
        pytest.param(setting, level, captured, id=f"{setting.name.lower()}_{level}")
        for (setting, level), captured in CAPTURED_SETTINGS.items()
    ],
)
def test_setting_sends_the_captured_level_payload(
    setting: AlphaBidetJX2Setting, level: int, captured: str
) -> None:
    """Levels are absolute: the value byte says which one, not which direction."""
    assert captured_frames(setting.to_command(level)) == [captured, captured]


@pytest.mark.parametrize("level", [-1, 4, 16], ids=["negative", "above_max", "nibble"])
def test_setting_rejects_a_level_outside_the_range(level: int) -> None:
    """A level wider than the low nibble would corrupt the value byte silently."""
    with pytest.raises(ValueError, match="level"):
        AlphaBidetJX2Setting.WATER_TEMP.to_command(level)
