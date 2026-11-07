"""Tests for remko protocol behavior."""

import json
from pathlib import Path

from infrared_protocols.commands.remko_ar715 import (
    RemkoAr715Command,
    RemkoAr715FanSpeed,
    RemkoAr715Mode,
    RemkoAr715State,
)

_CAPTURES = json.loads(
    (Path(__file__).parents[1] / "fixtures/receiver_captures.json").read_text()
)["captures"]


def test_recorded_remko() -> None:
    """The handheld remote adds a final mark after its 3.5-ms footer space."""
    capture = next(c for c in _CAPTURES if c["protocol"] == "remko")
    result = RemkoAr715Command.from_raw_timings(capture["timings"])
    assert result is not None
    assert result.data == 0x8000000058802
    assert result.state == RemkoAr715State(
        power=False,
        mode=RemkoAr715Mode.COOL,
        temperature=16,
        fan=RemkoAr715FanSpeed.HIGH,
        swing_v=True,
    )
