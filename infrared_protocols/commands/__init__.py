"""IR command encoders. Import directly from each protocol submodule."""

import abc


class Command(abc.ABC):
    """Base class for IR commands."""

    repeat_count: int
    modulation: int

    def __init__(self, *, modulation: int, repeat_count: int = 0) -> None:
        """Initialize the IR command."""
        self.modulation = modulation
        self.repeat_count = repeat_count

    @abc.abstractmethod
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the command.

        Positive values are pulse (high) durations in microseconds; negative
        values are space (low) durations in microseconds.
        """
