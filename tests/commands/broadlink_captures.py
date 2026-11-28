"""Broadlink 0x26 capture helpers shared by the Gree YAP1F capture tests."""

from __future__ import annotations

import base64

# Any space at least this long separates two bursts.
_BURST_GAP = 10000

# Broadlink 0x26 packet tick (tasks-loop broadlink.py).
_TICK_US = 8192 / 269


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
