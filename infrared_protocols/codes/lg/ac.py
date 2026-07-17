"""Fixed-code button codes for LG air conditioners.

Each value is the 16-bit body of an LG2 frame the remote emits verbatim, unlike the
state frames built by ``LgAcCommand``. The fixed 0x88 signature and the checksum nibble
are the same for every frame, so they are not stored here; ``LgAcFixedCommand`` adds
them. A full frame is ``0x88`` + the 16-bit value + a checksum nibble, e.g. the display
toggle ``0xC00A`` is transmitted as ``0x88C00A6``.
"""

from enum import IntEnum

from ...commands import Command
from ...commands.lg_ac import LgAcFixedCommand


class LgAcButton(IntEnum):
    """LG AC fixed-code button; value is the 16-bit frame body."""

    SWING_V_TOGGLE = 0x1000
    """only flips between auto-swing and off; prefer SWING_V_SWING and SWING_V_OFF"""
    JET = 0x100D
    """Turbo mode; may be called VIRAAT or Power Cool on some remotes."""
    DIET = 0x101F
    """Reduces the unit's power draw"""

    SWING_V_LOWEST = 0x1304
    SWING_V_LOW = 0x1305
    SWING_V_MIDDLE_LOW = 0x1306
    SWING_V_MIDDLE_HIGH = 0x1307
    SWING_V_HIGH = 0x1308
    SWING_V_HIGHEST = 0x1309
    SWING_H_LEFT = 0x130B
    SWING_H_MIDDLE_LEFT = 0x130C
    SWING_H_MIDDLE = 0x130D
    SWING_H_MIDDLE_RIGHT = 0x130E
    SWING_H_RIGHT = 0x130F
    # Sweeps between the middle and one side, rather than resting at a position.
    SWING_H_MIDDLE_TO_LEFT = 0x1310
    SWING_H_MIDDLE_TO_RIGHT = 0x1311
    # The swing (oscillate) and auto positions share one frame on this protocol.
    SWING_V_SWING = 0x1314
    SWING_V_OFF = 0x1315
    SWING_H_SWING = 0x1316
    SWING_H_OFF = 0x1317

    AI_CONVERTIBLE = 0x1408

    ION_GENERATOR_ON = 0xC000
    ION_GENERATOR_OFF = 0xC008
    LIGHT_TOGGLE = 0xC00A
    AUTO_CLEAN_ON = 0xC00B
    AUTO_CLEAN_OFF = 0xC00C
    WIFI_TOGGLE = 0xC029
    AUDIO_TOGGLE = 0xC075
    # Caps the unit's power draw.
    ENERGY_LIMIT_80 = 0xC07D
    ENERGY_LIMIT_60 = 0xC07E
    ENERGY_LIMIT_OFF = 0xC07F
    ENERGY_LIMIT_40 = 0xC080
    DIAGNOSE = 0xC0CE

    def to_command(self) -> Command:
        """Build an LG AC fixed-code command for this button."""
        return LgAcFixedCommand(command=self.value)
