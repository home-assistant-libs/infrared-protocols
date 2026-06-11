"""Dyson infrared protocol structural command."""

from typing import override

from . import Command


class DysonCoolCommand(Command):
    """Dyson Cool IR command encoder supporting the 15-bit protocol.

    Timings layout (in microseconds):
    - Leader pulse: 1480µs high, 520µs low
    - Logical '0': 520µs high, 500µs low
    - Logical '1': 520µs high, 1020µs low
    - End pulse: 520µs high
    - Inter-packet gap: 4000µs low
    """

    payload: int

    def __init__(
        self,
        *,
        payload: int,
        modulation: int = 38000,
        repeat_count: int = 1,
    ) -> None:
        """Initialize the Dyson Cool structural command."""
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        if payload < 0 or payload > 0x7FFF:
            raise ValueError("Dyson payload must be a valid 15-bit integer")
        self.payload = payload

    @override
    def get_raw_timings(self) -> list[int]:
        """Compile the 16-bit payload into raw IR microsecond timings matched to your actual remote."""
        
        leader_high = 8940
        leader_low = 4440
        bit_high = 590
        zero_low = 520
        one_low = 1630
        gap_low = 4000

        timings: list[int] = []
        
        for packet_idx in range(self.repeat_count + 1):
            # Preambolo
            timings.append(leader_high)
            timings.append(leader_low)
            
            data = self.payload
            # CORREZIONE: Range impostato a 16 bit (da 15 a 0) per non tagliare l'MSB del payload
            for i in range(15, -1, -1):
                bit = (data >> i) & 1
                timings.append(bit_high)
                timings.append(one_low if bit else zero_low)
                    
            # Bit di stop finale
            timings.append(bit_high)
            
            if packet_idx < self.repeat_count:
                timings.append(gap_low)
            
        return timings