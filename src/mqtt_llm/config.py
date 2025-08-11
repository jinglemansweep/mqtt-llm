"""Configuration management for MQTT-LLM bridge."""

import os
from typing import Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class MQTTConfig(BaseModel):
    """MQTT configuration settings."""

    broker: str = Field(..., description="MQTT broker address")
    port: int = Field(default=1883, description="MQTT broker port")
    username: Optional[str] = Field(default=None, description="MQTT username")
    password: Optional[str] = Field(default=None, description="MQTT password")
    client_id: str = Field(
        default_factory=lambda: str(uuid4()), description="MQTT client ID"
    )
    subscribe_topic: str = Field(..., description="Topic to subscribe to")
    subscribe_path: str = Field(
        default="$.text", description="JSON path for extracting text content"
    )
    publish_topic: str = Field(
        ..., description="Topic to publish responses to"
    )
    publish_template: Union[str, dict] = Field(
        default="{response}", description="Template for response messages"
    )
    qos: int = Field(
        default=0, ge=0, le=2, description="Quality of Service level"
    )
    retain: bool = Field(default=False, description="Retain messages")
    sanitize_response: bool = Field(
        default=False,
        description="Remove formatting, newlines, unicode, emojis from LLM response",
    )
    trigger_pattern: str = Field(
        default="@ai",
        description="Regex pattern that must be present in message to trigger AI call",
    )
    use_tls: bool = Field(
        default=False, description="Enable TLS/SSL connection"
    )
    tls_ca_certs: Optional[str] = Field(
        default=None, description="Path to CA certificates file"
    )
    tls_certfile: Optional[str] = Field(
        default=None, description="Path to client certificate file"
    )
    tls_keyfile: Optional[str] = Field(
        default=None, description="Path to client private key file"
    )
    tls_insecure: bool = Field(
        default=False, description="Skip certificate verification (insecure)"
    )

    @field_validator("port")  # type: ignore[misc]
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate MQTT port range."""
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v


class OllamaConfig(BaseModel):
    """Ollama API configuration settings."""

    api_url: str = Field(
        default="http://localhost:11434", description="Ollama API URL"
    )
    api_key: Optional[str] = Field(default=None, description="Ollama API key")
    model: str = Field(..., description="Ollama model name")
    system_prompt: str = Field(
        default="You are a helpful assistant.",
        description="System prompt for LLM",
    )
    timeout: float = Field(
        default=30.0, gt=0, description="API request timeout"
    )
    max_tokens: int = Field(
        default=1000, gt=0, description="Maximum tokens in response"
    )


class AppConfig(BaseModel):
    """Main application configuration."""

    mqtt: MQTTConfig
    ollama: OllamaConfig
    log_level: str = Field(default="INFO", description="Logging level")

    @field_validator("log_level")  # type: ignore[misc]
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Load configuration from environment variables with validation."""
        try:
            # Parse MQTT port with validation
            mqtt_port_str = os.getenv("MQTT_PORT", "1883")
            try:
                mqtt_port = int(mqtt_port_str)
            except ValueError:
                raise ValueError(
                    f"Invalid MQTT_PORT value: {mqtt_port_str}. Must be an integer."
                )

            # Parse MQTT QoS with validation
            mqtt_qos_str = os.getenv("MQTT_QOS", "0")
            try:
                mqtt_qos = int(mqtt_qos_str)
            except ValueError:
                raise ValueError(
                    f"Invalid MQTT_QOS value: {mqtt_qos_str}. Must be an integer."
                )

            # Parse MQTT retain boolean
            mqtt_retain_str = os.getenv("MQTT_RETAIN", "false").lower()
            mqtt_retain = mqtt_retain_str in ("true", "1", "yes", "on")

            # Parse MQTT sanitize response boolean
            mqtt_sanitize_str = os.getenv(
                "MQTT_SANITIZE_RESPONSE", "false"
            ).lower()
            mqtt_sanitize = mqtt_sanitize_str in ("true", "1", "yes", "on")

            # Parse MQTT TLS boolean
            mqtt_use_tls_str = os.getenv("MQTT_USE_TLS", "false").lower()
            mqtt_use_tls = mqtt_use_tls_str in ("true", "1", "yes", "on")

            # Parse MQTT TLS insecure boolean
            mqtt_tls_insecure_str = os.getenv(
                "MQTT_TLS_INSECURE", "false"
            ).lower()
            mqtt_tls_insecure = mqtt_tls_insecure_str in (
                "true",
                "1",
                "yes",
                "on",
            )

            mqtt_config = MQTTConfig(
                broker=os.getenv("MQTT_BROKER", ""),
                port=mqtt_port,
                username=os.getenv("MQTT_USERNAME"),
                password=os.getenv("MQTT_PASSWORD"),
                client_id=os.getenv("MQTT_CLIENT_ID", str(uuid4())),
                subscribe_topic=os.getenv("MQTT_SUBSCRIBE_TOPIC", ""),
                subscribe_path=os.getenv("MQTT_SUBSCRIBE_PATH", "$.text"),
                publish_topic=os.getenv("MQTT_PUBLISH_TOPIC", ""),
                publish_template=os.getenv(
                    "MQTT_PUBLISH_TEMPLATE", "{response}"
                ),
                qos=mqtt_qos,
                retain=mqtt_retain,
                sanitize_response=mqtt_sanitize,
                trigger_pattern=os.getenv("MQTT_TRIGGER_PATTERN", "@ai"),
                use_tls=mqtt_use_tls,
                tls_ca_certs=os.getenv("MQTT_TLS_CA_CERTS"),
                tls_certfile=os.getenv("MQTT_TLS_CERTFILE"),
                tls_keyfile=os.getenv("MQTT_TLS_KEYFILE"),
                tls_insecure=mqtt_tls_insecure,
            )

            # Parse Ollama timeout with validation
            ollama_timeout_str = os.getenv("OLLAMA_TIMEOUT", "30.0")
            try:
                ollama_timeout = float(ollama_timeout_str)
            except ValueError:
                raise ValueError(
                    f"Invalid OLLAMA_TIMEOUT value: {ollama_timeout_str}. Must be a number."
                )

            # Parse Ollama max tokens with validation
            ollama_max_tokens_str = os.getenv("OLLAMA_MAX_TOKENS", "1000")
            try:
                ollama_max_tokens = int(ollama_max_tokens_str)
            except ValueError:
                raise ValueError(
                    f"Invalid OLLAMA_MAX_TOKENS value: {ollama_max_tokens_str}. Must be an integer."
                )

            ollama_config = OllamaConfig(
                api_url=os.getenv("OLLAMA_API_URL", "http://localhost:11434"),
                api_key=os.getenv("OLLAMA_API_KEY"),
                model=os.getenv("OLLAMA_MODEL", ""),
                system_prompt=os.getenv(
                    "OLLAMA_SYSTEM_PROMPT", "You are a helpful assistant."
                ),
                timeout=ollama_timeout,
                max_tokens=ollama_max_tokens,
            )

            return cls(
                mqtt=mqtt_config,
                ollama=ollama_config,
                log_level=os.getenv("LOG_LEVEL", "INFO"),
            )

        except ValueError as e:
            raise ValueError(
                f"Configuration error from environment variables: {e}"
            )

    def validate_config(self) -> None:
        """Validate the complete configuration and check for issues."""
        errors = []

        # Validate required MQTT fields
        if not self.mqtt.broker:
            errors.append("MQTT broker is required")
        if not self.mqtt.subscribe_topic:
            errors.append("MQTT subscribe topic is required")
        if not self.mqtt.publish_topic:
            errors.append("MQTT publish topic is required")

        # Validate MQTT QoS range
        if not 0 <= self.mqtt.qos <= 2:
            errors.append(f"MQTT QoS must be 0, 1, or 2, got: {self.mqtt.qos}")

        # Validate MQTT port range
        if not 1 <= self.mqtt.port <= 65535:
            errors.append(
                f"MQTT port must be between 1-65535, got: {self.mqtt.port}"
            )

        # Validate required Ollama fields
        if not self.ollama.model:
            errors.append("Ollama model is required")

        # Validate Ollama timeout
        if self.ollama.timeout <= 0:
            errors.append(
                f"Ollama timeout must be positive, got: {self.ollama.timeout}"
            )

        # Validate Ollama max_tokens
        if self.ollama.max_tokens <= 0:
            errors.append(
                f"Ollama max_tokens must be positive, got: {self.ollama.max_tokens}"
            )

        # Validate log level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_levels:
            errors.append(
                f"Log level must be one of {valid_levels}, got: {self.log_level}"
            )

        if errors:
            raise ValueError(
                "Configuration validation failed:\n"
                + "\n".join(f"- {error}" for error in errors)
            )

    def get_summary(self) -> dict:
        """Get a summary of the configuration for logging/display."""
        return {
            "mqtt_broker": f"{self.mqtt.broker}:{self.mqtt.port}",
            "mqtt_subscribe_topic": self.mqtt.subscribe_topic,
            "mqtt_publish_topic": self.mqtt.publish_topic,
            "mqtt_qos": self.mqtt.qos,
            "mqtt_retain": self.mqtt.retain,
            "mqtt_trigger_pattern": self.mqtt.trigger_pattern,
            "ollama_api_url": self.ollama.api_url,
            "ollama_model": self.ollama.model,
            "ollama_timeout": self.ollama.timeout,
            "ollama_max_tokens": self.ollama.max_tokens,
            "log_level": self.log_level,
        }
