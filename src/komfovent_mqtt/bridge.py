import json
import logging
import time

import paho.mqtt.client as mqtt
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

from .config import Config
from .registers import BLOCKS, decode

log = logging.getLogger(__name__)


def read_registers(client: ModbusTcpClient, device_id: int) -> dict[int, int]:
    raw: dict[int, int] = {}
    for start, count in BLOCKS:
        response = client.read_holding_registers(start - 1, count=count, device_id=device_id)
        if response.isError():
            raise ModbusException(f"Reading registers {start}-{start + count - 1} failed: {response}")
        raw.update(zip(range(start, start + count), response.registers))
    return raw


def create_mqtt_client(config: Config, status_topic: str) -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="komfovent-mqtt")
    if config.mqtt_username:
        client.username_pw_set(config.mqtt_username, config.mqtt_password)
    client.will_set(status_topic, "offline", retain=True)
    client.on_connect = lambda _client, _userdata, _flags, reason, _props: log.info("MQTT connected: %s", reason)
    client.on_disconnect = lambda _client, _userdata, _flags, reason, _props: log.warning("MQTT disconnected: %s", reason)
    client.connect_async(config.mqtt_host, config.mqtt_port)
    return client


def run(config: Config) -> None:
    status_topic = f"{config.mqtt_topic_prefix}/status"
    state_topic = f"{config.mqtt_topic_prefix}/state"

    mqtt_client = create_mqtt_client(config, status_topic)
    modbus_client = ModbusTcpClient(config.komfovent_host, port=config.komfovent_port)
    mqtt_client.loop_start()

    def set_status(status: str) -> None:
        nonlocal last_status
        if status != last_status:
            mqtt_client.publish(status_topic, status, retain=True)
            last_status = status

    last_status: str | None = None
    try:
        while True:
            try:
                if not modbus_client.connected:
                    modbus_client.connect()
                state = decode(read_registers(modbus_client, config.komfovent_device_id))
                mqtt_client.publish(state_topic, json.dumps(state), retain=True)
                set_status("online")
                log.debug("Published %s", state)
            except ModbusException as error:
                log.warning("Komfovent unreachable: %s", error)
                set_status("offline")
                modbus_client.close()

            time.sleep(config.poll_interval)
    finally:
        mqtt_client.publish(status_topic, "offline", retain=True).wait_for_publish(timeout=2)
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        modbus_client.close()
