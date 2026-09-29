import json
import logging
import queue
import time

import paho.mqtt.client as mqtt
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

from .commands import Command, CommandError, parse_command
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


def write_register(client: ModbusTcpClient, device_id: int, command: Command) -> None:
    response = client.write_register(command.register - 1, command.value, device_id=device_id)
    if response.isError():
        raise ModbusException(f"Writing {command.description} failed: {response}")


class Bridge:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.status_topic = f"{config.mqtt_topic_prefix}/status"
        self.state_topic = f"{config.mqtt_topic_prefix}/state"
        self.command_prefix = f"{config.mqtt_topic_prefix}/set/"
        # Filled from the MQTT network thread, drained by the main loop, so Modbus is only used from one thread
        self.commands: queue.Queue[tuple[str, str]] = queue.Queue()
        self.last_status: str | None = None
        self.modbus = ModbusTcpClient(config.komfovent_host, port=config.komfovent_port)
        self.mqtt = self._create_mqtt_client()

    def _create_mqtt_client(self) -> mqtt.Client:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="komfovent-mqtt")
        if self.config.mqtt_username:
            client.username_pw_set(self.config.mqtt_username, self.config.mqtt_password)
        client.will_set(self.status_topic, "offline", retain=True)
        client.on_connect = self._on_connect
        client.on_disconnect = lambda _client, _userdata, _flags, reason, _props: log.warning(
            "MQTT disconnected: %s", reason
        )
        client.on_message = self._on_message
        return client

    def _on_connect(self, client: mqtt.Client, _userdata, _flags, reason, _props) -> None:
        log.info("MQTT connected: %s", reason)
        # Re-publish on reconnect, since the broker may have fired our will in the meantime
        if self.last_status:
            client.publish(self.status_topic, self.last_status, retain=True)
        if self.config.enable_control:
            client.subscribe(f"{self.command_prefix}+")
            log.info("Control enabled, listening on %s+", self.command_prefix)

    def _on_message(self, _client, _userdata, message: mqtt.MQTTMessage) -> None:
        name = message.topic.removeprefix(self.command_prefix)
        self.commands.put((name, message.payload.decode(errors="replace")))

    def _set_status(self, status: str) -> None:
        if status != self.last_status:
            self.mqtt.publish(self.status_topic, status, retain=True)
            self.last_status = status

    def _ensure_connected(self) -> None:
        if not self.modbus.connected:
            self.modbus.connect()

    def _poll(self) -> None:
        try:
            self._ensure_connected()
            state = decode(read_registers(self.modbus, self.config.komfovent_device_id))
        except ModbusException as error:
            log.warning("Komfovent unreachable: %s", error)
            self._set_status("offline")
            self.modbus.close()
            return

        self.mqtt.publish(self.state_topic, json.dumps(state), retain=True)
        self._set_status("online")
        log.debug("Published %s", state)

    def _execute(self, name: str, payload: str) -> None:
        try:
            command = parse_command(name, payload)
        except CommandError as error:
            log.warning("Ignoring command: %s", error)
            return

        try:
            self._ensure_connected()
            write_register(self.modbus, self.config.komfovent_device_id, command)
        except ModbusException as error:
            log.error("Command %s failed: %s", command.description, error)
            self.modbus.close()
            return

        log.info("Executed %s", command.description)

    def run(self) -> None:
        self.mqtt.connect_async(self.config.mqtt_host, self.config.mqtt_port)
        self.mqtt.loop_start()
        next_poll = 0.0
        try:
            while True:
                try:
                    name, payload = self.commands.get(timeout=max(0.0, next_poll - time.monotonic()))
                except queue.Empty:
                    self._poll()
                    next_poll = time.monotonic() + self.config.poll_interval
                    continue

                self._execute(name, payload)
                # Publish the new state right away rather than waiting for the next scheduled poll
                next_poll = 0.0
        finally:
            self.mqtt.publish(self.status_topic, "offline", retain=True).wait_for_publish(timeout=2)
            self.mqtt.loop_stop()
            self.mqtt.disconnect()
            self.modbus.close()


def run(config: Config) -> None:
    Bridge(config).run()
