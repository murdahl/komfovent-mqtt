import pytest

from komfovent_mqtt.config import Config, ConfigError


def test_defaults():
    config = Config.from_env({"KOMFOVENT_HOST": "192.168.1.50", "MQTT_HOST": "mosquitto"})

    assert config == Config(komfovent_host="192.168.1.50", mqtt_host="mosquitto")


def test_overrides():
    config = Config.from_env(
        {
            "KOMFOVENT_HOST": "192.168.1.50",
            "MQTT_HOST": "mosquitto",
            "MQTT_USERNAME": "komfovent",
            "MQTT_PASSWORD": "secret",
            "MQTT_TOPIC_PREFIX": "home/ventilation/",
            "POLL_INTERVAL": "10",
        }
    )

    assert config.mqtt_username == "komfovent"
    assert config.mqtt_topic_prefix == "home/ventilation"
    assert config.poll_interval == 10


def test_missing_required():
    with pytest.raises(ConfigError, match="KOMFOVENT_HOST, MQTT_HOST"):
        Config.from_env({})


def test_invalid_number():
    with pytest.raises(ConfigError):
        Config.from_env({"KOMFOVENT_HOST": "x", "MQTT_HOST": "y", "MQTT_PORT": "abc"})
