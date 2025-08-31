"""Command-line interface for MQTT-LLM bridge."""

import logging
import os
from typing import Optional
from uuid import uuid4

import click

from .config import AppConfig


@click.command()  # type: ignore[misc]
@click.option(  # type: ignore[misc]
    "--mqtt-broker",
    help="MQTT broker address (required). Can also be set via MQTT_BROKER environment variable.",
    envvar="MQTT_BROKER",
)
@click.option(  # type: ignore[misc]
    "--mqtt-port",
    type=int,
    default=1883,
    help="MQTT broker port (default: 1883). Environment: MQTT_PORT",
    envvar="MQTT_PORT",
)
@click.option(  # type: ignore[misc]
    "--mqtt-username",
    help="MQTT username for authentication (optional). Environment: MQTT_USERNAME",
    envvar="MQTT_USERNAME",
)
@click.option(  # type: ignore[misc]
    "--mqtt-password",
    help="MQTT password for authentication (optional). Environment: MQTT_PASSWORD",
    envvar="MQTT_PASSWORD",
)
@click.option(  # type: ignore[misc]
    "--mqtt-client-id",
    help="MQTT client ID (default: auto-generated). Environment: MQTT_CLIENT_ID",
    envvar="MQTT_CLIENT_ID",
)
@click.option(  # type: ignore[misc]
    "--mqtt-subscribe-topic",
    help="MQTT topic to subscribe to for incoming messages (required). Environment: MQTT_SUBSCRIBE_TOPIC",
    envvar="MQTT_SUBSCRIBE_TOPIC",
)
@click.option(  # type: ignore[misc]
    "--mqtt-subscribe-path",
    default="$.text",
    help="JSONPath expression to extract text from incoming messages (default: $.text). Environment: MQTT_SUBSCRIBE_PATH",
    envvar="MQTT_SUBSCRIBE_PATH",
)
@click.option(  # type: ignore[misc]
    "--mqtt-publish-topic",
    help="MQTT topic to publish LLM responses to (required). Environment: MQTT_PUBLISH_TOPIC",
    envvar="MQTT_PUBLISH_TOPIC",
)
@click.option(  # type: ignore[misc]
    "--mqtt-publish-template",
    default="{response}",
    help="Template for formatting response messages. Use {response} placeholder (default: {response}). Environment: MQTT_PUBLISH_TEMPLATE",
    envvar="MQTT_PUBLISH_TEMPLATE",
)
@click.option(  # type: ignore[misc]
    "--mqtt-qos",
    type=click.IntRange(0, 2),
    default=0,
    help="MQTT Quality of Service level: 0=at most once, 1=at least once, 2=exactly once (default: 0). Environment: MQTT_QOS",
    envvar="MQTT_QOS",
)
@click.option(  # type: ignore[misc]
    "--mqtt-retain/--no-mqtt-retain",
    default=False,
    help="Whether to retain MQTT messages (default: no-retain). Environment: MQTT_RETAIN",
    envvar="MQTT_RETAIN",
)
@click.option(  # type: ignore[misc]
    "--mqtt-sanitize-response/--no-mqtt-sanitize-response",
    default=False,
    help="Remove formatting, newlines, unicode, emojis from LLM responses (default: no-sanitize). Environment: MQTT_SANITIZE_RESPONSE",
    envvar="MQTT_SANITIZE_RESPONSE",
)
@click.option(  # type: ignore[misc]
    "--mqtt-trigger-pattern",
    default="@ai",
    help="Regex pattern that must be present in message to trigger AI call (default: @ai). Environment: MQTT_TRIGGER_PATTERN",
    envvar="MQTT_TRIGGER_PATTERN",
)
@click.option(  # type: ignore[misc]
    "--mqtt-use-tls/--no-mqtt-use-tls",
    default=False,
    help="Enable TLS/SSL for MQTT connection (default: no-tls, automatically enabled for port 8883). Environment: MQTT_USE_TLS",
    envvar="MQTT_USE_TLS",
)
@click.option(  # type: ignore[misc]
    "--mqtt-tls-ca-certs",
    help="Path to CA certificates file for TLS validation (optional). Environment: MQTT_TLS_CA_CERTS",
    envvar="MQTT_TLS_CA_CERTS",
)
@click.option(  # type: ignore[misc]
    "--mqtt-tls-certfile",
    help="Path to client certificate file for TLS authentication (optional). Environment: MQTT_TLS_CERTFILE",
    envvar="MQTT_TLS_CERTFILE",
)
@click.option(  # type: ignore[misc]
    "--mqtt-tls-keyfile",
    help="Path to client private key file for TLS authentication (optional). Environment: MQTT_TLS_KEYFILE",
    envvar="MQTT_TLS_KEYFILE",
)
@click.option(  # type: ignore[misc]
    "--mqtt-tls-insecure/--no-mqtt-tls-insecure",
    default=False,
    help="Skip certificate verification for TLS (insecure, default: no-insecure). Environment: MQTT_TLS_INSECURE",
    envvar="MQTT_TLS_INSECURE",
)
@click.option(  # type: ignore[misc]
    "--mqtt-message-max-length",
    type=int,
    help="Maximum message length in characters. Long responses will be chunked with '1/x:' prefix. Environment: MQTT_MESSAGE_MAX_LENGTH",
    envvar="MQTT_MESSAGE_MAX_LENGTH",
)
@click.option(  # type: ignore[misc]
    "--openai-api-url",
    default="http://localhost:11434",
    help="OpenAI-compatible API base URL (default: http://localhost:11434 for Ollama). Environment: OPENAI_API_URL",
    envvar="OPENAI_API_URL",
)
@click.option(  # type: ignore[misc]
    "--openai-api-key",
    help="API key for authentication (optional). Environment: OPENAI_API_KEY",
    envvar="OPENAI_API_KEY",
)
@click.option(  # type: ignore[misc]
    "--openai-model",
    help="Model name to use (required). Examples: llama3, gpt-4, claude-3-sonnet. Environment: OPENAI_MODEL",
    envvar="OPENAI_MODEL",
)
@click.option(  # type: ignore[misc]
    "--openai-system-prompt",
    default="You are a helpful assistant.",
    help="System prompt to guide the LLM behavior (default: 'You are a helpful assistant.'). Environment: OPENAI_SYSTEM_PROMPT",
    envvar="OPENAI_SYSTEM_PROMPT",
)
@click.option(  # type: ignore[misc]
    "--openai-timeout",
    type=float,
    default=30.0,
    help="Timeout for API requests in seconds (default: 30.0). Environment: OPENAI_TIMEOUT",
    envvar="OPENAI_TIMEOUT",
)
@click.option(  # type: ignore[misc]
    "--openai-max-tokens",
    type=int,
    default=1000,
    help="Maximum number of tokens to generate in response (default: 1000). Environment: OPENAI_MAX_TOKENS",
    envvar="OPENAI_MAX_TOKENS",
)
@click.option(  # type: ignore[misc]
    "--openai-temperature",
    type=float,
    help="Sampling temperature (0.0-2.0, optional). Environment: OPENAI_TEMPERATURE",
    envvar="OPENAI_TEMPERATURE",
)
@click.option(  # type: ignore[misc]
    "--openai-skip-health-check/--no-openai-skip-health-check",
    default=False,
    help="Skip health check on startup (useful for APIs that don't support /v1/models). Environment: OPENAI_SKIP_HEALTH_CHECK",
    envvar="OPENAI_SKIP_HEALTH_CHECK",
)
@click.option(  # type: ignore[misc]
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    default="INFO",
    help="Application logging level (default: INFO). Environment: LOG_LEVEL",
    envvar="LOG_LEVEL",
)
@click.option(  # type: ignore[misc]
    "--dry-run",
    is_flag=True,
    help="Validate configuration and display settings without starting the bridge",
)
def main(
    mqtt_broker: Optional[str],
    mqtt_port: int,
    mqtt_username: Optional[str],
    mqtt_password: Optional[str],
    mqtt_client_id: Optional[str],
    mqtt_subscribe_topic: Optional[str],
    mqtt_subscribe_path: str,
    mqtt_publish_topic: Optional[str],
    mqtt_publish_template: str,
    mqtt_qos: int,
    mqtt_retain: bool,
    mqtt_sanitize_response: bool,
    mqtt_trigger_pattern: str,
    mqtt_use_tls: bool,
    mqtt_tls_ca_certs: Optional[str],
    mqtt_tls_certfile: Optional[str],
    mqtt_tls_keyfile: Optional[str],
    mqtt_tls_insecure: bool,
    mqtt_message_max_length: Optional[int],
    openai_api_url: str,
    openai_api_key: Optional[str],
    openai_model: Optional[str],
    openai_system_prompt: str,
    openai_timeout: float,
    openai_max_tokens: int,
    openai_temperature: Optional[float],
    openai_skip_health_check: bool,
    log_level: str,
    dry_run: bool,
) -> None:
    """MQTT to OpenAI-compatible LLM bridge application.

    This application connects MQTT messages to OpenAI-compatible APIs (Ollama, OpenRouter, etc.),
    allowing you to send messages via MQTT and receive AI-generated responses back through MQTT.

    \b
    Configuration Priority (highest to lowest):
    1. Command-line arguments
    2. Environment variables
    3. Default values

    \b
    Required Configuration:
    - MQTT broker address (--mqtt-broker or MQTT_BROKER)
    - MQTT subscribe topic (--mqtt-subscribe-topic or MQTT_SUBSCRIBE_TOPIC)
    - MQTT publish topic (--mqtt-publish-topic or MQTT_PUBLISH_TOPIC)
    - Model name (--openai-model or OPENAI_MODEL)

    \b
    Example Usage:
    mqtt-llm --mqtt-broker mqtt.example.com --mqtt-subscribe-topic input/messages --mqtt-publish-topic output/responses --openai-model llama3

    \b
    Environment Variables:
    All command-line options can be configured via environment variables.
    See individual option help for the corresponding environment variable names.
    """
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    try:
        # Load configuration from environment and CLI arguments
        logger.info("Loading configuration from environment and CLI arguments")

        # Build config from CLI arguments and environment
        from .config import MQTTConfig, OpenAIConfig

        # CLI arguments override environment variables
        mqtt_config = MQTTConfig(
            broker=mqtt_broker or os.getenv("MQTT_BROKER", ""),
            port=(
                mqtt_port
                if mqtt_port != 1883
                else int(os.getenv("MQTT_PORT", "1883"))
            ),
            username=mqtt_username or os.getenv("MQTT_USERNAME"),
            password=mqtt_password or os.getenv("MQTT_PASSWORD"),
            client_id=mqtt_client_id
            or os.getenv("MQTT_CLIENT_ID", str(uuid4())),
            subscribe_topic=mqtt_subscribe_topic
            or os.getenv("MQTT_SUBSCRIBE_TOPIC", ""),
            subscribe_path=(
                mqtt_subscribe_path
                if mqtt_subscribe_path != "$.text"
                else os.getenv("MQTT_SUBSCRIBE_PATH", "$.text")
            ),
            publish_topic=mqtt_publish_topic
            or os.getenv("MQTT_PUBLISH_TOPIC", ""),
            publish_template=(
                mqtt_publish_template
                if mqtt_publish_template != "{response}"
                else os.getenv("MQTT_PUBLISH_TEMPLATE", "{response}")
            ),
            qos=mqtt_qos if mqtt_qos != 0 else int(os.getenv("MQTT_QOS", "0")),
            retain=mqtt_retain
            or os.getenv("MQTT_RETAIN", "false").lower() == "true",
            sanitize_response=mqtt_sanitize_response
            or os.getenv("MQTT_SANITIZE_RESPONSE", "false").lower() == "true",
            trigger_pattern=(
                mqtt_trigger_pattern
                if mqtt_trigger_pattern != "@ai"
                else os.getenv("MQTT_TRIGGER_PATTERN", "@ai")
            ),
            use_tls=mqtt_use_tls
            or os.getenv("MQTT_USE_TLS", "false").lower() == "true",
            tls_ca_certs=mqtt_tls_ca_certs or os.getenv("MQTT_TLS_CA_CERTS"),
            tls_certfile=mqtt_tls_certfile or os.getenv("MQTT_TLS_CERTFILE"),
            tls_keyfile=mqtt_tls_keyfile or os.getenv("MQTT_TLS_KEYFILE"),
            tls_insecure=mqtt_tls_insecure
            or os.getenv("MQTT_TLS_INSECURE", "false").lower() == "true",
            message_max_length=(
                mqtt_message_max_length
                if mqtt_message_max_length is not None
                else (
                    int(length_str)
                    if (length_str := os.getenv("MQTT_MESSAGE_MAX_LENGTH"))
                    else None
                )
            ),
        )

        openai_config = OpenAIConfig(
            api_url=(
                openai_api_url
                if openai_api_url != "http://localhost:11434"
                else os.getenv("OPENAI_API_URL", "http://localhost:11434")
            ),
            api_key=openai_api_key or os.getenv("OPENAI_API_KEY"),
            model=openai_model or os.getenv("OPENAI_MODEL", ""),
            system_prompt=(
                openai_system_prompt
                if openai_system_prompt != "You are a helpful assistant."
                else os.getenv(
                    "OPENAI_SYSTEM_PROMPT", "You are a helpful assistant."
                )
            ),
            timeout=(
                openai_timeout
                if openai_timeout != 30.0
                else float(os.getenv("OPENAI_TIMEOUT", "30.0"))
            ),
            max_tokens=(
                openai_max_tokens
                if openai_max_tokens != 1000
                else int(os.getenv("OPENAI_MAX_TOKENS", "1000"))
            ),
            temperature=(
                openai_temperature
                if openai_temperature is not None
                else (
                    float(temp_str)
                    if (temp_str := os.getenv("OPENAI_TEMPERATURE"))
                    else None
                )
            ),
            skip_health_check=(
                openai_skip_health_check
                or os.getenv("OPENAI_SKIP_HEALTH_CHECK", "false").lower()
                == "true"
            ),
        )

        app_config = AppConfig(
            mqtt=mqtt_config,
            openai=openai_config,
            log_level=(
                log_level
                if log_level != "INFO"
                else os.getenv("LOG_LEVEL", "INFO")
            ),
        )

        # Validate the complete configuration
        app_config.validate_config()

        if dry_run:
            click.echo("Configuration validation successful!")
            summary = app_config.get_summary()
            for key, value in summary.items():
                click.echo(f"{key.replace('_', ' ').title()}: {value}")
            return

        logger.info("Starting MQTT-LLM bridge...")

        # Import and run the application
        import asyncio

        from .bridge import MQTTLLMBridge

        bridge = MQTTLLMBridge(app_config)
        try:
            asyncio.run(bridge.run())
        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
            pass  # Exit gracefully

    except Exception as e:
        logger.error(f"Error: {e}")
        raise click.ClickException(str(e))


if __name__ == "__main__":
    main()
