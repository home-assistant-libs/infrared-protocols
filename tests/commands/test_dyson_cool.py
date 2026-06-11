"""Tests for the Dyson Cool infrared protocol encoder."""

import unittest
from infrared_protocols.commands.dyson import DysonCoolCommand
# Nota: Assicurati che l'import del Builder sia corretto in base alla tua struttura
from infrared_protocols.codes.dyson.cool import DysonCoolStateBuilder 


def test_dyson_cool_payload_validation() -> None:
    """Test that DysonCoolCommand enforces strict 16-bit boundaries."""
    test_case = unittest.TestCase()
    # Modificato l'errore atteso per riflettere i 16-bit
    with test_case.assertRaisesRegex(ValueError, "Dyson payload must be a valid 16-bit integer"):
        DysonCoolCommand(payload=0x10000)  # Fuori scala (> 0xFFFF)


def test_dyson_cool_command_get_raw_timings() -> None:
    """Test that Dyson logical actions compile to exact structural timings."""
    # L'azione "off" mappa il payload 0x4001 -> In binario LSB il bit 0 è 1
    builder = DysonCoolStateBuilder(action="off")
    command = builder.to_command()
    timings = command.get_raw_timings()

    # Verifica la struttura del Leader Pulse (Standard NEC)
    assert timings[0] == 8940
    assert timings[1] == 4440

    # Primo bit di dati (Bit 0 del payload 0x4001 è 1 -> deve essere HIGH + ONE_LOW)
    assert timings[2] == 590   # bit_high
    assert timings[3] == 1630  # one_low (era 520 quando era MSB)


def test_dyson_cool_extended_actions() -> None:
    """Test that specialized speeds and timer increments compile safely."""
    test_cases = ["speed_5", "speed_10", "time_up", "time_down", "swing"]

    for action in test_cases:
        builder = DysonCoolStateBuilder(action=action)
        command = builder.to_command()
        timings = command.get_raw_timings()

        assert len(timings) > 0
        assert timings[0] == 8940  # Modificato da 1480 a 8940 per il nuovo leader pulse