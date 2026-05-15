"""Sharp IR command."""

from typing import override

from . import Command

_BIT_HIGH = 320
_ZERO_LOW = 1000 - 320  # 680
_ONE_LOW = 2000 - 320  # 1680
_TRAILER_LOW = 40000


class SharpCommand(Command):
    """Sharp IR command."""

    address: int
    command: int
    extension: int

    def __init__(
        self,
        *,
        address: int,
        command: int,
        extension: int = 0,
        modulation: int = 38000,
    ) -> None:
        """Initialize the Sharp IR command.

        :param address: The IR address for the Sharp command. (5 bits)
        :param command: The IR command for the Sharp command. (8 bits)
        :param extension: The extension bit for the Sharp command. (1 bit)
        """
        if not 0 <= address <= 0x1F:
            raise ValueError(f"address must be in range 0-31, got {address}")
        if not 0 <= command <= 0xFF:
            raise ValueError(f"command must be in range 0-255, got {command}")
        if extension not in (0, 1):
            raise ValueError(f"extension must be 0 or 1, got {extension}")
        super().__init__(modulation=modulation)
        self.address = address
        self.command = command
        self.extension = extension

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Sharp command.

        The Sharp protocol has no dedicated repeat code; a held button
        retransmits the same full frame repeatedly.

        Sharp protocol timing (in microseconds):
        - No leader pulse
        - Logical '0': 320µs high, 680µs low (1ms total)
        - Logical '1': 320µs high, 1680µs low (2ms total)
        - Trailer pulse: 320µs high, 40ms low (frame gap)

        Frame format:
        - Data frame (15 bits total):
          - 5-bit address (LSB first)
          - 8-bit command (LSB first)
          - 1 extension bit
          - check bit (0)
        - Trailer pulse
        - Inverted data frame (15 bits total):
          - 5-bit address (unchanged)
          - 8-bit command (inverted)
          - 1 extension bit (inverted)
          - check bit (1)
        - Trailer pulse
        """
        # Build 15-bit data word (LSB first):
        # bits 0-4: address, bits 5-12: command, bit 13: extension, bit 14: check (0)
        data = self.address | (self.command << 5) | (self.extension << 13)
        # Invert bits 5-14 for the second frame (address bits 0-4 stay the same)
        idata = data ^ 0x7FE0

        timings: list[int] = []

        def _encode_bits(value: int) -> None:
            for _ in range(15):
                bit = value & 1
                timings.append(_BIT_HIGH)
                timings.append(-(_ONE_LOW if bit else _ZERO_LOW))
                value >>= 1
            timings.extend([_BIT_HIGH, -_TRAILER_LOW])

        _encode_bits(data)
        _encode_bits(idata)

        return timings
