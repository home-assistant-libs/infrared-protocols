"""Tests for the Marantz extended (RC-5 + extension) IR command encoder."""

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
