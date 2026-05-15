"""Tests for the Sharp IR command."""

import pytest

from infrared_protocols.commands.sharp import SharpCommand

_BIT_ZERO = [320, -680]
_BIT_ONE = [320, -1680]


class TestSharpCommandEncoding:
    """Test SharpCommand.get_raw_timings()."""

    def test_aquos_button_1(self) -> None:
        """AQUOS TV button '1': address=1, command=1, extension=1."""
        cmd = SharpCommand(address=1, command=1, extension=1)
        assert cmd.get_raw_timings() == [
            # region Address (5 bits, LSB first: 1,0,0,0,0)
            *_BIT_ONE,
            *_BIT_ZERO,
            *_BIT_ZERO,
            *_BIT_ZERO,
            *_BIT_ZERO,
            # endregion Address (5 bits, LSB first: 1,0,0,0,0)
            # region Command (8 bits, LSB first: 1,0,0,0,0,0,0,0)
            *_BIT_ONE,
            *_BIT_ZERO,
            *_BIT_ZERO,
            *_BIT_ZERO,
            *_BIT_ZERO,
            *_BIT_ZERO,
            *_BIT_ZERO,
            *_BIT_ZERO,
            # endregion Command (8 bits, LSB first: 1,0,0,0,0,0,0,0)
            # region Extension and Check (2 bits, LSB first: 1,0)
            *_BIT_ONE,
            *_BIT_ZERO,
            # endregion Extension and Check (2 bits, LSB first: 1,0)
            320, -40000,  # Trailer
            # region Address (5 bits, LSB first: 1,0,0,0,0)
            *_BIT_ONE,
            *_BIT_ZERO,
            *_BIT_ZERO,
            *_BIT_ZERO,
            *_BIT_ZERO,
            # endregion Address (5 bits, LSB first: 1,0,0,0,0)
            # region Command inverted (8 bits, LSB first: 0,1,1,1,1,1,1,1)
            *_BIT_ZERO,
            *_BIT_ONE,
            *_BIT_ONE,
            *_BIT_ONE,
            *_BIT_ONE,
            *_BIT_ONE,
            *_BIT_ONE,
            *_BIT_ONE,
            # endregion Command inverted (8 bits, LSB first: 0,1,1,1,1,1,1,1)
            # region Extension and Check inverted (2 bits, LSB first: 0,1)
            *_BIT_ZERO,
            *_BIT_ONE,
            # endregion Extension and Check inverted (2 bits, LSB first: 0,1)
            320, -40000,  # Trailer
        ]

    def test_aquos_power_button(self) -> None:
        """AQUOS TV power button: address=1, command=22, extension=1."""
        cmd = SharpCommand(address=1, command=22, extension=1)
        assert cmd.get_raw_timings() == [
            # region Address (5 bits, LSB first: 1,0,0,0,0)
            *_BIT_ONE,
            *_BIT_ZERO,
            *_BIT_ZERO,
            *_BIT_ZERO,
            *_BIT_ZERO,
            # endregion Address (5 bits, LSB first: 1,0,0,0,0)
            # region Command (8 bits, LSB first: 0,1,1,0,1,0,0,0)
            *_BIT_ZERO,
            *_BIT_ONE,
            *_BIT_ONE,
            *_BIT_ZERO,
            *_BIT_ONE,
            *_BIT_ZERO,
            *_BIT_ZERO,
            *_BIT_ZERO,
            # endregion Command (8 bits, LSB first: 0,1,1,0,1,0,0,0)
            # region Extension and Check (2 bits, LSB first: 1,0)
            *_BIT_ONE,
            *_BIT_ZERO,
            # endregion Extension and Check (2 bits, LSB first: 1,0)
            320, -40000,  # Trailer
            # region Address (5 bits, LSB first: 1,0,0,0,0)
            *_BIT_ONE,
            *_BIT_ZERO,
            *_BIT_ZERO,
            *_BIT_ZERO,
            *_BIT_ZERO,
            # endregion Address (5 bits, LSB first: 1,0,0,0,0)
            # region Command inverted (8 bits, LSB first: 1,0,0,1,0,1,1,1)
            *_BIT_ONE,
            *_BIT_ZERO,
            *_BIT_ZERO,
            *_BIT_ONE,
            *_BIT_ZERO,
            *_BIT_ONE,
            *_BIT_ONE,
            *_BIT_ONE,
            # endregion Command inverted (8 bits, LSB first: 1,0,0,1,0,1,1,1)
            # region Extension and Check inverted (2 bits, LSB first: 0,1)
            *_BIT_ZERO,
            *_BIT_ONE,
            # endregion Extension and Check inverted (2 bits, LSB first: 0,1)
            320, -40000,  # Trailer
        ]

    def test_frame_length(self) -> None:
        """Total timings: 2 frames × (15 bits × 2 + trailer × 2) = 64 values."""
        cmd = SharpCommand(address=1, command=1, extension=1)
        assert len(cmd.get_raw_timings()) == 64

    def test_address_preserved_in_inverted_frame(self) -> None:
        """Address bits must be identical in data and inverted data frames."""
        cmd = SharpCommand(address=0x15, command=0)
        timings = cmd.get_raw_timings()
        # First frame: indices 0-29 (bits) + 30,31 (trailer)
        data_bits = timings[:30]
        # Second frame: indices 32-61 (bits) + 62,63 (trailer)
        idata_bits = timings[32:62]
        # First 5 bits (10 values) represent the address and must match
        assert data_bits[:10] == idata_bits[:10]

    def test_non_address_bits_inverted_in_inverted_frame(self) -> None:
        """Command, extension, and check bits must be inverted in the second frame."""
        cmd = SharpCommand(address=0x00, command=0xB4, extension=1)
        timings = cmd.get_raw_timings()
        # Bits 5-14 (command + extension + check): space values at odd indices
        # within each frame. Space -680 = '0', -1680 = '1'.
        data_spaces = [timings[n * 2 + 1] for n in range(5, 15)]
        idata_spaces = [timings[32 + n * 2 + 1] for n in range(5, 15)]
        invert = {-680: -1680, -1680: -680}
        assert idata_spaces == [invert[s] for s in data_spaces]

    def test_trailer_values(self) -> None:
        """Both trailer pulses must be 320µs high, 40000µs low."""
        cmd = SharpCommand(address=1, command=1, extension=1)
        timings = cmd.get_raw_timings()
        # Trailer after data frame
        assert timings[30] == 320
        assert timings[31] == -40000
        # Trailer after inverted data frame
        assert timings[62] == 320
        assert timings[63] == -40000


@pytest.mark.parametrize(
    ("address", "command", "extension"),
    [
        (-1, 0x00, 0),
        (0x20, 0x00, 0),
        (0x00, -1, 0),
        (0x00, 0x100, 0),
        (0x00, 0x00, -1),
        (0x00, 0x00, 2),
    ],
)
def test_sharp_rejects_out_of_range(
    address: int, command: int, extension: int
) -> None:
    """5-bit address, 8-bit command, 1-bit extension — anything else is invalid."""
    with pytest.raises(ValueError):
        SharpCommand(address=address, command=command, extension=extension)
