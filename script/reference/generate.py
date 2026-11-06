"""Regenerate signal fixtures from a local ESPHome checkout and a C++20 compiler.

Run with `uv run python script/reference/generate.py /path/to/ESPHome`.
The checkout is supplied by the caller; this tool never downloads source. Source
extraction and compiled executables stay in a temporary directory. Only measured
outputs and encoder inputs are saved. The installed library does not import or
link these reference encoders.

Cases in the fixture files select inputs from the stage programs. Climate keys
record component:mode:fan:temperature:swing using ESPHome's enum values; the
arguments object records the corresponding Python API inputs. Timing palettes
are lossless: each character indexes the palette using base-36 digits.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from captures import toshiba_states

_DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"


def read_signals(output: str) -> dict[str, tuple[int, list[int]]]:
    """Parse name, carrier and signed durations from the reference executable."""
    result = {}
    for line in output.splitlines():
        name, carrier, *raw = line.split()
        result[name] = int(carrier), list(map(int, raw))
    return result


def main() -> None:
    """Build the reference programs and refresh existing selected cases."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("esphome_source", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "tests/fixtures",
    )
    args = parser.parse_args()
    if not (args.esphome_source / "esphome/components/remote_base").is_dir():
        parser.error("esphome_source must be a complete local ESPHome checkout")
    args.output.joinpath("toshiba_captures.json").write_text(
        json.dumps(
            {
                "source": (
                    "WH-TA15PE handheld captures recorded in ESPHome "
                    "tests/components/toshiba/toshiba_tests.cpp"
                ),
                "states": toshiba_states(args.esphome_source),
            },
            indent=2,
        )
        + "\n"
    )
    signals = {}
    with TemporaryDirectory(prefix="ir-reference-") as directory:
        for stage in (
            "reference",
            "climate_reference",
            "climate_reference2",
            "climate_reference3",
            "climate_reference4",
            "extra_reference",
        ):
            output = subprocess.check_output(
                [
                    sys.executable,
                    str(Path(__file__).with_name(stage + ".py")),
                    str(args.esphome_source.resolve()),
                    directory,
                ],
                text=True,
            )
            signals.update(read_signals(output))
        inputs = json.loads(Path(directory, "inputs.json").read_text())
        inputs.update(json.loads(Path(directory, "extra/inputs.json").read_text()))
    climate_path = args.output / "esphome_climate.json"
    corpus = json.loads(climate_path.read_text())
    corpus.pop("hash_format", None)
    corpus["timing_format"] = (
        "Each base-36 character indexes the signed microsecond palette; "
        "zero-duration spaces omitted"
    )
    for case in corpus["cases"]:
        _, timings = signals[case["key"]]
        palette = list(dict.fromkeys(timings))
        case.pop("sha256", None)
        case["palette"] = palette
        case["timings"] = "".join(_DIGITS[palette.index(t)] for t in timings)
    metadata = {k: v for k, v in corpus.items() if k != "cases"}
    climate_path.write_text(
        json.dumps(metadata, indent=2)[:-2]
        + ',\n  "cases": [\n'
        + ",\n".join("    " + json.dumps(c) for c in corpus["cases"])
        + "\n  ]\n}\n"
    )
    transport_path = args.output / "esphome_protocols.json"
    corpus = json.loads(transport_path.read_text())
    for case in corpus["signals"]:
        carrier, timings = signals[case["protocol"]]
        if case["protocol"] == "toto":
            # The component's transmitter config sends three encoder outputs.
            timings = timings + [-36000] + timings + [-36000] + timings
        case["carrier"], case["timings"] = carrier, timings
        case["input"] = inputs[case["protocol"]]
    transport_path.write_text(json.dumps(corpus, indent=2) + "\n")


if __name__ == "__main__":
    main()
