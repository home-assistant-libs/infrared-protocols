"""Dyson infrared protocol structural command."""

from typing import override

from . import Command


class DysonCoolCommand(Command):
    """Dyson Cool IR command encoder supporting the 16-bit NEC-like protocol.

    Timings layout (in microseconds):
    - Leader pulse: 8940µs high, 4440µs low
    - Logical '0': 590µs high, 520µs low
    - Logical '1': 590µs high, 1630µs low
    - End pulse: 590µs high
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
        if payload < 0 or payload > 0xFFFF:
            raise ValueError("Dyson payload must be a valid 16-bit integer")
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
            timings.append(leader_high)
            timings.append(leader_low)
            
            data = self.payload
            for i in range(16):
                bit = (data >> i) & 1
                timings.append(bit_high)
                timings.append(one_low if bit else zero_low)
                    
            timings.append(bit_high)
            
            if packet_idx < self.repeat_count:
                timings.append(gap_low)
            
        return timings