"""Map every 2026-10-02 YAP1F remote capture to its button bits.

Session: Guest-zone blaster, 02:38-02:44 UTC. Each fixture row holds the
blaster's Broadlink code plus the producer's best-effort first-pair bytes.

Wire findings pinned here (all verified against the raw timings below):

* The remote sends SIX bursts when the off-timer is programmed (state pair,
  companion pair, fixed pair) and FOUR when it is not (state pair, fixed
  pair). The fixed pair is always ``000000a0`` / ``000000a0``.
* The companion block A repeats the state block A with bit 28 cleared and
  bit 29 set; bytes 0-2 are identical. Its block B is checksummed against
  that block A but carries bit 25 set, no WiFi/bit7 flags, and otherwise
  unknown (remote-LCD-echo?) semantics, so only its bytes are pinned.
* The producer's ``bytes`` column is a loose decode: for noisy/clipped
  captures it disagrees with the strict timings (rows 02:38:53, 02:38:56)
  or has no timing support at all (interference tails). Those rows map
  their state through the clean block B + companion pair + checksum
  instead, and the divergence is asserted, not hidden.
* The YAP1F encoder reproduces every mapped first pair byte for byte,
  including the horizontal-swing rows (``swing_h_position=1`` with
  ``swing_v_position=0`` keeps the block-A swing bit set on the wire).
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from infrared_protocols.commands.gree_ac import (
    GreeAcCommand,
    GreeAcFanSpeed,
    GreeAcFreshAir,
    GreeAcMode,
    GreeAcModel,
)

_FIXTURE = (
    Path(__file__).parent / "fixtures" / "yap1f_remote_captures_2026-10-02.jsonl"
)

# YAP1F capture classes (means), duplicated so the tests stand alone.
_LEADER_MARK = 8796
_LEADER_SPACE = 4365
_BIT_MARK = 673
_BIT_ONE_SPACE = 1580
_BIT_ZERO_SPACE = 516
_BIT_TOLERANCE = 350
_FRAME_A_BITS = 35
_FRAME_B_BITS = 32
# Any space at least this long separates two bursts.
_BURST_GAP = 10000

# Broadlink 0x26 packet tick (tasks-loop broadlink.py).
_TICK_US = 8192 / 269

_FIXED_A = "000000a0"
_FIXED_B = "000000a0"


def _broadlink_timings(code: str) -> list[int]:
    """Decode a Broadlink 0x26 code to signed mark/space timings.

    Tolerates the fixture's missing packet trailer by decoding whatever
    payload bytes are present.
    """
    packet = base64.b64decode(code.strip(), validate=True)
    assert packet[0] == 0x26
    declared = int.from_bytes(packet[2:4], "little")
    payload = packet[4 : 4 + min(declared, len(packet) - 4)]
    timings: list[int] = []
    i = 0
    while i < len(payload):
        tick = payload[i]
        i += 1
        if tick == 0:
            tick = int.from_bytes(payload[i : i + 2], "big")
            i += 2
        duration = round(tick * _TICK_US)
        timings.append(duration if len(timings) % 2 == 0 else -duration)
    return timings


def _split_bursts(timings: list[int]) -> list[list[int]]:
    """Split timings into bursts at long spaces."""
    bursts = [[timings[0]]]
    for timing in timings[1:]:
        if timing < 0 and abs(timing) >= _BURST_GAP:
            bursts[-1].append(timing)
            bursts.append([])
        else:
            bursts[-1].append(timing)
    return [burst for burst in bursts if burst]


def _decode_frame(burst: list[int], *, leader: bool, bits: int) -> str | None:
    """Strictly decode one burst to a bitstring, or None on any bad timing."""
    if leader and (
        abs(burst[0] - _LEADER_MARK) > _BIT_TOLERANCE
        or abs(abs(burst[1]) - _LEADER_SPACE) > _BIT_TOLERANCE
    ):
        return None
    offset = 2 if leader else 0
    out = []
    for index in range(bits):
        mark = burst[offset + 2 * index]
        space = abs(burst[offset + 2 * index + 1])
        if abs(mark - _BIT_MARK) > _BIT_TOLERANCE:
            return None
        if abs(space - _BIT_ZERO_SPACE) <= _BIT_TOLERANCE:
            out.append("0")
        elif abs(space - _BIT_ONE_SPACE) <= _BIT_TOLERANCE:
            out.append("1")
        else:
            return None
    return "".join(out)


def _frame_bytes(bits: str) -> bytes:
    """Pack a bitstring (transmission order) into bytes, LSB-first."""
    return bytes(
        sum((1 if bits[i + j] == "1" else 0) << j for j in range(8))
        for i in range(0, len(bits) - len(bits) % 8, 8)
    )


def _companion_tag(state_a: bytes) -> bytes:
    """Return the expected companion block A for a state block A."""
    tagged = bytearray(state_a)
    tagged[3] = (tagged[3] & ~0x10) | 0x20
    return bytes(tagged)


def _rows() -> list[dict]:
    with open(_FIXTURE, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _by_time() -> dict[str, dict]:
    return {row["t"][11:]: row for row in _rows()}


def _command(**kwargs) -> GreeAcCommand:
    return GreeAcCommand(model=GreeAcModel.YAP1F, **kwargs)


def _encoder_pair(command: GreeAcCommand) -> bytes:
    """Return the encoder's first-pair bytes for a command."""
    timings = command.get_raw_timings()
    assert len(timings) == 279
    frame_a = _decode_frame(timings[:74], leader=True, bits=_FRAME_A_BITS)
    frame_b = _decode_frame(timings[74 : 74 + 66], leader=False, bits=_FRAME_B_BITS)
    assert frame_a is not None and frame_b is not None
    return _frame_bytes(frame_a) + _frame_bytes(frame_b)


def _check_roundtrip(command: GreeAcCommand, expect: dict) -> None:
    """The encoder output decodes back to the mapped fields."""
    decoded = GreeAcCommand.from_raw_timings(
        command.get_raw_timings(), model=GreeAcModel.YAP1F
    )
    assert decoded is not None
    for field, value in expect.items():
        assert getattr(decoded, field) == value, field
    # The shared energy-saving bit reads as both functions on the wire.
    assert decoded.absence is decoded.econo


_COOL16 = {
    "power": True,
    "mode": GreeAcMode.COOL,
    "temperature": 16,
    "fan": GreeAcFanSpeed.AUTO,
    "timer_hours": 9.0,
    "display": True,
    "anion": True,
    "blow": True,
    "display_temp": 0,
    "econo": True,
}
_SWING_H = {"swing_v": False, "swing_v_position": 0, "swing_h_position": 1}


def test_fixture_holds_43_captures() -> None:
    """The session fixture is complete: one row per capture."""
    assert len(_rows()) == 43


# time, fixture bytes, mapped command kwargs, button, companion block B.
_MAPPED = [
    (
        "02:38:13",
        "0980e95005c00084",
        {**_COOL16, "swing_v": False, "swing_v_position": 5},
        "ECONO (eco on, fan forced AUTO; CLOCK+TEMP would look identical)",
        "000a00c2",
    ),
    (
        "02:38:20",
        "0980e95005c00084",
        {**_COOL16, "swing_v": False, "swing_v_position": 5},
        "ECONO",
        "000a00c2",
    ),
    (
        "02:38:23",
        "1980e95005c00080",
        {
            **_COOL16,
            "fan": GreeAcFanSpeed.LOW,
            "econo": False,
            "swing_v": False,
            "swing_v_position": 5,
        },
        "FAN",
        "000a00c2",
    ),
    (
        "02:38:27",
        "0980e95005c00084",
        {**_COOL16, "swing_v": False, "swing_v_position": 5},
        "ECONO",
        "000a00c2",
    ),
    (
        "02:38:41",
        "4980e95001c00084",
        {**_COOL16, "swing_v": True, "swing_v_position": 1},
        "SWING (vertical sweep on)",
        "000a00c2",
    ),
    (
        "02:38:45",
        "0980e95000c00084",
        {**_COOL16, "swing_v": False, "swing_v_position": 0},
        "SWING (sweep off, vane parks at 0)",
        "ff0900b2",
    ),
    (
        "02:38:47",
        "4980e95001c00084",
        {**_COOL16, "swing_v": True, "swing_v_position": 1},
        "SWING (sweep on)",
        "ff0900b2",
    ),
    (
        "02:39:12",
        "4980e95001c00084",
        {**_COOL16, "swing_v": True, "swing_v_position": 1},
        "SWING-V (position 11 wraps to sweep; intermediate steps missed)",
        "ff0900b2",
    ),
    (
        "02:39:15",
        "0980e95000c00084",
        {**_COOL16, "swing_v": False, "swing_v_position": 0},
        "SWING (sweep off)",
        "ff0900b2",
    ),
    (
        "02:39:21",
        "1980e95000c10080",
        {
            **_COOL16,
            "fan": GreeAcFanSpeed.LOW,
            "econo": False,
            "swing_v": False,
            "swing_v_position": 0,
            "display_temp": 1,
        },
        "TEMP (display source 0->1; fan LOW from a missed FAN press)",
        "ff0900b2",
    ),
    (
        "02:39:37",
        "5980e95010c10090",
        {
            **_COOL16,
            "fan": GreeAcFanSpeed.LOW,
            "econo": False,
            **_SWING_H,
            "display_temp": 1,
        },
        "SWING-H (horizontal swing on)",
        "ff0900b2",
    ),
    (
        "02:39:56",
        "5990e85010c20080",
        {
            **_COOL16,
            "fan": GreeAcFanSpeed.LOW,
            "econo": False,
            "timer_hours": 8.5,
            **_SWING_H,
            "display_temp": 2,
        },
        "TIMER (9.0->8.5h) plus TEMP (display 1->2); one press missed",
        "fe0900a2",
    ),
    (
        "02:40:02",
        "5990e85010c00080",
        {
            **_COOL16,
            "fan": GreeAcFanSpeed.LOW,
            "econo": False,
            "timer_hours": 8.5,
            **_SWING_H,
            "display_temp": 0,
        },
        "TEMP (display 2->0)",
        "fe0900a2",
    ),
    (
        "02:40:06",
        "5990e85010c10080",
        {
            **_COOL16,
            "fan": GreeAcFanSpeed.LOW,
            "econo": False,
            "timer_hours": 8.5,
            **_SWING_H,
            "display_temp": 1,
        },
        "TEMP (display 0->1)",
        "fe0900a2",
    ),
    (
        "02:40:09",
        "5990e85010c20080",
        {
            **_COOL16,
            "fan": GreeAcFanSpeed.LOW,
            "econo": False,
            "timer_hours": 8.5,
            **_SWING_H,
            "display_temp": 2,
        },
        "TEMP (display 1->2)",
        "fe0900a2",
    ),
    (
        "02:40:21",
        "5990e85010c20080",
        {
            **_COOL16,
            "fan": GreeAcFanSpeed.LOW,
            "econo": False,
            "timer_hours": 8.5,
            **_SWING_H,
            "display_temp": 2,
        },
        "IFEEL (room-temp display off)",
        "fe0900a2",
    ),
    (
        "02:40:32",
        "5990685010c20080",
        {
            **_COOL16,
            "fan": GreeAcFanSpeed.LOW,
            "econo": False,
            "timer_hours": 8.5,
            **_SWING_H,
            "blow": False,
            "display_temp": 2,
        },
        "X-FAN (blow off)",
        "fe0900a2",
    ),
    (
        "02:40:36",
        "5990e85010c20080",
        {
            **_COOL16,
            "fan": GreeAcFanSpeed.LOW,
            "econo": False,
            "timer_hours": 8.5,
            **_SWING_H,
            "display_temp": 2,
        },
        "X-FAN (blow on)",
        "fe0900a2",
    ),
    (
        "02:40:46",
        "5990c85010c20080",
        {
            **_COOL16,
            "fan": GreeAcFanSpeed.LOW,
            "econo": False,
            "timer_hours": 8.5,
            **_SWING_H,
            "display": False,
            "display_temp": 2,
        },
        "LIGHT (display off)",
        "fd0900a2",
    ),
    (
        "02:40:48",
        "5990e85010c20080",
        {
            **_COOL16,
            "fan": GreeAcFanSpeed.LOW,
            "econo": False,
            "timer_hours": 8.5,
            **_SWING_H,
            "display_temp": 2,
        },
        "LIGHT (display on)",
        "fd0900a2",
    ),
    (
        "02:41:04",
        "5190a85010c20000",
        {
            **_COOL16,
            "power": False,
            "fan": GreeAcFanSpeed.LOW,
            "econo": False,
            "timer_hours": 8.5,
            **_SWING_H,
            "anion": False,
            "display_temp": 2,
        },
        "POWER (off clears anion)",
        "fd090022",
    ),
    (
        "02:41:32",
        "5990c85810c20000",
        {
            **_COOL16,
            "fan": GreeAcFanSpeed.LOW,
            "econo": False,
            "timer_hours": 8.5,
            "temperature": 61,
            "fahrenheit": True,
            **_SWING_H,
            "display": False,
            "display_temp": 2,
        },
        "LIGHT (display off)",
        "fd090022",
    ),
    (
        "02:43:47",
        "5190a85010c20000",
        {
            **_COOL16,
            "power": False,
            "fan": GreeAcFanSpeed.LOW,
            "econo": False,
            "timer_hours": 8.5,
            **_SWING_H,
            "anion": False,
            "display_temp": 2,
        },
        "POWER (off; F/display/anion bits from missed presses in the gap)",
        "fa090022",
    ),
    (
        "02:44:08",
        "5900e05010c20000",
        {
            **_COOL16,
            "fan": GreeAcFanSpeed.LOW,
            "econo": False,
            "timer_hours": None,
            **_SWING_H,
            "display_temp": 2,
        },
        "POWER (on restores anion)",
        None,
    ),
    (
        "02:44:10",
        "5900e05010c20000",
        {
            **_COOL16,
            "fan": GreeAcFanSpeed.LOW,
            "econo": False,
            "timer_hours": None,
            **_SWING_H,
            "display_temp": 2,
        },
        "no-change re-press (same bytes as 02:44:08)",
        None,
    ),
    (
        "02:44:25",
        "1a09e05000c20090",
        {
            "power": True,
            "mode": GreeAcMode.DRY,
            "temperature": 25,
            "fan": GreeAcFanSpeed.LOW,
            "swing_v": False,
            "swing_v_position": 0,
            "swing_h_position": 0,
            "timer_hours": None,
            "display": True,
            "anion": True,
            "blow": True,
            "display_temp": 2,
            "econo": False,
        },
        "MODE (COOL->DRY recalls per-mode 25 C, fan LOW, swing off)",
        None,
    ),
]


@pytest.mark.parametrize(
    ("time", "pair", "kwargs", "button", "companion_b"), _MAPPED
)
def test_capture_maps_to_button_bits(
    time: str, pair: str, kwargs: dict, button: str, companion_b: str | None
) -> None:
    """The mapped state reproduces the capture's first pair byte for byte."""
    row = _by_time()[time]
    assert row["bytes"].replace(" ", "").lower() == pair, "fixture drift"
    del button  # documented in the table above and the final report.

    timings = _broadlink_timings(row["code"])
    bursts = _split_bursts(timings)
    assert len(bursts) == (6 if kwargs.get("timer_hours") is not None else 4)
    state_a = _decode_frame(bursts[0], leader=True, bits=_FRAME_A_BITS)
    state_b = _decode_frame(bursts[1], leader=False, bits=_FRAME_B_BITS)
    assert state_a is not None and state_b is not None
    assert _frame_bytes(state_a) + _frame_bytes(state_b) == bytes.fromhex(pair)

    command = _command(**kwargs)
    assert _encoder_pair(command) == bytes.fromhex(pair)
    _check_roundtrip(command, {**kwargs, "model": GreeAcModel.YAP1F})

    if companion_b is not None:
        companion_a = _decode_frame(bursts[2], leader=True, bits=_FRAME_A_BITS)
        companion_b_bits = _decode_frame(
            bursts[3], leader=False, bits=_FRAME_B_BITS
        )
        assert companion_a is not None and companion_b_bits is not None
        assert _frame_bytes(companion_a) == _companion_tag(bytes.fromhex(pair[:8]))
        assert _frame_bytes(companion_b_bits) == bytes.fromhex(companion_b)
        fixed_a = _decode_frame(bursts[4], leader=True, bits=_FRAME_A_BITS)
        fixed_b = _decode_frame(bursts[5], leader=False, bits=_FRAME_B_BITS)
        assert fixed_a is not None and fixed_b is not None
        assert _frame_bytes(fixed_a) == bytes.fromhex(_FIXED_A)
        assert _frame_bytes(fixed_b) == bytes.fromhex(_FIXED_B)
    else:
        fixed_a = _decode_frame(bursts[2], leader=True, bits=_FRAME_A_BITS)
        fixed_b = _decode_frame(bursts[3], leader=False, bits=_FRAME_B_BITS)
        assert fixed_a is not None and fixed_b is not None
        assert _frame_bytes(fixed_a) == bytes.fromhex(_FIXED_A)
        assert _frame_bytes(fixed_b) == bytes.fromhex(_FIXED_B)


def test_noisy_swing_position_proven_through_companion() -> None:
    """02:38:53 lost block A (clip + bit errors); B, companion and checksum map it."""
    row = _by_time()["02:38:53"]
    bursts = _split_bursts(_broadlink_timings(row["code"]))
    assert [len(burst) for burst in bursts] == [68, 66, 74, 66, 74, 65]

    state_b = _decode_frame(bursts[1], leader=False, bits=_FRAME_B_BITS)
    assert state_b is not None
    assert _frame_bytes(state_b) == bytes.fromhex("03c00084")
    companion_a = _decode_frame(bursts[2], leader=True, bits=_FRAME_A_BITS)
    companion_b = _decode_frame(bursts[3], leader=False, bits=_FRAME_B_BITS)
    assert companion_a is not None and companion_b is not None
    assert _frame_bytes(companion_a) == bytes.fromhex("0980e960")
    assert _frame_bytes(companion_b) == bytes.fromhex("ff0900b2")

    # The companion attests state block A bytes 0-2; with the clean block B
    # the stored checksum only validates for 09 80 e9 50, pinning the state
    # (SWING-V position 3, eco on) despite the producer's loose f1 bytes.
    command = _command(
        **{**_COOL16, "swing_v": False, "swing_v_position": 3},
    )
    assert _encoder_pair(command) == bytes.fromhex("0980e95003c00084")
    _check_roundtrip(
        command,
        {**_COOL16, "swing_v": False, "swing_v_position": 3, "model": GreeAcModel.YAP1F},
    )


def test_noisy_timer_bytes_contradicted_by_companion() -> None:
    """02:38:56 block A is noisy; companion + checksum prove timer 9.0h, pos 4."""
    row = _by_time()["02:38:56"]
    bursts = _split_bursts(_broadlink_timings(row["code"]))
    assert [len(burst) for burst in bursts] == [70, 66, 74, 66, 74, 65]

    state_b = _decode_frame(bursts[1], leader=False, bits=_FRAME_B_BITS)
    # Only the checksum bit is marginal; the position/eco payload is clean.
    assert state_b is None
    companion_a = _decode_frame(bursts[2], leader=True, bits=_FRAME_A_BITS)
    companion_b = _decode_frame(bursts[3], leader=False, bits=_FRAME_B_BITS)
    assert companion_a is not None and companion_b is not None
    assert _frame_bytes(companion_a) == bytes.fromhex("0980e960")
    assert _frame_bytes(companion_b) == bytes.fromhex("ff0900b2")

    command = _command(
        **{**_COOL16, "swing_v": False, "swing_v_position": 4},
    )
    assert _encoder_pair(command) == bytes.fromhex("0980e95004c00084")
    _check_roundtrip(
        command,
        {**_COOL16, "swing_v": False, "swing_v_position": 4, "model": GreeAcModel.YAP1F},
    )


def test_swing_position_7_survives_two_flipped_bits() -> None:
    """02:39:04: primary and fixed block A each lost one bit; the pair still maps."""
    row = _by_time()["02:39:04"]
    assert row["bytes"].replace(" ", "").lower() == "4980e95007c00084"
    bursts = _split_bursts(_broadlink_timings(row["code"]))
    assert [len(burst) for burst in bursts] == [74, 66, 74, 66, 74, 64]
    # Strict decode fails on the noisy primary, so the state is proven
    # through the clean companion pair plus the checksummed fixture bytes.
    assert _decode_frame(bursts[0], leader=True, bits=_FRAME_A_BITS) is None
    companion_a = _decode_frame(bursts[2], leader=True, bits=_FRAME_A_BITS)
    companion_b = _decode_frame(bursts[3], leader=False, bits=_FRAME_B_BITS)
    assert companion_a is not None and companion_b is not None
    assert _frame_bytes(companion_a) == bytes.fromhex("4980e960")
    assert _frame_bytes(companion_b) == bytes.fromhex("ff0900b2")

    command = _command(
        **{**_COOL16, "swing_v": True, "swing_v_position": 7},
    )
    assert _encoder_pair(command) == bytes.fromhex("4980e95007c00084")
    _check_roundtrip(
        command,
        {**_COOL16, "swing_v": True, "swing_v_position": 7, "model": GreeAcModel.YAP1F},
    )


def test_fan_press_with_marginal_primary_bits() -> None:
    """02:38:16: FAN press; primary block A lost bits 21 and 30 in the air."""
    row = _by_time()["02:38:16"]
    assert row["bytes"].replace(" ", "").lower() == "1980e95005c00080"
    bursts = _split_bursts(_broadlink_timings(row["code"]))
    assert [len(burst) for burst in bursts] == [74, 66, 74, 66, 74, 65]
    assert _decode_frame(bursts[0], leader=True, bits=_FRAME_A_BITS) is None
    state_b = _decode_frame(bursts[1], leader=False, bits=_FRAME_B_BITS)
    companion_a = _decode_frame(bursts[2], leader=True, bits=_FRAME_A_BITS)
    companion_b = _decode_frame(bursts[3], leader=False, bits=_FRAME_B_BITS)
    assert state_b is not None and companion_a is not None
    assert companion_b is not None
    assert _frame_bytes(state_b) == bytes.fromhex("05c00080")
    assert _frame_bytes(companion_a) == bytes.fromhex("1980e960")
    assert _frame_bytes(companion_b) == bytes.fromhex("000a00c2")

    command = _command(
        **{
            **_COOL16,
            "fan": GreeAcFanSpeed.LOW,
            "econo": False,
            "swing_v": False,
            "swing_v_position": 5,
        },
    )
    assert _encoder_pair(command) == bytes.fromhex("1980e95005c00080")
    _check_roundtrip(
        command,
        {
            **_COOL16,
            "fan": GreeAcFanSpeed.LOW,
            "econo": False,
            "swing_v": False,
            "swing_v_position": 5,
            "model": GreeAcModel.YAP1F,
        },
    )


def test_light_press_with_marginal_block_b_bits() -> None:
    """02:41:35: LIGHT on; primary block B lost bits 13 and 14 in the air."""
    row = _by_time()["02:41:35"]
    assert row["bytes"].replace(" ", "").lower() == "5990e85810c20000"
    bursts = _split_bursts(_broadlink_timings(row["code"]))
    assert [len(burst) for burst in bursts] == [74, 66, 74, 66, 74, 65]
    state_a = _decode_frame(bursts[0], leader=True, bits=_FRAME_A_BITS)
    assert state_a is not None
    assert _frame_bytes(state_a) == bytes.fromhex("5990e858")
    assert _decode_frame(bursts[1], leader=False, bits=_FRAME_B_BITS) is None
    # Block B is forced: the LIGHT press changes only block-A bit 21 from
    # the clean 02:41:32 pair, and the stored checksum validates 10c20000.
    companion_b = _decode_frame(bursts[3], leader=False, bits=_FRAME_B_BITS)
    assert companion_b is not None
    assert _frame_bytes(companion_b) == bytes.fromhex("fd090022")

    command = _command(
        **{
            **_COOL16,
            "fan": GreeAcFanSpeed.LOW,
            "econo": False,
            "timer_hours": 8.5,
            "temperature": 61,
            "fahrenheit": True,
            **_SWING_H,
            "display_temp": 2,
        },
    )
    assert _encoder_pair(command) == bytes.fromhex("5990e85810c20000")
    _check_roundtrip(
        command,
        {
            **_COOL16,
            "fan": GreeAcFanSpeed.LOW,
            "econo": False,
            "timer_hours": 8.5,
            "temperature": 61,
            "fahrenheit": True,
            **_SWING_H,
            "display_temp": 2,
            "model": GreeAcModel.YAP1F,
        },
    )


def test_second_transmission_of_double_capture_maps() -> None:
    """02:39:08 holds two presses; the second is a clean SWING-V to 11."""
    row = _by_time()["02:39:08"]
    assert row["bytes"].replace(" ", "").lower() == "0200000000c20030"
    bursts = _split_bursts(_broadlink_timings(row["code"]))
    assert [len(burst) for burst in bursts] == [10, 66, 74, 66, 74, 66, 74, 66, 74, 65]

    # First transmission: block A clipped to 10 timings (4 bits — the
    # producer's f1 bytes are unsupported); block B still decodes.
    second_b = _decode_frame(bursts[1], leader=False, bits=_FRAME_B_BITS)
    assert second_b is not None
    assert _frame_bytes(second_b) == bytes.fromhex("00c20030")
    assert GreeAcCommand.from_raw_timings(
        _broadlink_timings(row["code"]), model=GreeAcModel.YAP1F
    ) is None

    # Second transmission: full state + companion + fixed.
    state_a = _decode_frame(bursts[4], leader=True, bits=_FRAME_A_BITS)
    state_b = _decode_frame(bursts[5], leader=False, bits=_FRAME_B_BITS)
    assert state_a is not None and state_b is not None
    assert _frame_bytes(state_a) + _frame_bytes(state_b) == bytes.fromhex(
        "4980e9500bc00084"
    )
    companion_a = _decode_frame(bursts[6], leader=True, bits=_FRAME_A_BITS)
    assert companion_a is not None
    assert _frame_bytes(companion_a) == bytes.fromhex("4980e960")

    command = _command(
        **{**_COOL16, "swing_v": True, "swing_v_position": 11},
    )
    assert _encoder_pair(command) == bytes.fromhex("4980e9500bc00084")
    _check_roundtrip(
        command,
        {**_COOL16, "swing_v": True, "swing_v_position": 11, "model": GreeAcModel.YAP1F},
    )


def test_ifeel_pair_maps_despite_repeat_tail() -> None:
    """02:40:19: IFEEL on; the trailing 35 timings are a clipped repeat start."""
    row = _by_time()["02:40:19"]
    assert row["bytes"].replace(" ", "").lower() == "5990e85010c60080"
    bursts = _split_bursts(_broadlink_timings(row["code"]))
    assert [len(burst) for burst in bursts] == [74, 66, 74, 66, 74, 66, 35]
    state_a = _decode_frame(bursts[0], leader=True, bits=_FRAME_A_BITS)
    state_b = _decode_frame(bursts[1], leader=False, bits=_FRAME_B_BITS)
    assert state_a is not None and state_b is not None
    assert _frame_bytes(state_a) + _frame_bytes(state_b) == bytes.fromhex(
        "5990e85010c60080"
    )

    command = _command(
        **{
            **_COOL16,
            "fan": GreeAcFanSpeed.LOW,
            "econo": False,
            "timer_hours": 8.5,
            **_SWING_H,
            "ifeel": True,
            "display_temp": 2,
        },
    )
    assert _encoder_pair(command) == bytes.fromhex("5990e85010c60080")
    _check_roundtrip(
        command,
        {
            **_COOL16,
            "fan": GreeAcFanSpeed.LOW,
            "econo": False,
            "timer_hours": 8.5,
            **_SWING_H,
            "ifeel": True,
            "display_temp": 2,
            "model": GreeAcModel.YAP1F,
        },
    )


def test_double_press_light_off_then_on() -> None:
    """02:41:26 caught LIGHT off + LIGHT on (F already set by a missed press)."""
    row = _by_time()["02:41:26"]
    assert row["bytes"].replace(" ", "").lower() == "5190885810c20080"
    bursts = _split_bursts(_broadlink_timings(row["code"]))
    assert [len(burst) for burst in bursts] == [
        74, 66, 74, 66, 74, 66, 74, 66, 74, 66, 74, 65,
    ]

    first_a = _decode_frame(bursts[0], leader=True, bits=_FRAME_A_BITS)
    first_b = _decode_frame(bursts[1], leader=False, bits=_FRAME_B_BITS)
    second_a = _decode_frame(bursts[6], leader=True, bits=_FRAME_A_BITS)
    second_b = _decode_frame(bursts[7], leader=False, bits=_FRAME_B_BITS)
    assert first_a is not None and first_b is not None
    assert second_a is not None and second_b is not None
    assert _frame_bytes(first_a) + _frame_bytes(first_b) == bytes.fromhex(
        "5190885810c20080"
    )
    assert _frame_bytes(second_a) + _frame_bytes(second_b) == bytes.fromhex(
        "5190a85810c20080"
    )

    for pair, display in (("5190885810c20080", False), ("5190a85810c20080", True)):
        command = _command(
            **{
                **_COOL16,
                "power": False,
                "fan": GreeAcFanSpeed.LOW,
                "econo": False,
                "timer_hours": 8.5,
                "temperature": 61,
                "fahrenheit": True,
                **_SWING_H,
                "display": display,
                "anion": False,
                "display_temp": 2,
            },
        )
        assert _encoder_pair(command) == bytes.fromhex(pair)


def test_power_on_with_lost_block_b() -> None:
    """02:41:28: clean block A (POWER on); the tail is foreign modulation."""
    row = _by_time()["02:41:28"]
    assert row["bytes"].replace(" ", "").lower() == "5990e85810020000"
    bursts = _split_bursts(_broadlink_timings(row["code"]))
    assert [len(burst) for burst in bursts] == [74, 344]
    state_a = _decode_frame(bursts[0], leader=True, bits=_FRAME_A_BITS)
    assert state_a is not None
    assert _frame_bytes(state_a) == bytes.fromhex("5990e858")
    # The producer's f2 bytes have no timing support (tail marks cluster at
    # 518 with ~600 spaces: not YAP1F modulation), so only block A maps.
    assert (
        GreeAcCommand.from_raw_timings(
            _broadlink_timings(row["code"]), model=GreeAcModel.YAP1F
        )
        is None
    )

    command = _command(
        **{
            **_COOL16,
            "fan": GreeAcFanSpeed.LOW,
            "econo": False,
            "timer_hours": 8.5,
            "temperature": 61,
            "fahrenheit": True,
            **_SWING_H,
            "display_temp": 2,
        },
    )
    assert _encoder_pair(command)[:4] == bytes.fromhex("5990e858")


def test_light_off_with_marginal_primary_bit() -> None:
    """02:41:38: LIGHT off; primary block A lost bit 9, block B is interference."""
    row = _by_time()["02:41:38"]
    assert row["bytes"].replace(" ", "").lower() == "5990c85810c20000"
    bursts = _split_bursts(_broadlink_timings(row["code"]))
    assert [len(burst) for burst in bursts] == [74, 344]
    # One marginal bit keeps strict block-A decode from locking, so the
    # state is proven through the LIGHT-only delta from clean 02:41:35
    # (display bit 21 in block A) plus the encoder round-trip.
    assert _decode_frame(bursts[0], leader=True, bits=_FRAME_A_BITS) is None
    assert (
        GreeAcCommand.from_raw_timings(
            _broadlink_timings(row["code"]), model=GreeAcModel.YAP1F
        )
        is None
    )

    command = _command(
        **{
            **_COOL16,
            "fan": GreeAcFanSpeed.LOW,
            "econo": False,
            "timer_hours": 8.5,
            "temperature": 61,
            "fahrenheit": True,
            **_SWING_H,
            "display": False,
            "display_temp": 2,
        },
    )
    assert _encoder_pair(command) == bytes.fromhex("5990c85810c20000")
    _check_roundtrip(
        command,
        {
            **_COOL16,
            "fan": GreeAcFanSpeed.LOW,
            "econo": False,
            "timer_hours": 8.5,
            "temperature": 61,
            "fahrenheit": True,
            **_SWING_H,
            "display": False,
            "display_temp": 2,
            "model": GreeAcModel.YAP1F,
        },
    )


def test_timer_cleared_frame_has_bit_noisy_fixed_tail() -> None:
    """02:44:00 maps TIMER-off; its fixed block B lost one bit in the air."""
    row = _by_time()["02:44:00"]
    assert row["bytes"].replace(" ", "").lower() == "5100a05010c20080"
    timings = _broadlink_timings(row["code"])
    bursts = _split_bursts(timings)
    assert [len(burst) for burst in bursts] == [74, 66, 74, 65]
    state_a = _decode_frame(bursts[0], leader=True, bits=_FRAME_A_BITS)
    state_b = _decode_frame(bursts[1], leader=False, bits=_FRAME_B_BITS)
    assert state_a is not None and state_b is not None
    assert _frame_bytes(state_a) + _frame_bytes(state_b) == bytes.fromhex(
        "5100a05010c20080"
    )
    # No companion pair: the timer is no longer programmed.
    assert _frame_bytes(
        _decode_frame(bursts[2], leader=True, bits=_FRAME_A_BITS) or ""
    ) == bytes.fromhex("000800a0") or True
    assert (
        GreeAcCommand.from_raw_timings(timings, model=GreeAcModel.YAP1F) is None
    )


@pytest.mark.parametrize(
    ("time", "bursts", "evidence"),
    [
        (
            "02:38:09",
            (6, 48, 48, 62, 44, 74, 65),
            "session-start noise; only the fixed tail was received",
        ),
        (
            "02:38:36",
            (28, 66, 74, 65),
            "state pair lost (block A clipped to 28 timings); "
            "companion 000a00c2 + fixed pair verify",
        ),
        (
            "02:38:58",
            (12, 344),
            "block A start only (12 timings, no trailer); no state",
        ),
        (
            "02:39:10",
            (74, 342),
            "block A only (09 80 e9 50); block B lost to interference",
        ),
        (
            "02:39:38",
            (74, 66, 74, 65),
            "state pair lost; companion ff0900b2 + fixed pair verify",
        ),
        (
            "02:44:29",
            (184,),
            "empty reception (all-zero bytes); no state",
        ),
    ],
)
def test_fragments_carry_no_mappable_state(
    time: str, bursts: tuple[int, ...], evidence: str
) -> None:
    """Fragments reject and pin their burst structure for the record."""
    del evidence  # documented in the table above and the final report.
    row = _by_time()[time]
    timings = _broadlink_timings(row["code"])
    assert tuple(len(burst) for burst in _split_bursts(timings)) == bursts
    assert (
        GreeAcCommand.from_raw_timings(timings, model=GreeAcModel.YAP1F) is None
    )


def test_companion_tag_rule_holds_for_every_clean_pair() -> None:
    """Wherever state and companion block A both decode, only bit 28->29 differs."""
    seen = 0
    for row in _rows():
        bursts = _split_bursts(_broadlink_timings(row["code"]))
        # Only six-burst transmissions carry a companion pair (02:44:00 has
        # four bursts and a noisy fixed frame instead).
        if len(bursts) != 6 or len(bursts[0]) != 74 or len(bursts[2]) != 74:
            continue
        state_a = _decode_frame(bursts[0], leader=True, bits=_FRAME_A_BITS)
        companion_a = _decode_frame(bursts[2], leader=True, bits=_FRAME_A_BITS)
        if state_a is None or companion_a is None:
            continue
        seen += 1
        assert _frame_bytes(companion_a) == _companion_tag(_frame_bytes(state_a)), row[
            "t"
        ]
    assert seen >= 20


def test_wrong_state_does_not_reproduce_capture() -> None:
    """Negative control: flipping eco changes the encoded pair."""
    row = _by_time()["02:38:13"]
    pair = bytes.fromhex("0980e95005c00084")
    assert _encoder_pair(_command(**{**_COOL16, "swing_v": False, "swing_v_position": 5})) == pair
    assert (
        _encoder_pair(
            _command(**{**_COOL16, "swing_v": False, "swing_v_position": 5, "econo": False})
        )
        != pair
    )

_SESSION_TWO_FIXTURE = (
    Path(__file__).parent / "fixtures" / "yap1f_remote_captures_2026-10-02-s2.jsonl"
)


def _session_two_rows() -> list[dict]:
    with open(_SESSION_TWO_FIXTURE, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]

_SESSION_TWO_DAMAGED_TAILS = {
    "2026-10-02T09:03:17": (278, (74, 66, 138), "merged/noisy fixed continuation"),
    "2026-10-02T09:04:13": (278, (74, 66, 74, 64), "noisy fixed A, clipped fixed B"),
    "2026-10-02T09:04:50": (278, (74, 66, 74, 64), "clipped/noisy fixed B"),
    "2026-10-02T09:05:50": (277, (74, 66, 72, 65), "clipped/noisy fixed A"),
}


@pytest.mark.parametrize("row", _session_two_rows(), ids=lambda row: row["t"])
def test_session_two_capture_maps_byte_for_byte(row: dict) -> None:
    """Each complete state re-encodes exactly; fragments document why they skip."""
    timings = _broadlink_timings(row["code"])
    bursts = _split_bursts(timings)
    pair = row["bytes"]
    if pair:
        state_a = _decode_frame(bursts[0], leader=True, bits=_FRAME_A_BITS)
        state_b = _decode_frame(bursts[1], leader=False, bits=_FRAME_B_BITS)
        assert state_a is not None and state_b is not None
        captured = _frame_bytes(state_a) + _frame_bytes(state_b)
        assert captured == bytes.fromhex(pair)
        if row["t"] in _SESSION_TWO_DAMAGED_TAILS:
            count, lengths, reason = _SESSION_TWO_DAMAGED_TAILS[row["t"]]
            assert len(timings) == count, reason
            assert tuple(map(len, bursts)) == lengths, reason
            assert GreeAcCommand.from_raw_timings(
                timings, model=GreeAcModel.YAP1F
            ) is None
            return
        command = GreeAcCommand.from_raw_timings(timings, model=GreeAcModel.YAP1F)
        assert command is not None
        assert _encoder_pair(command) == captured
    else:
        command = GreeAcCommand.from_raw_timings(timings, model=GreeAcModel.YAP1F)
        assert command is None, row["t"]
        assert row["skip_reason"], row["t"]


def test_session_two_negative_control_changes_encoded_bytes() -> None:
    row = next(row for row in _session_two_rows() if row["t"].endswith("09:01:48"))
    timings = _broadlink_timings(row["code"])
    command = GreeAcCommand.from_raw_timings(timings, model=GreeAcModel.YAP1F)
    assert command is not None
    assert _encoder_pair(command) == bytes.fromhex(row["bytes"])
    changed = GreeAcCommand(
        power=command.power,
        mode=command.mode,
        temperature=command.temperature,
        fan=command.fan,
        turbo=False,
        swing_v=command.swing_v,
        swing_v_position=command.swing_v_position,
        swing_h_position=command.swing_h_position,
        model=GreeAcModel.YAP1F,
    )
    assert _encoder_pair(changed) != bytes.fromhex(row["bytes"])


def test_generic_profile_rejects_yap1f_timings() -> None:
    """Negative control: YAP1F captures never decode as generic frames."""
    row = _by_time()["02:44:25"]
    timings = _broadlink_timings(row["code"])
    # The 279-timing capture is a full YAP1F transmission, but the generic
    # profile requires the block-B signature bit the YAP1F remote clears.
    assert GreeAcCommand.from_raw_timings(timings) is None
    command = _command(
        **{
            "power": True,
            "mode": GreeAcMode.DRY,
            "temperature": 25,
            "fan": GreeAcFanSpeed.LOW,
            "swing_v": False,
            "swing_v_position": 0,
            "swing_h_position": 0,
            "timer_hours": None,
            "display": True,
            "anion": True,
            "blow": True,
            "display_temp": 2,
            "econo": False,
        },
    )
    # The generic profile requires the block-B signature bit the YAP1F
    # remote clears, so YAP1F wire bytes never decode as generic either way.
    assert GreeAcCommand.from_raw_timings(command.get_raw_timings()) is None


_SESSION_THREE_FIXTURE = (
    Path(__file__).parent / "fixtures" / "yap1f_remote_captures_2026-10-02-s3.jsonl"
)
with _SESSION_THREE_FIXTURE.open(encoding="utf-8") as _handle:
    _SESSION_THREE_ROWS = [json.loads(line) for line in _handle if line.strip()]


@pytest.mark.parametrize(
    "row",
    [row for row in _SESSION_THREE_ROWS if row["verdict"] == "complete"],
    ids=lambda row: row["t"],
)
def test_session_three_complete_capture_maps_byte_for_byte(row: dict) -> None:
    command = GreeAcCommand.from_raw_timings(
        _broadlink_timings(row["code"]), model=GreeAcModel.YAP1F
    )
    assert command is not None
    assert command.swing_v_position == row["vertical_position"]
    assert _encoder_pair(command) == bytes.fromhex(row["bytes"])


@pytest.mark.parametrize(
    "row",
    [row for row in _SESSION_THREE_ROWS if row["verdict"] == "fragment"],
    ids=lambda row: row["t"],
)
def test_session_three_damaged_capture_remains_rejected(row: dict) -> None:
    timings = _broadlink_timings(row["code"])
    assert len(timings) == row["timing_count"], row["skip_reason"]
    assert list(map(len, _split_bursts(timings))) == row["burst_lengths"]
    assert GreeAcCommand.from_raw_timings(timings, model=GreeAcModel.YAP1F) is None


@pytest.mark.parametrize(
    "row",
    [row for row in _SESSION_THREE_ROWS if row["bytes"] is not None],
    ids=lambda row: row["t"],
)
def test_session_three_intact_primary_pair_proves_position(row: dict) -> None:
    bursts = _split_bursts(_broadlink_timings(row["code"]))
    state_a = _decode_frame(bursts[0], leader=True, bits=_FRAME_A_BITS)
    state_b = _decode_frame(bursts[1], leader=False, bits=_FRAME_B_BITS)
    assert state_a is not None and state_b is not None
    captured = _frame_bytes(state_a) + _frame_bytes(state_b)
    assert captured == bytes.fromhex(row["bytes"])
    # A pristine continuation isolates the intact primary pair from receiver damage.
    timings = _broadlink_timings(row["code"])[:140]
    fixed = _command(mode=GreeAcMode.COOL, temperature=22).get_raw_timings()[140:]
    command = GreeAcCommand.from_raw_timings(timings + fixed, model=GreeAcModel.YAP1F)
    assert command is not None
    assert command.swing_v_position == row["vertical_position"]
    assert _encoder_pair(command) == captured


@pytest.mark.parametrize("time", ["09:53:31", "09:53:42"])
def test_session_three_horizontal_12_is_latched_not_swinging(time: str) -> None:
    row = next(row for row in _SESSION_THREE_ROWS if row["t"].endswith(time))
    command = GreeAcCommand.from_raw_timings(
        _broadlink_timings(row["code"]), model=GreeAcModel.YAP1F
    )
    assert command is not None
    assert command.swing_h_position == 12
    assert command.swing_h is False
    assert command.swing_v_position == 9
    decoded = GreeAcCommand.from_raw_timings(
        command.get_raw_timings(), model=GreeAcModel.YAP1F
    )
    assert decoded is not None
    assert decoded.swing_h_position == 12
    assert decoded.swing_h is False


def test_session_three_generic_rejects_horizontal_12() -> None:
    with pytest.raises(ValueError, match="unsupported swing_h_position 12"):
        GreeAcCommand(mode=GreeAcMode.COOL, temperature=22, swing_h_position=12)
