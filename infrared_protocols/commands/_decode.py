"""Internal helpers for repeated and Manchester-encoded captures."""

from ._timing import close


def frames(
    timings: list[int], *, min_gap: int = 10000, period: int | None = None
) -> list[list[int]]:
    """Split at long idle spaces, checking full-frame repeat periods when given."""
    result: list[list[int]] = []
    current: list[int] = []
    for i, duration in enumerate(timings):
        if duration <= -min_gap:
            if not current:
                raise ValueError("empty frame")
            if (
                period is not None
                and i < len(timings) - 1
                and not close(sum(abs(t) for t in current) - duration, period)
            ):
                raise ValueError("incorrect repeat period")
            result.append(current)
            current = []
        else:
            current.append(duration)
    if current:
        result.append(current)
    if not result:
        raise ValueError("empty capture")
    return result


def levels(timings: list[int], unit: int, *, maximum: int = 3) -> list[int]:
    """Expand mark/space runs, rejecting zero, oversized or off-grid durations."""
    result: list[int] = []
    for duration in timings:
        count = round(abs(duration) / unit)
        if not 1 <= count <= maximum or not close(abs(duration), count * unit, 0.2):
            raise ValueError("invalid Manchester run")
        result.extend([int(duration > 0)] * count)
    return result


def manchester(values: list[int], *, one_starts_high: bool = False) -> list[int]:
    """Decode complete Manchester bit cells."""
    if len(values) % 2:
        raise ValueError("incomplete Manchester cell")
    result: list[int] = []
    for i in range(0, len(values), 2):
        if values[i] == values[i + 1]:
            raise ValueError("missing Manchester transition")
        result.append(values[i] if one_starts_high else values[i + 1])
    return result


def rc5_bits(timings: list[int], *, extended: bool = False) -> list[int]:
    """Recover the idle leading half-bit and optional final space of RC-5."""
    values = levels(timings, 889, maximum=6 if extended else 2)
    if timings[0] > 0:
        values.insert(0, 0)
    count = 44 if extended else 28
    if len(values) == count - 1:
        values.append(0)
    if len(values) != count:
        raise ValueError("invalid RC-5 frame length")
    if extended:
        if values[16:20] != [0, 0, 0, 0]:
            raise ValueError("missing RC5X pause")
        values = values[:16] + values[20:]
    result = manchester(values)
    if result[0] != 1:
        raise ValueError("invalid RC-5 start")
    return result
