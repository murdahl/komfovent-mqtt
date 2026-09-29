from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import IntEnum

# The controller reports a missing sensor as 0x8000
NO_SENSOR = 0x8000

REG_OPERATION_MODE = 5


class OperationMode(IntEnum):
    STANDBY = 0
    AWAY = 1
    NORMAL = 2
    INTENSIVE = 3
    BOOST = 4
    KITCHEN = 5
    FIREPLACE = 6
    OVERRIDE = 7
    HOLIDAY = 8
    AIR_QUALITY = 9


def _mode_name(value: float) -> str | None:
    try:
        return OperationMode(int(value)).name.lower()
    except ValueError:
        return None


def _humidity(value: float) -> float | None:
    return value if 0 <= value <= 100 else None


@dataclass(frozen=True)
class Field:
    name: str
    register: int  # 1-based, as in the Komfovent Modbus documentation
    scale: float = 1
    signed: bool = False
    words: int = 1
    convert: Callable[[float], object] | None = None

    def decode(self, raw: Mapping[int, int]) -> object:
        value = raw[self.register]
        if self.words == 2:
            value = (value << 16) + raw[self.register + 1]
        elif self.signed:
            if value == NO_SENSOR:
                return None
            value -= (value >> 15) << 16

        scaled = round(value * self.scale, 3) if self.scale != 1 else value
        return self.convert(scaled) if self.convert else scaled


FIELDS = (
    Field("power", 1, convert=bool),
    Field("eco_mode", 3, convert=bool),
    Field("auto_mode", 4, convert=bool),
    Field("operation_mode", REG_OPERATION_MODE, convert=_mode_name),
    Field("supply_temperature", 902, scale=0.1, signed=True),
    Field("extract_temperature", 903, scale=0.1, signed=True),
    Field("outdoor_temperature", 904, scale=0.1, signed=True),
    Field("supply_fan", 910, scale=0.1),
    Field("extract_fan", 911, scale=0.1),
    Field("heat_exchanger", 912, scale=0.1),
    Field("electric_heater", 913, scale=0.1),
    Field("filter_clogging", 917),
    Field("power_consumption", 921),
    Field("heater_power", 922),
    Field("heat_recovery", 923),
    Field("heat_exchanger_efficiency", 924),
    Field("specific_power_input", 926, scale=0.001),
    Field("energy_consumed_day", 927, scale=0.001, words=2),
    Field("energy_consumed_month", 929, scale=0.001, words=2),
    Field("energy_consumed_total", 931, scale=0.001, words=2),
    Field("energy_recovered_day", 939, scale=0.001, words=2),
    Field("energy_recovered_month", 941, scale=0.001, words=2),
    Field("energy_recovered_total", 943, scale=0.001, words=2),
    Field("panel_temperature", 946, scale=0.1, signed=True),
    Field("panel_humidity", 947, convert=_humidity),
    Field("indoor_absolute_humidity", 956, scale=0.01),
)

# Contiguous (start, count) reads covering every field above
BLOCKS = ((1, 5), (900, 45), (946, 11))


def decode(raw: Mapping[int, int]) -> dict[str, object]:
    return {field.name: field.decode(raw) for field in FIELDS}
