"""Tests for the Marantz extended (RC-5 + extension) IR command encoder."""

import json
from itertools import product
from pathlib import Path

import pytest

from infrared_protocols.commands.marantz_extended import MarantzExtendedCommand


def test_marantz_extended_get_raw_timings_pm6006_coax() -> None:
    """Encode the PM6006 COAX selector (addr=0x10, cmd=0x01, ext=0x19).

    The expected timing sequence was hand-derived from the protocol
    definition (S1, S2, T, A4..A0 + 4-half-bit pause + C5..C0, E5..E0)
    and matches a real Marantz PM6006 capture to within measurement
    noise (e.g. 889µs encoded vs. 904-965µs captured).
    """
    expected = [
        889,
        -889,
        889,
        -889,
        889,
        -889,
        1778,
        -889,
        889,
        -889,
        889,
        -889,
        889,
        -4445,
        889,
        -889,
        889,
        -889,
        889,
        -889,
        889,
        -889,
        889,
        -1778,
        1778,
        -1778,
        889,
        -889,
        1778,
        -889,
        889,
        -1778,
        889,
    ]
    command = MarantzExtendedCommand(
        address=0x10, command=0x01, extension=0x19, toggle=1
    )
    assert command.get_raw_timings() == expected
    assert command.modulation == 36000


def test_marantz_extended_get_raw_timings_pm6006_network() -> None:
    """Encode the PM6006 NETWORK selector (addr=0x19, cmd=0x3F, ext=0x0A).

    Verifies a frame whose last bit is '0' (so the trailing space is
    stripped) and whose address LSB is '1' (so the pause does not merge
    with a preceding space).
    """
    expected = [
        889,
        -889,
        1778,
        -1778,
        889,
        -889,
        1778,
        -889,
        889,
        -1778,
        889,
        -4445,
        889,
        -889,
        889,
        -889,
        889,
        -889,
        889,
        -889,
        889,
        -889,
        1778,
        -889,
        889,
        -1778,
        1778,
        -1778,
        1778,
    ]
    command = MarantzExtendedCommand(
        address=0x19, command=0x3F, extension=0x0A, toggle=0
    )
    assert command.get_raw_timings() == expected


def test_marantz_extended_repeats_match_rc5_period() -> None:
    """Repeats reuse the standard RC-5 114ms period so the gap is derived."""
    command = MarantzExtendedCommand(
        address=0x10, command=0x01, extension=0x19, toggle=1, repeat_count=2
    )
    base = MarantzExtendedCommand(
        address=0x10, command=0x01, extension=0x19, toggle=1
    ).get_raw_timings()
    timings = command.get_raw_timings()
    frame_duration = sum(abs(t) for t in base)
    gap = 114000 - frame_duration
    assert timings == [*base, -gap, *base, -gap, *base]


def test_marantz_extended_extended_command_clears_s2() -> None:
    """Bit 6 of ``command`` re-purposes S2 (RC5X behaviour, same as RC-5)."""
    standard = MarantzExtendedCommand(
        address=0x10, command=0x01, extension=0x00, toggle=0
    ).get_raw_timings()
    extended = MarantzExtendedCommand(
        address=0x10, command=0x41, extension=0x00, toggle=0
    ).get_raw_timings()
    # Same total duration; differ on the S2 half.
    assert standard != extended
    assert sum(abs(t) for t in standard) == sum(abs(t) for t in extended)
    # S2=0 → frame opens with a merged 1778µs double-burst (S1 burst + S2 burst).
    assert extended[0] == 1778
    assert standard[0] == 889


@pytest.mark.parametrize(
    ("address", "command", "extension"),
    [
        (-1, 0x00, 0x00),
        (0x20, 0x00, 0x00),
        (0x10, -1, 0x00),
        (0x10, 0x80, 0x00),
        (0x10, 0x00, -1),
        (0x10, 0x00, 0x40),
    ],
)
def test_marantz_extended_rejects_out_of_range(
    address: int, command: int, extension: int
) -> None:
    """5-bit address, 7-bit command, 6-bit extension — anything else is invalid."""
    with pytest.raises(ValueError):
        MarantzExtendedCommand(
            address=address, command=command, extension=extension, toggle=0
        )


_CAPTURES = json.loads(
    (Path(__file__).parents[1] / "fixtures/receiver_captures.json").read_text()
)["captures"]

_DECODE_CASES = [
    pytest.param(command, id=type(command).__name__ + "-" + str(vars(command)))
    for command in [
        *[
            MarantzExtendedCommand(
                address=a, command=c, extension=e, toggle=t, repeat_count=r
            )
            for a, c, e, t, r in product((0, 31), (0, 64, 127), (0, 63), (0, 1), (0, 2))
        ]
    ]
]


@pytest.mark.parametrize("scale", [0.88, 0.9, 0.92, 1.1, 1.12, 1.15])
@pytest.mark.parametrize("address", [0, 31])
@pytest.mark.parametrize("command", [0, 63, 64, 127])
@pytest.mark.parametrize("extension", [0, 63])
def test_marantz_clock_skew(
    scale: float, address: int, command: int, extension: int
) -> None:
    """The long pause must not shift all subsequent Manchester cells."""
    sent = MarantzExtendedCommand(address=address, command=command, extension=extension)
    received = MarantzExtendedCommand.from_raw_timings(
        [round(t * scale) for t in sent.get_raw_timings()] + [-5000]
    )
    assert received is not None
    assert (received.address, received.command, received.extension) == (
        address,
        command,
        extension,
    )


@pytest.mark.parametrize(
    "raw,address,command,toggle,extension",
    [
        pytest.param(
            c["timings"],
            c["address"],
            c["command"],
            c["toggle"],
            c["extension"],
            id=f"marantz-{c['address']:x}-{c['command']:x}",
        )
        for c in _CAPTURES
        if c["protocol"] == "marantz"
    ],
)
def test_recorded_marantz(
    raw: list[int], address: int, command: int, toggle: int, extension: int
) -> None:
    """The extended frame retains its command and extension after the long pause."""
    result = MarantzExtendedCommand.from_raw_timings(raw)
    assert result is not None
    assert (result.address, result.command, result.toggle, result.extension) == (
        address,
        command,
        toggle,
        extension,
    )


@pytest.mark.parametrize("command", _DECODE_CASES)
def test_decoder_round_trip_fields(command: MarantzExtendedCommand) -> None:
    """Decode edge-valued fields and preserve their protocol meaning."""
    raw = command.get_raw_timings()
    result = type(command).from_raw_timings(raw)
    assert result is not None
    assert result.get_raw_timings() == raw
    assert result.address == command.address
    assert result.command == command.command
    assert result.extension == command.extension
    assert result.toggle == command.toggle
    assert result.repeat_count == command.repeat_count


@pytest.mark.parametrize("command", _DECODE_CASES)
@pytest.mark.parametrize("prefix", [0, 1, 5])
def test_decoder_truncated(command: MarantzExtendedCommand, prefix: int) -> None:
    """A partial leader or payload cannot be a complete command."""
    assert type(command).from_raw_timings(command.get_raw_timings()[:prefix]) is None
