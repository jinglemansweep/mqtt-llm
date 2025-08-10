"""Tests for environment variable configuration."""

import pytest
from pydantic import ValidationError

from mqtt_llm.config import AppConfig


class TestEnvironmentConfig:
    """Test environment variable configuration loading."""

    def test_from_env_valid_config(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test loading valid configuration from environment variables."""
        # Set environment variables
        env_vars = {
            "MQTT_BROKER": "test.mqtt.com",
            "MQTT_PORT": "8883",
            "MQTT_USERNAME": "testuser",
            "MQTT_PASSWORD": "testpass",
            "MQTT_SUBSCRIBE_TOPIC": "input/test",
            "MQTT_PUBLISH_TOPIC": "output/test",
            "MQTT_QOS": "1",
            "MQTT_RETAIN": "true",
            "OLLAMA_API_URL": "http://test.ollama.com:11434",
            "OLLAMA_MODEL": "test-model",
            "OLLAMA_TIMEOUT": "45.0",
            "OLLAMA_MAX_TOKENS": "500",
            "LOG_LEVEL": "DEBUG",
        }

        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

        config = AppConfig.from_env()

        assert config.mqtt.broker == "test.mqtt.com"
        assert config.mqtt.port == 8883
        assert config.mqtt.username == "testuser"
        assert config.mqtt.password == "testpass"
        assert config.mqtt.subscribe_topic == "input/test"
        assert config.mqtt.publish_topic == "output/test"
        assert config.mqtt.qos == 1
        assert config.mqtt.retain is True
        assert config.ollama.api_url == "http://test.ollama.com:11434"
        assert config.ollama.model == "test-model"
        assert config.ollama.timeout == 45.0
        assert config.ollama.max_tokens == 500
        assert config.log_level == "DEBUG"

    def test_from_env_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that defaults are used when environment variables are not set."""
        # Clear any existing environment variables
        env_vars = [
            "MQTT_BROKER",
            "MQTT_PORT",
            "MQTT_USERNAME",
            "MQTT_PASSWORD",
            "MQTT_CLIENT_ID",
            "MQTT_SUBSCRIBE_TOPIC",
            "MQTT_SUBSCRIBE_PATH",
            "MQTT_PUBLISH_TOPIC",
            "MQTT_PUBLISH_TEMPLATE",
            "MQTT_QOS",
            "MQTT_RETAIN",
            "OLLAMA_API_URL",
            "OLLAMA_API_KEY",
            "OLLAMA_MODEL",
            "OLLAMA_SYSTEM_PROMPT",
            "OLLAMA_TIMEOUT",
            "OLLAMA_MAX_TOKENS",
            "LOG_LEVEL",
        ]
        for var in env_vars:
            monkeypatch.delenv(var, raising=False)

        config = AppConfig.from_env()

        assert config.mqtt.broker == ""
        assert config.mqtt.port == 1883
        assert config.mqtt.username is None
        assert config.mqtt.password is None
        assert config.mqtt.subscribe_path == "$.text"
        assert config.mqtt.publish_template == "{response}"
        assert config.mqtt.qos == 0
        assert config.mqtt.retain is False
        assert config.ollama.api_url == "http://localhost:11434"
        assert config.ollama.timeout == 30.0
        assert config.ollama.max_tokens == 1000
        assert config.log_level == "INFO"

    def test_from_env_invalid_port(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test error handling for invalid MQTT port."""
        monkeypatch.setenv("MQTT_PORT", "not_a_number")

        with pytest.raises(ValueError, match="Invalid MQTT_PORT value"):
            AppConfig.from_env()

    def test_from_env_invalid_qos(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test error handling for invalid MQTT QoS."""
        monkeypatch.setenv("MQTT_QOS", "invalid")

        with pytest.raises(ValueError, match="Invalid MQTT_QOS value"):
            AppConfig.from_env()

    def test_from_env_invalid_timeout(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test error handling for invalid Ollama timeout."""
        monkeypatch.setenv("OLLAMA_TIMEOUT", "not_a_float")

        with pytest.raises(ValueError, match="Invalid OLLAMA_TIMEOUT value"):
            AppConfig.from_env()

    def test_from_env_invalid_max_tokens(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test error handling for invalid max tokens."""
        monkeypatch.setenv("OLLAMA_MAX_TOKENS", "not_an_int")

        with pytest.raises(
            ValueError, match="Invalid OLLAMA_MAX_TOKENS value"
        ):
            AppConfig.from_env()

    def test_retain_boolean_parsing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test MQTT retain boolean parsing variations."""
        test_cases = [
            ("true", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
            ("off", False),
            ("anything_else", False),
        ]

        for env_value, expected in test_cases:
            monkeypatch.setenv("MQTT_RETAIN", env_value)
            config = AppConfig.from_env()
            assert config.mqtt.retain is expected


class TestConfigValidation:
    """Test configuration validation methods."""

    def test_validate_config_success(self) -> None:
        """Test successful configuration validation."""
        from mqtt_llm.config import MQTTConfig, OllamaConfig

        mqtt_config = MQTTConfig(
            broker="test.mqtt.com",
            subscribe_topic="input/test",
            publish_topic="output/test",
        )
        ollama_config = OllamaConfig(model="test-model")
        config = AppConfig(mqtt=mqtt_config, ollama=ollama_config)

        # Should not raise any exception
        config.validate_config()

    def test_validate_config_missing_broker(self) -> None:
        """Test validation fails with missing MQTT broker."""
        from mqtt_llm.config import MQTTConfig, OllamaConfig

        mqtt_config = MQTTConfig(
            broker="",  # Empty broker
            subscribe_topic="input/test",
            publish_topic="output/test",
        )
        ollama_config = OllamaConfig(model="test-model")
        config = AppConfig(mqtt=mqtt_config, ollama=ollama_config)

        with pytest.raises(ValueError, match="MQTT broker is required"):
            config.validate_config()

    def test_validate_config_invalid_qos(self) -> None:
        """Test validation fails with invalid QoS during creation."""
        from mqtt_llm.config import MQTTConfig, OllamaConfig

        # Test that Pydantic validation catches invalid QoS at creation time
        with pytest.raises(
            ValidationError, match="Input should be less than or equal to 2"
        ):
            MQTTConfig(
                broker="test.mqtt.com",
                subscribe_topic="input/test",
                publish_topic="output/test",
                qos=5,  # Invalid QoS
            )

    def test_validate_config_missing_model(self) -> None:
        """Test validation fails with missing Ollama model."""
        from mqtt_llm.config import MQTTConfig, OllamaConfig

        mqtt_config = MQTTConfig(
            broker="test.mqtt.com",
            subscribe_topic="input/test",
            publish_topic="output/test",
        )
        ollama_config = OllamaConfig(model="")  # Empty model
        config = AppConfig(mqtt=mqtt_config, ollama=ollama_config)

        with pytest.raises(ValueError, match="Ollama model is required"):
            config.validate_config()

    def test_get_summary(self) -> None:
        """Test configuration summary generation."""
        from mqtt_llm.config import MQTTConfig, OllamaConfig

        mqtt_config = MQTTConfig(
            broker="test.mqtt.com",
            port=1883,
            subscribe_topic="input/test",
            publish_topic="output/test",
            qos=1,
            retain=True,
        )
        ollama_config = OllamaConfig(
            model="test-model",
            api_url="http://test.com:11434",
            timeout=45.0,
            max_tokens=500,
        )
        config = AppConfig(
            mqtt=mqtt_config, ollama=ollama_config, log_level="DEBUG"
        )

        summary = config.get_summary()

        expected_keys = {
            "mqtt_broker",
            "mqtt_subscribe_topic",
            "mqtt_publish_topic",
            "mqtt_qos",
            "mqtt_retain",
            "mqtt_trigger_pattern",
            "ollama_api_url",
            "ollama_model",
            "ollama_timeout",
            "ollama_max_tokens",
            "log_level",
        }

        assert set(summary.keys()) == expected_keys
        assert summary["mqtt_broker"] == "test.mqtt.com:1883"
        assert summary["mqtt_subscribe_topic"] == "input/test"
        assert summary["mqtt_publish_topic"] == "output/test"
        assert summary["mqtt_qos"] == 1
        assert summary["mqtt_retain"] is True
        assert summary["mqtt_trigger_pattern"] == "@ai"
        assert summary["ollama_api_url"] == "http://test.com:11434"
        assert summary["ollama_model"] == "test-model"
        assert summary["ollama_timeout"] == 45.0
        assert summary["ollama_max_tokens"] == 500
        assert summary["log_level"] == "DEBUG"
