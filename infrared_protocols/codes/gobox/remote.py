"""Go-Box remote button codes."""

from enum import IntEnum, unique

from ...commands import Command
from ...commands.gobox import GoboxCommand


@unique
class GoboxCode(IntEnum):
    """Go-Box navigation, playback and adjustment buttons."""

    MENU = 0xAA55
    RETURN = 0x22DD
    UP = 0x0AF5
    LEFT = 0x8A75
    RIGHT = 0x48B7
    DOWN = 0xA25D
    OK = 0xC837
    TOGGLE = 0xB847
    PROFILE = 0xFA05
    FASTER = 0xF00F
    SLOWER = 0xD02F
    LOUDER = 0xB04F
    SOFTER = 0xF807

    def to_command(self) -> Command:
        """Build an infrared button command."""
        return GoboxCommand(code=self.value)
