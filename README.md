# komfovent-mqtt

Publishes readings from a Komfovent ventilation unit (Domekt and others with a **C6 / C6M** controller) to MQTT, over Modbus TCP. It can also switch the operation mode from MQTT, if you turn that on.

## Run

```sh
docker run -d --name komfovent-mqtt --restart unless-stopped \
  -e KOMFOVENT_HOST=192.168.1.50 \
  -e MQTT_HOST=192.168.1.10 \
  -e MQTT_USERNAME=komfovent -e MQTT_PASSWORD=secret \
  ghcr.io/murdahl/komfovent-mqtt:latest
```

Or with Docker Compose:

```yaml
services:
  komfovent-mqtt:
    image: ghcr.io/murdahl/komfovent-mqtt:latest
    restart: unless-stopped
    environment:
      KOMFOVENT_HOST: 192.168.1.50
      MQTT_HOST: mosquitto
      MQTT_USERNAME: komfovent
      MQTT_PASSWORD: ${MQTT_KOMFOVENT_PASSWORD}
```

Modbus TCP must be reachable on the unit (port 502). On the C6 it's on by default when the controller is on the network.

## Configuration

| Variable              | Default     | Description |
|-----------------------|-------------|-------------|
| `KOMFOVENT_HOST`      | (required)  | IP or hostname of the C6 controller |
| `KOMFOVENT_PORT`      | `502`       | Modbus TCP port |
| `KOMFOVENT_DEVICE_ID` | `1`         | Modbus unit ID |
| `MQTT_HOST`           | (required)  | MQTT broker |
| `MQTT_PORT`           | `1883`      | |
| `MQTT_USERNAME`       |             | |
| `MQTT_PASSWORD`       |             | |
| `MQTT_TOPIC_PREFIX`   | `komfovent` | |
| `POLL_INTERVAL`       | `30`        | Seconds between reads |
| `ENABLE_CONTROL`      | `false`     | `true` to accept commands on `komfovent/set/...`; otherwise the bridge never writes to the unit |
| `LOG_LEVEL`           | `INFO`      | `DEBUG` logs every published state |

## Topics

| Topic                | Retained | Payload |
|----------------------|----------|---------|
| `komfovent/status`   | yes      | `online` / `offline`. Goes `offline` when the unit stops answering or the bridge stops |
| `komfovent/state`    | yes      | JSON, see below |

```json
{
  "power": true,
  "eco_mode": false,
  "auto_mode": false,
  "operation_mode": "normal",
  "supply_temperature": 19.6,
  "extract_temperature": 25.1,
  "outdoor_temperature": 17.5,
  "supply_fan": 50.0,
  "extract_fan": 50.0,
  "heat_exchanger": 0.0,
  "electric_heater": 0.0,
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
  "indoor_absolute_humidity": 8.76
}
```

- **Units:** temperatures in °C; fans, heat exchanger, heater, filter clogging, efficiency and humidity in %; power in W; energy in kWh; absolute humidity in g/m³.
- **`operation_mode`:** one of `standby`, `away`, `normal`, `intensive`, `boost`, `kitchen`, `fireplace`, `override`, `holiday` or `air_quality`.
- **`panel_*`:** readings from the control panel's own sensors (panel 1). A value is `null` when the sensor is missing or out of range.

## Control

With `ENABLE_CONTROL=true`, the bridge subscribes to:

| Topic                           | Payload |
|---------------------------------|---------|
| `komfovent/set/operation_mode`  | `away`, `normal`, `intensive` or `boost` |

```sh
mosquitto_pub -t komfovent/set/operation_mode -m intensive
```

The bridge polls right after each command, so `komfovent/state` shows the new mode within a second. The fans ramp up over a few seconds, so their new speed appears at the next regular poll. A manually set mode lasts until the unit's own schedule changes mode. Invalid commands are logged and ignored.

## Development

```sh
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
KOMFOVENT_HOST=192.168.1.50 MQTT_HOST=localhost LOG_LEVEL=DEBUG .venv/bin/komfovent-mqtt
```

Pushes to `main` publish `ghcr.io/murdahl/komfovent-mqtt:latest`; `v*` tags publish versioned images.

## Credits

The register map and scaling come from [lnagel/hass-komfovent](https://github.com/lnagel/hass-komfovent) (MIT), the Home Assistant integration for Komfovent C6/C6M/C8.
