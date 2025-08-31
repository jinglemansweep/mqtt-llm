"""Tests for configuration management."""

import pytest
from pydantic import ValidationError

from mqtt_llm.config import AppConfig, MQTTConfig, OpenAIConfig


def test_mqtt_config_defaults() -> None:
    """Test MQTT config with defaults."""
    config = MQTTConfig(
        broker="localhost",
        subscribe_topic="test/input",
        publish_topic="test/output",
    )
    assert config.port == 1883
    assert config.qos == 0
    assert not config.retain
    assert config.subscribe_path == "$.text"


def test_mqtt_config_validation() -> None:
    """Test MQTT config validation."""
    with pytest.raises(ValidationError):
        MQTTConfig(
            broker="localhost",
            port=70000,  # Invalid port
            subscribe_topic="test/input",
            publish_topic="test/output",
        )


def test_openai_config_defaults() -> None:
    """Test OpenAI config with defaults."""
    config = OpenAIConfig(model="llama3")
    assert config.api_url == "http://localhost:11434"
    assert config.timeout == 30.0
    assert config.max_tokens == 1000
    assert config.system_prompt == "You are a helpful assistant."
    assert config.temperature is None


def test_app_config() -> None:
    """Test complete app configuration."""
    mqtt_config = MQTTConfig(
        broker="localhost",
        subscribe_topic="test/input",
        publish_topic="test/output",
    )
    openai_config = OpenAIConfig(model="llama3")

    app_config = AppConfig(mqtt=mqtt_config, openai=openai_config)
    assert app_config.log_level == "INFO"


def test_log_level_validation() -> None:
    """Test log level validation."""
    mqtt_config = MQTTConfig(
        broker="localhost",
        subscribe_topic="test/input",
        publish_topic="test/output",
    )
    openai_config = OpenAIConfig(model="llama3")

    with pytest.raises(ValidationError):
        AppConfig(mqtt=mqtt_config, openai=openai_config, log_level="INVALID")
