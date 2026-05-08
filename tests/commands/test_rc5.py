"""Tests for the RC-5 IR command encoder."""

import pytest

from infrared_protocols.commands.rc5 import RC5Command


def test_rc5_command_get_raw_timings_marantz_volume_up() -> None:
    """Test RC-5 timings for a Marantz amplifier volume-up press.

    Marantz integrated amplifiers (e.g. PM6006) use RC-5 with address
    0x10 (audio amplifier). Command 0x10 is volume up.
    """
    expected_raw_timings = [
        889,
        -889,
        1778,
        -1778,
        1778,
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
        -889,
        889,
        -889,
        889,
        -889,
        889,
    ]
    command = RC5Command(address=0x10, command=0x10, toggle=0, repeat_count=0)
    timings = command.get_raw_timings()
    assert timings == expected_raw_timings
    assert command.modulation == 36000

    # Same command repeated twice with the standard 114ms RC-5 period.
    command_with_repeats = RC5Command(
        address=command.address,
        command=command.command,
        toggle=command.toggle,
        modulation=command.modulation,
        repeat_count=2,
    )
    timings_with_repeats = command_with_repeats.get_raw_timings()
    assert timings_with_repeats == [
        *expected_raw_timings,
        -90886,
        *expected_raw_timings,
        -90886,
        *expected_raw_timings,
    ]


def test_rc5_command_get_raw_timings_zero_address_zero_command() -> None:
    """Test RC-5 timings for the all-zero address/command edge case."""
    expected_raw_timings = [
        889,
        -889,
        1778,
        -889,
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
        889,
    ]
    command = RC5Command(address=0, command=0, toggle=0, repeat_count=0)
    assert command.get_raw_timings() == expected_raw_timings


def test_rc5_command_get_raw_timings_extended() -> None:
    """Test extended RC-5 (RC5X) handling for 7-bit commands.

    With command bit 6 set, the second start bit is repurposed as the
    inverted MSB of the command. The extended frame must differ from
    the standard frame yet preserve the 14-bit total duration.
    """
    extended = RC5Command(address=0x10, command=0x50, toggle=0)
    standard_equivalent = RC5Command(address=0x10, command=0x10, toggle=0)
    extended_timings = extended.get_raw_timings()
    standard_timings = standard_equivalent.get_raw_timings()
    assert extended_timings != standard_timings
    # S1=1, S2=0 means the first two halves are space, pulse, pulse — so
    # after stripping the leading idle space the frame begins with a
    # 1778µs double-burst rather than the 889µs single burst seen in
    # standard RC-5.
    assert extended_timings[0] == 1778
    assert standard_timings[0] == 889
    # Frame total duration is invariant across S2 values.
    assert sum(abs(t) for t in extended_timings) == sum(
        abs(t) for t in standard_timings
    )


def test_rc5_command_extended_triggered_by_command_bit_6() -> None:
    """The extended encoding must key off bit 6, not magnitude.

    ``command=0x40`` is the smallest RC5X command and must produce the
    same S2=0 frame shape as the existing 0x50 case (1778µs double-burst
    leader after stripping the idle space).
    """
    command_0x40 = RC5Command(address=0x10, command=0x40, toggle=0)
    command_0x50 = RC5Command(address=0x10, command=0x50, toggle=0)
    assert command_0x40.get_raw_timings()[0] == 1778
    assert command_0x50.get_raw_timings()[0] == 1778


@pytest.mark.parametrize(
    ("address", "command"),
    [
        (-1, 0x00),
        (0x20, 0x00),
        (0x10, -1),
        (0x10, 0x80),
    ],
)
def test_rc5_command_rejects_out_of_range(address: int, command: int) -> None:
    """RC-5 fields are 5-bit address / 7-bit command — anything else is invalid."""
    with pytest.raises(ValueError):
        RC5Command(address=address, command=command, toggle=0)
