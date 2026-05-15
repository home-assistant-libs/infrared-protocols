"""Command codes for Sharp AQUOS TVs."""

from enum import Enum

from ...commands import Command
from ...commands.sharp import SharpCommand


class SharpAquosTVCode(Enum):
    """Sharp AQUOS TV IR command codes.

    Values are tuples of (address, command, extension) for SharpCommand.
    """

    POWER_TOGGLE = (1, 22, 1)
    POWER_ON = (17, 74, 1)
    POWER_OFF = (17, 75, 1)
    NUM_1 = (1, 1, 1)
    NUM_2 = (1, 2, 1)
    NUM_3 = (1, 3, 1)
    NUM_4 = (1, 4, 1)
    NUM_5 = (1, 5, 1)
    NUM_6 = (1, 6, 1)
    NUM_7 = (1, 7, 1)
    NUM_8 = (1, 8, 1)
    NUM_9 = (1, 9, 1)
    NUM_10 = (1, 10, 1)
    NUM_11 = (1, 11, 1)
    NUM_12 = (1, 12, 1)
    CHANNEL_UP = (1, 17, 1)
    CHANNEL_DOWN = (1, 18, 1)
    SOURCE = (1, 19, 1)
    VOLUME_UP = (1, 20, 1)
    VOLUME_DOWN = (1, 21, 1)
    MUTE = (1, 23, 1)
    SLEEP = (1, 26, 1)
    INFO = (1, 27, 1)
    NAV_UP = (1, 87, 1)
    NAV_DOWN = (1, 32, 1)
    NAV_LEFT = (1, 215, 1)
    NAV_RIGHT = (1, 216, 1)
    OK = (1, 82, 1)
    BACK = (1, 228, 1)
    MENU = (1, 196, 1)

    def to_command(self) -> Command:
        """Convert the code to a SharpCommand."""
        address, command, extension = self.value
        return SharpCommand(address=address, command=command, extension=extension)
