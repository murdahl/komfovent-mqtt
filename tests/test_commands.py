import pytest

from komfovent_mqtt.commands import Command, CommandError, parse_command


@pytest.mark.parametrize(
    ("payload", "value"),
    [("away", 1), ("normal", 2), ("intensive", 3), ("boost", 4), (" Intensive\n", 3)],
)
def test_operation_mode(payload, value):
    assert parse_command("operation_mode", payload) == Command(5, value, f"operation_mode={payload.strip().lower()}")


@pytest.mark.parametrize("payload", ["kitchen", "standby", "3", ""])
def test_rejects_unsupported_operation_mode(payload):
    with pytest.raises(CommandError, match="expected one of: away, normal, intensive, boost"):
        parse_command("operation_mode", payload)


def test_rejects_unknown_command():
    with pytest.raises(CommandError, match="Unknown command 'power'"):
        parse_command("power", "on")
