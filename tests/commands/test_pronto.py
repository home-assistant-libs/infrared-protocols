from infrared_protocols.commands.pronto import ProntoCommand

TEST_DATA_KNOWN_GOOD_RAW_TIMINGS = [
    9100, -4446, 598, -494, 598, -494, 598, -494, 598, -1612, 598, -494, 598, -494, 598,
    -1612, 598, -494, 598, -494, 598, -1612, 598, -494, 598, -494, 598, -494, 598, -494,
    598, -494, 598, -1612, 598, -1612, 598, -494, 598, -494, 598, -494, 598, -494, 598,
    -494, 598, -494, 598, -1612, 598, -494, 598, -494, 598, -494, 598, -1612, 598, -494,
    598, -494, 598, -494, 598, -494, 598, -9984
]
TEST_DATA_KNOWN_GOOD_MODULATION = 38000
TEST_DATA_KNOWN_GOOD_REPEATS = 0
TEST_DATA_KNOWN_GOOD_PRONTO = b'\x01Z\x00\xaa\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00?\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00?\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00?\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00?\x00\x16\x00?\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00?\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00?\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x00\x14\x00\x16\x01}'
TEST_DATA_KNOWN_GOOD_PRONTO_REPR = "0000 006d 0022 0000 015a 00aa 0016 0014 0016 0014 0016 0014 0016 003f 0016 0014 0016 0014 0016 003f 0016 0014 0016 0014 0016 003f 0016 0014 0016 0014 0016 0014 0016 0014 0016 0014 0016 003f 0016 003f 0016 0014 0016 0014 0016 0014 0016 0014 0016 0014 0016 0014 0016 003f 0016 0014 0016 0014 0016 0014 0016 003f 0016 0014 0016 0014 0016 0014 0016 0014 0016 017d"

def test_encode_pronto_from_timing():
    pronto = ProntoCommand.from_raw_timings(TEST_DATA_KNOWN_GOOD_RAW_TIMINGS)
    assert pronto.modulation == TEST_DATA_KNOWN_GOOD_MODULATION
    assert pronto.repeat_count == TEST_DATA_KNOWN_GOOD_REPEATS
    assert pronto.timing_data == TEST_DATA_KNOWN_GOOD_PRONTO

def test_decode_pronto_to_timing():
    pronto = ProntoCommand(timing_data=TEST_DATA_KNOWN_GOOD_PRONTO, modulation=TEST_DATA_KNOWN_GOOD_MODULATION, repeat_count=TEST_DATA_KNOWN_GOOD_REPEATS)
    assert pronto.modulation == 38000
    assert pronto.repeat_count == TEST_DATA_KNOWN_GOOD_REPEATS
    assert all(abs(calculated - expected) < 2 * ProntoCommand._time_base(modulation=pronto.modulation) for calculated, expected in zip(pronto.get_raw_timings(), TEST_DATA_KNOWN_GOOD_RAW_TIMINGS, strict=True))

def test_pronto_repr():
    pronto = ProntoCommand.from_raw_timings(TEST_DATA_KNOWN_GOOD_RAW_TIMINGS)
    assert repr(pronto) == TEST_DATA_KNOWN_GOOD_PRONTO_REPR

def test_pronto_repeats():
    # Repeats only work correctly if pronto is constructed using the default constructor, not by using ProntoCommand.from_raw_timings.
    pronto = ProntoCommand(timing_data=TEST_DATA_KNOWN_GOOD_PRONTO, modulation=TEST_DATA_KNOWN_GOOD_MODULATION, repeat_count=2)
    assert pronto.repeat_count == 2
    # 1 base + 2 repeats
    assert len(pronto.get_raw_timings()) == (1 + 2) * len(TEST_DATA_KNOWN_GOOD_RAW_TIMINGS)
    assert all(abs(calculated - expected) < 2 * ProntoCommand._time_base(modulation=pronto.modulation) for calculated, expected in zip(pronto.get_raw_timings(), TEST_DATA_KNOWN_GOOD_RAW_TIMINGS * (1 + 2), strict=True))
