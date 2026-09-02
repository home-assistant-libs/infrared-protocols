"""Tests for the Sony television command codes."""

import pytest

from infrared_protocols.codes.sony.tv import (
    SONY_TV_ADDRESS,
    SONY_TV_ADDRESS_BITS,
    SonyTVCode,
)
from infrared_protocols.commands.sony import SonyCommand

# Leader, then two entries per bit for 12 bits, then the trailer.
SIRC12_ENTRIES = 26
SIRC_FRAME_PERIOD_US = 45000


def test_sony_tv_codes_are_unique() -> None:
    """Every code must be distinct, since duplicates become silent aliases."""
    members = SonyTVCode.__members__
    assert len(members) == len(set(members.values()))


def test_sony_tv_code_get_raw_timings_power() -> None:
    """Test the encoded frame for a Sony television power press."""
    expected_raw_timings = [
        2400, -600, 1200, -600, 600, -600, 1200, -600, 600, -600,
        1200, -600, 600, -600, 600, -600, 1200, -600, 600, -600,
        600, -600, 600, -600, 600, -25800,
    ]  # fmt: skip
    command = SonyTVCode.POWER.to_command()
    assert command.get_raw_timings() == expected_raw_timings
    assert command.modulation == 40000


@pytest.mark.parametrize(
    ("code", "command"),
    [
        pytest.param(SonyTVCode.POWER, 0x15, id="power"),
        pytest.param(SonyTVCode.VOLUME_UP, 0x12, id="volume_up"),
        pytest.param(SonyTVCode.INPUT, 0x25, id="input"),
        pytest.param(SonyTVCode.OK, 0x65, id="ok"),
    ],
)
def test_sony_tv_code_to_command(code: SonyTVCode, command: int) -> None:
    """Each code builds a 12-bit SIRC command on the television address."""
    built = code.to_command()
    assert isinstance(built, SonyCommand)
    assert built.address == SONY_TV_ADDRESS
    assert built.address_bits == SONY_TV_ADDRESS_BITS
    assert built.command == command


def test_sony_tv_digits_are_offset_by_one() -> None:
    """Digit 1 is command 0x00, so the keypad runs one below its face value.

    Zero sits past nine rather than before one, which is easy to get wrong
    when transcribing.
    """
    digits = [
        SonyTVCode.NUM_1,
        SonyTVCode.NUM_2,
        SonyTVCode.NUM_3,
        SonyTVCode.NUM_4,
        SonyTVCode.NUM_5,
        SonyTVCode.NUM_6,
        SonyTVCode.NUM_7,
        SonyTVCode.NUM_8,
        SonyTVCode.NUM_9,
    ]
    assert [code.value for code in digits] == list(range(0x00, 0x09))
    assert SonyTVCode.NUM_0 == 0x09


def test_sony_tv_codes_all_encode_to_a_sirc12_frame() -> None:
    """Every code must produce a full 12-bit frame padded to the SIRC period."""
    for code in SonyTVCode:
        timings = code.to_command().get_raw_timings()
        assert len(timings) == SIRC12_ENTRIES
        assert sum(abs(timing) for timing in timings) == SIRC_FRAME_PERIOD_US
