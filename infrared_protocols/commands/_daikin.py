"""Private section checksums for Daikin variants."""


def checked(packet: bytes) -> bytes:
    """Append the additive checksum to a Daikin section."""
    return packet + bytes([sum(packet) & 255])


def validate_sections(
    data: bytes, lengths: tuple[int, ...], signature: bytes = b"\x11\xda\x27\x00"
) -> None:
    """Validate each independent section's identity and checksum."""
    if len(data) != sum(lengths):
        raise ValueError("invalid Daikin packet length")
    offset = 0
    for length in lengths:
        section = data[offset : offset + length]
        if not section.startswith(signature) or sum(section[:-1]) & 255 != section[-1]:
            raise ValueError("invalid Daikin section signature or checksum")
        offset += length
