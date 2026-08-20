"""Tests for the Pioneer DVD command codes."""

import pytest

from infrared_protocols.codes.pioneer.dvd import PioneerDVDCode
from infrared_protocols.commands.pioneer import PioneerCommand

# A Pioneer frame is 67 timing entries, and two frames are joined by one gap.
FRAME_ENTRIES = 67
TWO_PART_ENTRIES = 2 * FRAME_ENTRIES + 1


def test_pioneer_dvd_codes_have_no_private_members() -> None:
    """Helper values must not leak into the enum.

    A name with a single leading underscore is not enough to keep it out of an
    ``Enum``: only sunder and dunder names are excluded, so a shared tuple
    prefix declared in the class body would become a member with the wrong
    shape.
    """
    assert [name for name in PioneerDVDCode.__members__ if name.startswith("_")] == []


def test_pioneer_dvd_codes_are_unique() -> None:
    """Every code must be distinct, since duplicates become silent aliases."""
    members = PioneerDVDCode.__members__
    assert len(members) == len(set(members.values()))


@pytest.mark.parametrize(
    ("code", "address", "command"),
    [
        pytest.param(PioneerDVDCode.STOP, 0xA3, 0x98, id="stop"),
        pytest.param(PioneerDVDCode.PLAY, 0xA3, 0x9E, id="play"),
        pytest.param(PioneerDVDCode.PAUSE, 0xA3, 0x9F, id="pause"),
    ],
)
def test_pioneer_dvd_transport_codes_are_single_frame(
    code: PioneerDVDCode, address: int, command: int
) -> None:
    """Transport keys sit in the base command set and need no preamble."""
    built = code.to_command()
    assert isinstance(built, PioneerCommand)
    assert built.preamble_address is None
    assert built.preamble_command is None
    assert built.get_raw_timings() == (
        PioneerCommand(address=address, command=command).get_raw_timings()
    )
    assert len(built.get_raw_timings()) == FRAME_ENTRIES


@pytest.mark.parametrize(
    ("code", "command"),
    [
        pytest.param(PioneerDVDCode.POWER, 0xBC, id="power"),
        pytest.param(PioneerDVDCode.NUM_0, 0xA0, id="num_0"),
        pytest.param(PioneerDVDCode.MENU, 0xB9, id="menu"),
    ],
)
def test_pioneer_dvd_extended_codes_are_two_part(
    code: PioneerDVDCode, command: int
) -> None:
    """Extended keys prepend the preamble that selects their command set."""
    built = code.to_command()
    assert isinstance(built, PioneerCommand)
    assert built.preamble_address == 0xA3
    assert built.preamble_command == 0x99
    assert built.address == 0xAF
    assert built.command == command
    assert len(built.get_raw_timings()) == TWO_PART_ENTRIES


def test_pioneer_dvd_code_set_covers_both_shapes() -> None:
    """The remote mixes both command shapes, so the enum must carry both."""
    single = [code for code in PioneerDVDCode if len(code.value) == 2]
    two_part = [code for code in PioneerDVDCode if len(code.value) == 4]
    assert single
    assert two_part
    assert len(single) + len(two_part) == len(PioneerDVDCode)


def test_pioneer_dvd_code_passes_through_repeat_count() -> None:
    """Repeat count must reach the built command."""
    built = PioneerDVDCode.POWER.to_command(2)
    assert isinstance(built, PioneerCommand)
    assert built.repeat_count == 2
    # Three passes of a two-part command: six frames joined by five gaps.
    assert len(built.get_raw_timings()) == 6 * FRAME_ENTRIES + 5
