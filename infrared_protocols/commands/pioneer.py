"""Pioneer IR command."""

from typing import override

from . import Command
from .nec import NECCommand

# Pioneer carrier frequency in Hz. The frame is NEC-shaped, but Pioneer
# modulates it at 40 kHz rather than NEC's 38 kHz.
PIONEER_MODULATION_HZ = 40000
# Time between the start of one frame and the start of the next. Measured
# across captures of Pioneer remotes, which agree on this for both one-frame
# and two-part commands.
PIONEER_FRAME_PERIOD_US = 90000


class PioneerCommand(Command):
    """Pioneer IR command.

    A Pioneer frame is a standard NEC frame with an 8-bit address, sent at a
    40 kHz carrier on a 90ms frame period.

    Many Pioneer devices reach a second command set through a two-part
    command: a preamble frame that selects the set, followed by the frame
    carrying the button. Pass ``preamble_address`` and ``preamble_command``
    together to emit one. Devices that need no preamble send a single frame.
    """

    address: int
    command: int
    preamble_address: int | None
    preamble_command: int | None

    def __init__(
        self,
        *,
        address: int,
        command: int,
        preamble_address: int | None = None,
        preamble_command: int | None = None,
        modulation: int = PIONEER_MODULATION_HZ,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the Pioneer IR command."""
        if not 0 <= address <= 0xFF:
            raise ValueError("Pioneer address must be in range 0x00..0xFF")
        if not 0 <= command <= 0xFF:
            raise ValueError("Pioneer command must be in range 0x00..0xFF")
        if (preamble_address is None) != (preamble_command is None):
            raise ValueError(
                "preamble_address and preamble_command must be given together"
            )
        if preamble_address is not None and not 0 <= preamble_address <= 0xFF:
            raise ValueError("Pioneer preamble_address must be in range 0x00..0xFF")
        if preamble_command is not None and not 0 <= preamble_command <= 0xFF:
            raise ValueError("Pioneer preamble_command must be in range 0x00..0xFF")

        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.address = address
        self.command = command
        self.preamble_address = preamble_address
        self.preamble_command = preamble_command

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Pioneer command.

        Pioneer protocol timing (in microseconds):
        - Carrier: 40 kHz
        - Frame: a standard NEC frame, 8-bit address and its complement
          followed by the 8-bit command and its complement, LSB first
        - Frame period: 90000µs, so a frame is followed by idle space until
          the next one starts

        A two-part command sends its preamble frame first. Repeats resend the
        whole command, preamble included, which is what Pioneer remotes do
        while a key is held.
        """
        frames = []
        if self.preamble_address is not None and self.preamble_command is not None:
            frames.append(self._frame(self.preamble_address, self.preamble_command))
        frames.append(self._frame(self.address, self.command))

        timings: list[int] = []
        previous_duration = 0
        for frame in frames * (self.repeat_count + 1):
            if timings:
                timings.append(-(PIONEER_FRAME_PERIOD_US - previous_duration))
            timings.extend(frame)
            previous_duration = sum(abs(t) for t in frame)

        return timings

    @staticmethod
    def _frame(address: int, command: int) -> list[int]:
        """Build one Pioneer frame.

        The frame is bit-for-bit an NEC frame; only the carrier and the frame
        period differ, and both are handled by the caller.
        """
        return NECCommand(address=address, command=command).get_raw_timings()
