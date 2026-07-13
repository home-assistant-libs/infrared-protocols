"""Commands for Dyson infrared protocol.
"""

from typing import override

from . import Command


class DysonCoolCommand(Command):
    """Dyson Cool infrared command.

    Real protocol (reverse-engineered from Broadlink learn_command captures):
      - Header: 2440us mark, 870us space
      - Bit mark: 850us (constant)
      - Bit space: 850us = "0", 1660us = "1"
      - 15-bit payload, MSB-first: 1001000 (7-bit preamble) + 8-bit command
      - Footer: 850us mark
      - "hold" commands (temp/time/swing) repeat the whole frame twice,
        with a ~108ms gap between repeats
    """

    payload: int

    def __init__(
        self,
        *,
        payload: int,
        modulation: int = 38000,
        repeat_count: int = 1,
    ) -> None:
        """Initialize a Dyson Cool command.

        Args:
            payload: 15-bit payload value.
            modulation: Carrier frequency in Hz.
            repeat_count: Number of times the command is repeated.

        """
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        if payload < 0 or payload > 0x7FFF:
            raise ValueError("Dyson payload must be a valid 15-bit integer")
        self.payload = payload

    @override
    def get_raw_timings(self) -> list[int]:
        header_mark = 2440
        header_space = 870
        bit_mark = 850
        zero_space = 850
        one_space = 1660
        footer_mark = 850
        repeat_gap = 108000

        timings: list[int] = []

        for packet_idx in range(self.repeat_count + 1):
            timings.append(header_mark)
            timings.append(header_space)

            # 15 bits, MSB-first
            for i in range(14, -1, -1):
                bit = (self.payload >> i) & 1
                timings.append(bit_mark)
                timings.append(one_space if bit else zero_space)

            timings.append(footer_mark)

            if packet_idx < self.repeat_count:
                timings.append(repeat_gap)

        return timings
