"""Tests for the Gree YAP1F I-Feel temperature report.

The report burst and the ``0bc60070`` state frame come from two captures of a
real YAP1F remote on 2026-11-28 (fixture keeps the original timestamps).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from broadlink_captures import _broadlink_timings, _split_bursts

from infrared_protocols.commands.gree_ac import (
    GreeAcCommand,
    GreeAcIFeelReport,
    GreeAcModel,
)

_FIXTURE = (
    Path(__file__).parent / "fixtures" / "yap1f_ifeel_report_captures_2026-11-28.jsonl"
)


def _rows() -> list[dict]:
    with open(_FIXTURE, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _bits(value: int) -> list[int]:
    return [(value >> i) & 1 for i in range(8)]


def test_golden_timings_for_27() -> None:
    """27 = 0x1B sent LSB-first, then 0xA5 LSB-first, then a bit mark."""
    expected = [5854, -2900]
    for bit in _bits(0x1B) + _bits(0xA5):
        expected += [673, -1580 if bit else -516]
    expected.append(673)
    command = GreeAcIFeelReport(temperature=27)
    assert command.get_raw_timings() == expected
    assert len(expected) == 35
    assert command.modulation == 38029


@pytest.mark.parametrize("temperature", [0, 27, 50])
def test_round_trip(temperature: int) -> None:
    """Encoding then decoding returns the same temperature."""
    timings = GreeAcIFeelReport(temperature=temperature).get_raw_timings()
    decoded = GreeAcIFeelReport.from_raw_timings(timings)
    assert decoded is not None
    assert decoded.temperature == temperature


@pytest.mark.parametrize("temperature", [-1, 51])
def test_invalid_temperature(temperature: int) -> None:
    """Out-of-range temperatures are rejected."""
    with pytest.raises(ValueError):
        GreeAcIFeelReport(temperature=temperature)


def test_non_yap1f_model_rejected() -> None:
    """Only YAP1F supports the report."""
    with pytest.raises(ValueError):
        GreeAcIFeelReport(temperature=27, model=GreeAcModel.GENERIC)


def test_decoder_rejects_malformed_bursts() -> None:
    """The decoder is strict about shape, leader, tag and range."""
    good = GreeAcIFeelReport(temperature=27).get_raw_timings()
    assert GreeAcIFeelReport.from_raw_timings(good[:-1]) is None
    assert GreeAcIFeelReport.from_raw_timings([*good, -20000]) is None
    wrong_leader = [8796, -4365, *good[2:]]
    assert GreeAcIFeelReport.from_raw_timings(wrong_leader) is None
    bad_tag = GreeAcIFeelReport(temperature=27).get_raw_timings()
    bad_tag[2 + 2 * 8 + 1] = -516  # byte1 bit0: 1 -> 0, tag 0xA4
    assert GreeAcIFeelReport.from_raw_timings(bad_tag) is None
    flipped = GreeAcIFeelReport(temperature=27).get_raw_timings()
    flipped[3] = -flipped[3]
    assert GreeAcIFeelReport.from_raw_timings(flipped) is None
    # 0xFF in byte 0 is a well-formed frame but not a plausible temperature.
    assert GreeAcIFeelReport.from_raw_timings(_raw_with_temp(0xFF)) is None
    assert GreeAcIFeelReport.from_raw_timings(_raw_with_temp(51)) is None
    assert GreeAcIFeelReport.from_raw_timings(_raw_with_temp(50)) is not None


@pytest.mark.parametrize(
    ("shift", "expected"),
    [pytest.param(300, 27, id="within-tolerance"), pytest.param(400, None, id="out")],
)
def test_uniform_mark_offset_is_consistent(shift: int, expected: int | None) -> None:
    """Data and trailing marks share one tolerance around the YAP1F mark."""
    timings = GreeAcIFeelReport(temperature=27).get_raw_timings()
    shifted = [t + shift if i % 2 == 0 and i >= 2 else t for i, t in enumerate(timings)]
    report = GreeAcIFeelReport.from_raw_timings(shifted)
    assert (report and report.temperature) == (expected or None)


def _raw_with_temp(value: int) -> list[int]:
    timings = [5854, -2900]
    for bit in _bits(value) + _bits(0xA5):
        timings += [673, -1580 if bit else -516]
    timings.append(673)
    return timings


def test_fixture_holds_two_captures() -> None:
    """The fixture keeps both report-bearing captures."""
    assert len(_rows()) == 2


@pytest.mark.parametrize("row", _rows(), ids=lambda row: row["t"])
def test_captured_report_decodes_to_27(row: dict) -> None:
    """The captured report burst decodes to 27 deg C."""
    bursts = _split_bursts(_broadlink_timings(row["code"]))
    report = GreeAcIFeelReport.from_raw_timings(bursts[-1])
    assert report is not None
    assert report.temperature == row["report"]["temperature_c"] == 27


@pytest.mark.parametrize("row", _rows(), ids=lambda row: row["t"])
def test_captured_state_bursts_are_not_reports(row: dict) -> None:
    """Negative control: state frames are not reports."""
    bursts = _split_bursts(_broadlink_timings(row["code"]))
    assert len(bursts) >= 3
    for burst in bursts[:-1]:
        assert GreeAcIFeelReport.from_raw_timings(burst) is None


@pytest.mark.parametrize("row", _rows(), ids=lambda row: row["t"])
def test_captured_state_frame_has_ifeel_set(row: dict) -> None:
    """Block B 0x0bc60070 decodes with ifeel=True."""
    assert row["block_b"] == "0bc60070"
    bursts = _split_bursts(_broadlink_timings(row["code"]))
    command = GreeAcCommand.from_raw_timings(
        _state_with_companions(bursts), model=GreeAcModel.YAP1F
    )
    assert command is not None
    assert command.ifeel is True


def _state_with_companions(bursts: list[list[int]]) -> list[int]:
    """Join the first four state bursts into one YAP1F command's timings."""
    timings: list[int] = []
    for burst in bursts[:4]:
        timings += burst
    # The capture ends the last pair with the long space before the report.
    assert timings[-1] < 0
    return timings[:-1]
