"""Dyson cool mode command mapping.

Provides a small builder to convert high-level actions into
DysonCoolCommand instances containing the appropriate payload.

Payloads are 15-bit values: 7-bit preamble (0b1001000) + 8-bit command code,
reverse-engineered from real Broadlink learn_command captures.
"""

from dataclasses import dataclass
from typing import Literal

from ...commands import Command
from ...commands.dyson import DysonCoolCommand


@dataclass(frozen=True)
class DysonCoolStateBuilder:
    """Builder for converting high-level Dyson cool mode actions to commands.

    Attributes:
        action: The action to perform, one of: on, cool_on, off, swing,
                speed_up, speed_down, time_up, time_down.

    """

    action: Literal[
        "on",
        "cool_on",
        "off",
        "swing",
        "speed_up",
        "speed_down",
        "time_up",
        "time_down",
    ]

    def to_command(self) -> Command:
        """Convert the builder state into a DysonCoolCommand.

        Returns:
            Command: A DysonCoolCommand instance containing the payload
            corresponding to the builder's action.

        """
        # 15-bit values: preamble 1001000 + 8-bit command byte
        action_mapping = {
            "on": 0x4800,  # cmd 0x00
            "cool_on": 0x4801,  # cmd 0x01
            "off": 0x4802,  # cmd 0x02 (cool_off)
            "swing": 0x48A9,  # cmd 0xA9
            "speed_up": 0x4854,  # cmd 0x54 (temp_up)
            "speed_down": 0x48FD,  # cmd 0xFD (temp_down)
            "time_up": 0x487A,  # cmd 0x7A
            "time_down": 0x48CC,  # cmd 0xCC
        }

        # repeat_count = 1 for single-frame commands (on/cool_on/off),
        # repeat_count = 2 for "hold" commands (sent twice in captures)
        repeat_mapping = {
            "on": 1,
            "cool_on": 1,
            "off": 1,
            "swing": 2,
            "speed_up": 2,
            "speed_down": 2,
            "time_up": 2,
            "time_down": 2,
        }

        payload = action_mapping[self.action]
        repeat_count = repeat_mapping[self.action]
        return DysonCoolCommand(payload=payload, repeat_count=repeat_count)
