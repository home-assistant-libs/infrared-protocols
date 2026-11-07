"""Internal climate field validation and wire lookups."""


def temperature_value(
    value: float | None, minimum: float, maximum: float, step: float = 1
) -> int:
    """Validate a temperature and return its offset in steps."""
    if value is None:
        raise ValueError("temperature is required for this mode")
    if not minimum <= value <= maximum or (value - minimum) % step:
        raise ValueError(f"temperature must be {minimum}..{maximum} in steps of {step}")
    return round((value - minimum) / step)


def selection[T](value: T, choices: dict[T, int]) -> int:
    """Look up a supported setting with a descriptive public error."""
    try:
        return choices[value]
    except KeyError:
        raise ValueError(f"unsupported setting: {value}") from None


def decoded[T](value: int, choices: dict[T, int]) -> T:
    """Look up a wire value, rejecting unknown encodings."""
    for key, candidate in choices.items():
        if candidate == value:
            return key
    raise ValueError(f"unknown wire value: {value}")
