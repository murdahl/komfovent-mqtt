from collections.abc import Callable
from dataclasses import dataclass

from .registers import REG_OPERATION_MODE, OperationMode

CONTROLLABLE_MODES = (OperationMode.AWAY, OperationMode.NORMAL, OperationMode.INTENSIVE, OperationMode.BOOST)


class CommandError(Exception):
    pass


@dataclass(frozen=True)
class Command:
    register: int
    value: int
    description: str


def _operation_mode(payload: str) -> Command:
    name = payload.strip().lower()
    for mode in CONTROLLABLE_MODES:
        if mode.name.lower() == name:
            return Command(REG_OPERATION_MODE, mode.value, f"operation_mode={name}")

    allowed = ", ".join(mode.name.lower() for mode in CONTROLLABLE_MODES)
    raise CommandError(f"Unsupported operation mode {payload!r}, expected one of: {allowed}")


COMMANDS: dict[str, Callable[[str], Command]] = {
    "operation_mode": _operation_mode,
}


def parse_command(name: str, payload: str) -> Command:
    parser = COMMANDS.get(name)
    if parser is None:
        raise CommandError(f"Unknown command {name!r}, expected one of: {', '.join(COMMANDS)}")
    return parser(payload)
