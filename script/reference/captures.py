"""Extract recorded WH-TA15PE wire facts from the supplied local checkout."""

import re
from pathlib import Path


def toshiba_states(source: Path) -> list[dict[str, object]]:
    """Read the captured packet table, without importing reference implementations."""
    text = (source / "tests/components/toshiba/toshiba_tests.cpp").read_text()
    table = text.split("CAPTURED_STATES[] = {", 1)[1].split("\n};", 1)[0]
    pattern = (
        r"\{\{([^}]+)\},\s*(\d+),\s*climate::CLIMATE_MODE_(\w+),"
        r'\s*"([^"]+)",\s*"([^"]+)"(?:,\s*(\d+))?\}'
    )
    modes = {"HEAT_COOL": "auto", "HEAT": "heat", "COOL": "cool", "DRY": "dry"}
    fans = {
        "AUTO": 0,
        "QUIET": 1,
        "LOW": 2,
        "Low+": 3,
        "MEDIUM": 4,
        "Medium+": 5,
        "HIGH": 6,
    }
    result = []
    for raw, temperature, mode, fan, preset, power in re.findall(pattern, table):
        result.append(
            {
                "data": bytes(
                    int(value, 16) for value in re.findall(r"0x[0-9A-Fa-f]+", raw)
                ).hex(),
                "temperature": int(temperature),
                "mode": modes[mode],
                "fan": fans[fan],
                "preset": preset.lower().replace(" ", "_"),
                "power_selection": int(power or 0),
            }
        )
    if not result or len(result) != table.count("{{"):
        raise ValueError("recorded WH-TA15PE table contains unsupported rows")
    return result
