"""Regenerate signal fixtures from a local ESPHome checkout and a C++20 compiler.

Run with `uv run python script/reference/generate.py /path/to/ESPHome`.
The checkout is supplied by the caller; this tool never downloads source. Source
extraction and compiled executables stay in a temporary directory. Only measured
outputs and encoder inputs are saved. The installed library does not import or
link these reference encoders.

Climate inputs come from cases.py; fixture keys name modes, fans and swing axes.
The arguments object records the corresponding Python API inputs. Timing palettes
are lossless: each character indexes the palette using base-36 digits.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from captures import toshiba_states
from cases import expected_state

_DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"


def read_signals(output: str) -> dict[str, tuple[int, list[int]]]:
    """Parse name, carrier and signed durations from the reference executable."""
    result = {}
    for line in output.splitlines():
        name, carrier, *raw = line.split()
        result[name] = int(carrier), list(map(int, raw))
    return result


def main() -> None:
    """Build reference programs and generate the climate case list from inputs."""
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
    args.output.mkdir(parents=True, exist_ok=True)
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
        climate_inputs = json.loads(Path(directory, "climate_inputs.json").read_text())
    climate_path = args.output / "esphome_climate.json"
    corpus = {
        "source": "ESPHome encoder output",
        "kind": "Synthetic outputs of original C++ encoders, not hardware captures",
    }
    corpus["timing_format"] = (
        "Each base-36 character indexes the signed microsecond palette; "
        "zero-duration spaces omitted"
    )
    corpus["cases"] = []
    for source in climate_inputs:
        index = 0
        while (key := source["key"] + f"@{index}") in signals:
            case = {
                "key": key,
                "factory": source["factory"],
                "arguments": source["arguments"],
            }
            if index:
                if source["component"] not in ("toshiba_1", "toshiba_2"):
                    raise ValueError(f"unmapped transmission: {key}")
                case.update(
                    factory="ToshibaRacCommand.swing",
                    arguments={"enabled": source["swing"] in (1, 2)},
                )
            _, timings = signals[key]
            if timings[0] < 0:
                case["leading_idle"] = -timings[0]
                timings = timings[1:]
            if len(timings) > 1 and timings[-1] < 0 and timings[-2] < 0:
                case["trailing_idle"] = -timings[-1]
                timings = timings[:-1]
            case["expected_state"] = expected_state(case["factory"], case["arguments"])
            palette = list(dict.fromkeys(timings))
            case["palette"] = palette
            case["timings"] = "".join(_DIGITS[palette.index(t)] for t in timings)
            corpus["cases"].append(case)
            index += 1
        if not index:
            raise ValueError(f"no signal for {source['key']}")
    metadata = {k: v for k, v in corpus.items() if k != "cases"}
    climate_path.write_text(
        json.dumps(metadata, indent=2)[:-2]
        + ',\n  "cases": [\n'
        + ",\n".join("    " + json.dumps(c) for c in corpus["cases"])
        + "\n  ]\n}\n"
    )
    transport_path = args.output / "esphome_protocols.json"
    corpus = {
        "source": "ESPHome encoder output",
        "kind": "Synthetic encoder outputs, not hardware captures",
        "signals": [],
    }
    for protocol, input_values in inputs.items():
        carrier, timings = signals[protocol]
        if protocol == "toto":
            # The component's transmitter config sends three encoder outputs.
            timings = timings + [-36000] + timings + [-36000] + timings
        corpus["signals"].append(
            dict(
                protocol=protocol, carrier=carrier, timings=timings, input=input_values
            )
        )
    transport_path.write_text(json.dumps(corpus, indent=2) + "\n")


if __name__ == "__main__":
    main()
