"""Main MQTT-LLM bridge application."""

import asyncio
import logging
import signal
import sys
from typing import Optional

from .config import AppConfig
from .mqtt_client import MQTTClient
from .ollama_client import OllamaClient


class MQTTLLMBridge:
    """Main bridge application connecting MQTT and Ollama."""

    def __init__(self, config: AppConfig) -> None:
        """Initialize the bridge with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.mqtt_client: Optional[MQTTClient] = None
        self.ollama_client: Optional[OllamaClient] = None
        self.running = False
        self.shutdown_event = asyncio.Event()

    async def _handle_mqtt_message(self, message: str) -> None:
        """Handle incoming MQTT message and generate response."""
        try:
            self.logger.info(f"Processing message: {message[:100]}...")

            if not self.ollama_client:
                self.logger.error("Ollama client not initialized")
                return

            # Generate response using Ollama
            response = await self.ollama_client.generate_response(message)

            if response:
                # Publish response back to MQTT
                if self.mqtt_client:
                    self.mqtt_client.publish_response(response)
                    self.logger.info("Response published successfully")
                else:
                    self.logger.error(
                        "MQTT client not available for publishing"
                    )
            else:
                self.logger.warning("Empty response from Ollama")

        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            # Optionally publish error response
            if self.mqtt_client:
                error_response = f"Error processing message: {str(e)}"
                self.mqtt_client.publish_response(error_response)

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        loop = asyncio.get_running_loop()

        def signal_handler() -> None:
            self.logger.info("Received shutdown signal, stopping...")
            self.shutdown_event.set()

        # Use asyncio's signal handling which works properly with event loops
        loop.add_signal_handler(signal.SIGINT, signal_handler)
        loop.add_signal_handler(signal.SIGTERM, signal_handler)

    async def start(self) -> None:
        """Start the bridge components."""
        try:
            self.logger.info("Starting MQTT-LLM bridge...")

            # Initialize Ollama client
            self.ollama_client = OllamaClient(self.config.ollama)
            await self.ollama_client.connect()

            # Health check for Ollama
            if not await self.ollama_client.health_check():
                raise Exception("Ollama health check failed")

            # Initialize MQTT client
            self.mqtt_client = MQTTClient(self.config.mqtt)
            self.mqtt_client.set_async_message_handler(
                self._handle_mqtt_message
            )
            self.mqtt_client.connect()

            # Wait for MQTT connection
            retry_count = 0
            max_retries = 30  # 30 seconds
            while (
                not self.mqtt_client.is_connected()
                and retry_count < max_retries
            ):
                await asyncio.sleep(1)
                retry_count += 1

            if not self.mqtt_client.is_connected():
                raise Exception(
                    "Failed to connect to MQTT broker within timeout"
                )

            self.running = True
            self.logger.info("MQTT-LLM bridge started successfully")

        except Exception as e:
            self.logger.error(f"Failed to start bridge: {e}")
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop the bridge components."""
        self.logger.info("Stopping MQTT-LLM bridge...")
        self.running = False

        # Disconnect MQTT client
        if self.mqtt_client:
            self.mqtt_client.disconnect()

        # Disconnect Ollama client
        if self.ollama_client:
            await self.ollama_client.disconnect()

        self.logger.info("MQTT-LLM bridge stopped")

    async def run(self) -> None:
        """Run the bridge application."""
        # Setup signal handlers
        self._setup_signal_handlers()

        try:
            # Start the bridge
            await self.start()

            # Run until shutdown signal
            self.logger.info("Bridge is running. Press Ctrl+C to stop.")

            # Use asyncio.wait_for with a timeout to periodically check for shutdown
            while not self.shutdown_event.is_set():
                try:
                    await asyncio.wait_for(
                        self.shutdown_event.wait(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    # Check if we should continue running
                    if not self.running:
                        break

        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            sys.exit(1)
        finally:
            await self.stop()

    async def run_once(self, message: str) -> str:
        """Process a single message and return response (for testing)."""
        try:
            # Initialize Ollama client if needed
            if not self.ollama_client:
                self.ollama_client = OllamaClient(self.config.ollama)
                await self.ollama_client.connect()

            # Generate response
            response = await self.ollama_client.generate_response(message)
            return response

        except Exception as e:
            self.logger.error(f"Error in run_once: {e}")
            raise

    def is_running(self) -> bool:
        """Check if bridge is running."""
        return self.running

    def get_status(self) -> dict:
        """Get bridge status information."""
        return {
            "running": self.running,
            "mqtt_connected": self.mqtt_client.is_connected()
            if self.mqtt_client
            else False,
            "ollama_url": self.config.ollama.api_url,
            "ollama_model": self.config.ollama.model,
            "mqtt_broker": f"{self.config.mqtt.broker}:{self.config.mqtt.port}",
            "subscribe_topic": self.config.mqtt.subscribe_topic,
            "publish_topic": self.config.mqtt.publish_topic,
        }
