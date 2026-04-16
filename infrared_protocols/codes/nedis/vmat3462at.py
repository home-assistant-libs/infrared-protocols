"""Command codes for the Nedis VMAT3462AT HDMI switch."""

from enum import IntEnum

from ...commands import Command, NECCommand


class NedisVMAT3462ATCode(IntEnum):
    """Nedis VMAT3462AT HDMI switch IR command codes."""

    POWER = 0x14
    A_OFF = 0xD
    A_1 = 0x19
    A_2 = 0x15
    A_3 = 0x50
    A_4 = 0x4A
    B_OFF = 0x2
    B_1 = 0x18
    B_2 = 0x51
    B_3 = 0x53
    B_4 = 0x45


def make_command(code: NedisVMAT3462ATCode, repeat_count: int = 0) -> Command:
    """Get the NECCommand for a Nedis VMAT3462AT HDMI switch IR code."""
    return NECCommand(address=0x0, command=code, repeat_count=repeat_count)
