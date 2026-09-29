import os
from collections.abc import Mapping
from dataclasses import dataclass


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    komfovent_host: str
    mqtt_host: str
    komfovent_port: int = 502
    komfovent_device_id: int = 1
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    mqtt_topic_prefix: str = "komfovent"
    poll_interval: float = 30
    enable_control: bool = False

    @classmethod
    def from_env(cls, env: Mapping[str, str] = os.environ) -> "Config":
        missing = [name for name in ("KOMFOVENT_HOST", "MQTT_HOST") if not env.get(name)]
        if missing:
            raise ConfigError(f"Missing required environment variables: {', '.join(missing)}")

        try:
            return cls(
                komfovent_host=env["KOMFOVENT_HOST"],
                mqtt_host=env["MQTT_HOST"],
                komfovent_port=int(env.get("KOMFOVENT_PORT", cls.komfovent_port)),
                komfovent_device_id=int(env.get("KOMFOVENT_DEVICE_ID", cls.komfovent_device_id)),
                mqtt_port=int(env.get("MQTT_PORT", cls.mqtt_port)),
                mqtt_username=env.get("MQTT_USERNAME") or None,
                mqtt_password=env.get("MQTT_PASSWORD") or None,
                mqtt_topic_prefix=env.get("MQTT_TOPIC_PREFIX", cls.mqtt_topic_prefix).rstrip("/"),
                poll_interval=float(env.get("POLL_INTERVAL", cls.poll_interval)),
                enable_control=env.get("ENABLE_CONTROL", "").strip().lower() in ("1", "true", "yes"),
            )
        except ValueError as error:
            raise ConfigError(f"Invalid numeric setting: {error}") from error
