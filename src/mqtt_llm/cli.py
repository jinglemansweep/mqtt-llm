"""Command-line interface for MQTT-LLM bridge."""

import logging
import os
from typing import Optional
from uuid import uuid4

import click

from .config import AppConfig


@click.command()
@click.option(
    "--mqtt-broker",
    help="MQTT broker address (required). Can also be set via MQTT_BROKER environment variable.",
    envvar="MQTT_BROKER",
)
@click.option(
    "--mqtt-port",
    type=int,
    default=1883,
    help="MQTT broker port (default: 1883). Environment: MQTT_PORT",
    envvar="MQTT_PORT",
)
@click.option(
    "--mqtt-username",
    help="MQTT username for authentication (optional). Environment: MQTT_USERNAME",
    envvar="MQTT_USERNAME",
)
@click.option(
    "--mqtt-password",
    help="MQTT password for authentication (optional). Environment: MQTT_PASSWORD",
    envvar="MQTT_PASSWORD",
)
@click.option(
    "--mqtt-client-id",
    help="MQTT client ID (default: auto-generated). Environment: MQTT_CLIENT_ID",
    envvar="MQTT_CLIENT_ID",
)
@click.option(
    "--mqtt-subscribe-topic",
    help="MQTT topic to subscribe to for incoming messages (required). Environment: MQTT_SUBSCRIBE_TOPIC",
    envvar="MQTT_SUBSCRIBE_TOPIC",
)
@click.option(
    "--mqtt-subscribe-path",
    default="$.text",
    help="JSONPath expression to extract text from incoming messages (default: $.text). Environment: MQTT_SUBSCRIBE_PATH",
    envvar="MQTT_SUBSCRIBE_PATH",
)
@click.option(
    "--mqtt-publish-topic",
    help="MQTT topic to publish LLM responses to (required). Environment: MQTT_PUBLISH_TOPIC",
    envvar="MQTT_PUBLISH_TOPIC",
)
@click.option(
    "--mqtt-publish-template",
    default="{response}",
    help="Template for formatting response messages. Use {response} placeholder (default: {response}). Environment: MQTT_PUBLISH_TEMPLATE",
    envvar="MQTT_PUBLISH_TEMPLATE",
)
@click.option(
    "--mqtt-qos",
    type=click.IntRange(0, 2),
    default=0,
    help="MQTT Quality of Service level: 0=at most once, 1=at least once, 2=exactly once (default: 0). Environment: MQTT_QOS",
    envvar="MQTT_QOS",
)
@click.option(
    "--mqtt-retain/--no-mqtt-retain",
    default=False,
    help="Whether to retain MQTT messages (default: no-retain). Environment: MQTT_RETAIN",
    envvar="MQTT_RETAIN",
)
@click.option(
    "--mqtt-sanitize-response/--no-mqtt-sanitize-response",
    default=False,
    help="Remove formatting, newlines, unicode, emojis from LLM responses (default: no-sanitize). Environment: MQTT_SANITIZE_RESPONSE",
    envvar="MQTT_SANITIZE_RESPONSE",
)
@click.option(
    "--mqtt-trigger-pattern",
    default="@ai",
    help="Regex pattern that must be present in message to trigger AI call (default: @ai). Environment: MQTT_TRIGGER_PATTERN",
    envvar="MQTT_TRIGGER_PATTERN",
)
@click.option(
    "--ollama-api-url",
    default="http://localhost:11434",
    help="Ollama API base URL (default: http://localhost:11434). Environment: OLLAMA_API_URL",
    envvar="OLLAMA_API_URL",
)
@click.option(
    "--ollama-api-key",
    help="Ollama API key for authentication (optional). Environment: OLLAMA_API_KEY",
    envvar="OLLAMA_API_KEY",
)
@click.option(
    "--ollama-model",
    help="Ollama model name to use (required). Environment: OLLAMA_MODEL",
    envvar="OLLAMA_MODEL",
)
@click.option(
    "--ollama-system-prompt",
    default="You are a helpful assistant.",
    help="System prompt to guide the LLM behavior (default: 'You are a helpful assistant.'). Environment: OLLAMA_SYSTEM_PROMPT",
    envvar="OLLAMA_SYSTEM_PROMPT",
)
@click.option(
    "--ollama-timeout",
    type=float,
    default=30.0,
    help="Timeout for Ollama API requests in seconds (default: 30.0). Environment: OLLAMA_TIMEOUT",
    envvar="OLLAMA_TIMEOUT",
)
@click.option(
    "--ollama-max-tokens",
    type=int,
    default=1000,
    help="Maximum number of tokens to generate in response (default: 1000). Environment: OLLAMA_MAX_TOKENS",
    envvar="OLLAMA_MAX_TOKENS",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    default="INFO",
    help="Application logging level (default: INFO). Environment: LOG_LEVEL",
    envvar="LOG_LEVEL",
)
@click.option(
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
    ollama_api_url: str,
    ollama_api_key: Optional[str],
    ollama_model: Optional[str],
    ollama_system_prompt: str,
    ollama_timeout: float,
    ollama_max_tokens: int,
    log_level: str,
    dry_run: bool,
) -> None:
    """MQTT to Ollama bridge application.

    This application connects MQTT messages to Ollama LLM API, allowing you to send
    messages via MQTT and receive AI-generated responses back through MQTT.

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
    - Ollama model name (--ollama-model or OLLAMA_MODEL)

    \b
    Example Usage:
    mqtt-llm --mqtt-broker mqtt.example.com --mqtt-subscribe-topic input/messages --mqtt-publish-topic output/responses --ollama-model llama3

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
        from .config import MQTTConfig, OllamaConfig

        # CLI arguments override environment variables
        mqtt_config = MQTTConfig(
            broker=mqtt_broker or os.getenv("MQTT_BROKER", ""),
            port=mqtt_port
            if mqtt_port != 1883
            else int(os.getenv("MQTT_PORT", "1883")),
            username=mqtt_username or os.getenv("MQTT_USERNAME"),
            password=mqtt_password or os.getenv("MQTT_PASSWORD"),
            client_id=mqtt_client_id or os.getenv("MQTT_CLIENT_ID", str(uuid4())),
            subscribe_topic=mqtt_subscribe_topic
            or os.getenv("MQTT_SUBSCRIBE_TOPIC", ""),
            subscribe_path=mqtt_subscribe_path
            if mqtt_subscribe_path != "$.text"
            else os.getenv("MQTT_SUBSCRIBE_PATH", "$.text"),
            publish_topic=mqtt_publish_topic or os.getenv("MQTT_PUBLISH_TOPIC", ""),
            publish_template=mqtt_publish_template
            if mqtt_publish_template != "{response}"
            else os.getenv("MQTT_PUBLISH_TEMPLATE", "{response}"),
            qos=mqtt_qos if mqtt_qos != 0 else int(os.getenv("MQTT_QOS", "0")),
            retain=mqtt_retain or os.getenv("MQTT_RETAIN", "false").lower() == "true",
            sanitize_response=mqtt_sanitize_response
            or os.getenv("MQTT_SANITIZE_RESPONSE", "false").lower() == "true",
            trigger_pattern=mqtt_trigger_pattern
            if mqtt_trigger_pattern != "@ai"
            else os.getenv("MQTT_TRIGGER_PATTERN", "@ai"),
        )

        ollama_config = OllamaConfig(
            api_url=ollama_api_url
            if ollama_api_url != "http://localhost:11434"
            else os.getenv("OLLAMA_API_URL", "http://localhost:11434"),
            api_key=ollama_api_key or os.getenv("OLLAMA_API_KEY"),
            model=ollama_model or os.getenv("OLLAMA_MODEL", ""),
            system_prompt=ollama_system_prompt
            if ollama_system_prompt != "You are a helpful assistant."
            else os.getenv("OLLAMA_SYSTEM_PROMPT", "You are a helpful assistant."),
            timeout=ollama_timeout
            if ollama_timeout != 30.0
            else float(os.getenv("OLLAMA_TIMEOUT", "30.0")),
            max_tokens=ollama_max_tokens
            if ollama_max_tokens != 1000
            else int(os.getenv("OLLAMA_MAX_TOKENS", "1000")),
        )

        app_config = AppConfig(
            mqtt=mqtt_config,
            ollama=ollama_config,
            log_level=log_level
            if log_level != "INFO"
            else os.getenv("LOG_LEVEL", "INFO"),
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
