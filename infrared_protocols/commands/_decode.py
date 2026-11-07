"""Internal helpers for repeated and Manchester-encoded captures."""

from statistics import median

from ._timing import close


def validate_pulse_prefix(
    actual: list[int], expected: list[int], *, tolerance: float = 0.25
) -> None:
    """Require every available duration of a clipped pulse-distance repeat to match."""
    for index, (duration, reference) in enumerate(zip(actual, expected, strict=False)):
        window = 350 if index > 1 and index % 2 else 225
        if not close(duration, reference, tolerance, absolute=window):
            raise ValueError("clipped repeat differs from the expected frame")


def frames(
    timings: list[int],
    *,
    min_gap: int = 10000,
    period: int | None = None,
    tolerance: float = 0.25,
) -> list[list[int]]:
    """Split at long idle spaces, checking full-frame repeat periods when given."""
    result: list[list[int]] = []
    current: list[int] = []
    for i, duration in enumerate(timings):
        if duration <= -min_gap or (i == len(timings) - 1 and duration <= -3000):
            if not current:
                raise ValueError("empty frame")
            if (
                period is not None
                and i < len(timings) - 1
                and not close(
                    sum(abs(t) for t in current) - duration, period, tolerance
                )
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


def levels(timings: list[int], unit: float, *, maximum: int = 3) -> list[int]:
    """Expand mark/space runs, rejecting zero, oversized or off-grid durations."""
    short = [
        (abs(mark) + abs(space)) / (round(abs(mark) / unit) + round(abs(space) / unit))
        for mark, space in zip(timings, timings[1:], strict=False)
        if mark * space < 0
        and all(0.5 * unit < abs(t) <= 2.5 * unit for t in (mark, space))
    ]
    measured_unit = median(short) if short else unit
    if not close(round(measured_unit), unit, 0.3):
        raise ValueError("invalid Manchester clock")
    unit = measured_unit
    result: list[int] = []
    for duration in timings:
        count = round(abs(duration) / unit)
        if not 1 <= count <= maximum or not close(
            abs(duration), count * unit, 0, absolute=unit * 0.4
        ):
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
