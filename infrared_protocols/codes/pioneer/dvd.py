"""Command codes for Pioneer DVD players.

Codes are taken from the Pioneer VXX2914 remote. Power, the menu keys and
audio are corroborated by other Pioneer remotes (CU-DV027, XXD3089), which
suggests the set is shared across Pioneer DVD devices rather than specific to
one player.
"""

from enum import Enum

from ...commands import Command
from ...commands.pioneer import PioneerCommand

PIONEER_DVD_ADDRESS = 0xA3
PIONEER_DVD_EXTENDED_ADDRESS = 0xAF
# Sent as the preamble of a two-part command to reach the extended set. It is
# itself a command in the 0xA3 set, alongside the transport keys.
PIONEER_DVD_EXTENDED_SELECTOR = 0x99

# Preamble and address shared by every extended code. Kept out of the enum
# body, where a leading underscore is not enough to stop it becoming a member.
_EXTENDED = (
    PIONEER_DVD_ADDRESS,
    PIONEER_DVD_EXTENDED_SELECTOR,
    PIONEER_DVD_EXTENDED_ADDRESS,
)


class PioneerDVDCode(Enum):
    """IR command code for a Pioneer DVD player.

    The tuple value is one of:

    - ``(address, command)`` — a single Pioneer frame.
    - ``(preamble_address, preamble_command, address, command)`` — a two-part
      command, whose preamble selects the extended command set.
    """

    STOP = (PIONEER_DVD_ADDRESS, 0x98)
    NEXT = (PIONEER_DVD_ADDRESS, 0x9C)
    PREVIOUS = (PIONEER_DVD_ADDRESS, 0x9D)
    PLAY = (PIONEER_DVD_ADDRESS, 0x9E)
    PAUSE = (PIONEER_DVD_ADDRESS, 0x9F)

    POWER = (*_EXTENDED, 0xBC)
    OPEN_CLOSE = (*_EXTENDED, 0xB6)

    NUM_0 = (*_EXTENDED, 0xA0)
    NUM_1 = (*_EXTENDED, 0xA1)
    NUM_2 = (*_EXTENDED, 0xA2)
    NUM_3 = (*_EXTENDED, 0xA3)
    NUM_4 = (*_EXTENDED, 0xA4)
    NUM_5 = (*_EXTENDED, 0xA5)
    NUM_6 = (*_EXTENDED, 0xA6)
    NUM_7 = (*_EXTENDED, 0xA7)
    NUM_8 = (*_EXTENDED, 0xA8)
    NUM_9 = (*_EXTENDED, 0xA9)

    NAV_UP = (*_EXTENDED, 0xF2)
    NAV_DOWN = (*_EXTENDED, 0xF3)
    NAV_LEFT = (*_EXTENDED, 0x63)
    NAV_RIGHT = (*_EXTENDED, 0x64)
    ENTER = (*_EXTENDED, 0xEF)
    RETURN = (*_EXTENDED, 0xF4)
    MENU = (*_EXTENDED, 0xB9)
    TOP_MENU = (*_EXTENDED, 0xB4)
    HOME_MENU = (*_EXTENDED, 0xB0)

    FORWARD = (*_EXTENDED, 0xE9)
    REWIND = (*_EXTENDED, 0xEA)
    PLAY_MODE = (*_EXTENDED, 0x7F)

    AUDIO = (*_EXTENDED, 0xBE)
    SUBTITLE = (*_EXTENDED, 0x36)
    ANGLE = (*_EXTENDED, 0xB5)
    SURROUND = (*_EXTENDED, 0x61)
    ZOOM = (*_EXTENDED, 0x37)
    DISPLAY = (*_EXTENDED, 0xE3)
    CLEAR = (*_EXTENDED, 0xE5)

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build the IR command for this Pioneer DVD code."""
        if len(self.value) == 4:
            preamble_address, preamble_command, address, command = self.value
            return PioneerCommand(
                address=address,
                command=command,
                preamble_address=preamble_address,
                preamble_command=preamble_command,
                repeat_count=repeat_count,
            )

        address, command = self.value
        return PioneerCommand(
            address=address,
            command=command,
            repeat_count=repeat_count,
        )
