from komfovent_mqtt.registers import BLOCKS, FIELDS, decode

# Captured from a Komfovent Domekt with a C6 controller, in NORMAL mode
SNAPSHOT = {
    1: [1, 0, 0, 0, 2],
    900: [
        4, 1, 196, 251, 175, 32768, 0, 50, 0, 50, 500, 500, 0, 0, 0, 0, 0, 32, 100, 0, 0, 27, 0, 0,
        0, 0, 168, 0, 445, 0, 14774, 51, 50435, 0, 0, 0, 0, 26, 10838, 0, 3714, 0, 47533, 325, 20278,
    ],
    946: [260, 36, 0, 32768, 156, 0, 32768, 32768, 1, 1, 876],
}


def raw_from(snapshot: dict[int, list[int]]) -> dict[int, int]:
    return {start + offset: value for start, values in snapshot.items() for offset, value in enumerate(values)}


def test_decodes_snapshot():
    state = decode(raw_from(SNAPSHOT))

    assert state == {
        "power": True,
        "eco_mode": False,
        "auto_mode": False,
        "operation_mode": "normal",
        "supply_temperature": 19.6,
        "extract_temperature": 25.1,
        "outdoor_temperature": 17.5,
        "supply_fan": 50.0,
        "extract_fan": 50.0,
        "heat_exchanger": 0,
        "electric_heater": 0,
        "filter_clogging": 32,
        "power_consumption": 27,
        "heater_power": 0,
        "heat_recovery": 0,
        "heat_exchanger_efficiency": 0,
        "specific_power_input": 0.168,
        "energy_consumed_day": 0.445,
        "energy_consumed_month": 14.774,
        "energy_consumed_total": 3392.771,
        "energy_recovered_day": 3.714,
        "energy_recovered_month": 47.533,
        "energy_recovered_total": 21319.478,
        "panel_temperature": 26.0,
        "panel_humidity": 36,
        "indoor_absolute_humidity": 8.76,
    }


def test_negative_temperature():
    raw = raw_from(SNAPSHOT) | {904: 65536 - 125}

    assert decode(raw)["outdoor_temperature"] == -12.5


def test_missing_sensor_is_none():
    raw = raw_from(SNAPSHOT) | {946: 32768}

    assert decode(raw)["panel_temperature"] is None


def test_out_of_range_humidity_is_none():
    raw = raw_from(SNAPSHOT) | {947: 255}

    assert decode(raw)["panel_humidity"] is None


def test_unknown_operation_mode_is_none():
    raw = raw_from(SNAPSHOT) | {5: 42}

    assert decode(raw)["operation_mode"] is None


def test_blocks_cover_every_field():
    covered = {start + offset for start, count in BLOCKS for offset in range(count)}

    for field in FIELDS:
        assert set(range(field.register, field.register + field.words)) <= covered, field.name
