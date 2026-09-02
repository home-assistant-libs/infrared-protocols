"""Commands for Dyson infrared protocol."""

from typing import ClassVar, override

from . import Command


class _DysonFanCommand(Command):
    """Dyson fan infrared command.

    Protocol specification:
      - Header: 2440us mark, 870us space
      - Bit mark: 850us (constant)
      - Bit space: 850us = "0", 1660us = "1"
      - 15-bit payload, MSB-first: 7-bit preamble (bits 14-8) + 8-bit command
        code (bits 7-0)
      - Footer: 850us mark
    """

    _PREAMBLE: ClassVar[int]

    code: int

    def __init__(
        self,
        *,
        code: int,
        modulation: int = 38000,
    ) -> None:
        """Initialize a Dyson fan command.

        Args:
            code: 8-bit command code. The fixed preamble for the device is
                prepended by the command class.
            modulation: Carrier frequency in Hz.

        """
        super().__init__(modulation=modulation)
        if code < 0 or code > 0xFF:
            raise ValueError("Dyson command code must be a valid 8-bit integer")
        self.code = code

    @override
    def get_raw_timings(self) -> list[int]:
        header_mark = 2440
        header_space = 870
        bit_mark = 850
        zero_space = 850
        one_space = 1660
        footer_mark = 850

        payload = (self._PREAMBLE << 8) | self.code

        timings: list[int] = [header_mark, -header_space]

        # 15 bits, MSB-first
        for i in range(14, -1, -1):
            bit = (payload >> i) & 1
            timings.append(bit_mark)
            timings.append(-(one_space if bit else zero_space))

        timings.append(footer_mark)

        return timings


class DysonCoolCommand(_DysonFanCommand):
    """Dyson Cool infrared command."""

    _PREAMBLE = 0b1001000


class DysonAm09Command(_DysonFanCommand):
    """Dyson AM09 (Hot+Cool) infrared command."""

    _PREAMBLE = 0b0011000
