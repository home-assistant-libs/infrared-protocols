"""Haier 72-bit and 112-bit infrared packet transport."""

from ._packet import PacketCommand
from ._timing import PulseTiming


class HaierCommand(PacketCommand):
    """Eight or thirteen payload bytes followed by an additive checksum."""

    HEADER = (3100, -3100, 3100, -4400)
    TIMING = PulseTiming(540, 580, 1650)
    LENGTHS = (8, 13)
    LSB = False
