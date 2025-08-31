"""MQTT client implementation for the MQTT-LLM bridge."""

import asyncio
import json
import logging
import re
import unicodedata
from typing import Any, Callable, Dict, Optional, Union

import paho.mqtt.client as mqtt
from jsonpath_ng import parse

from .config import MQTTConfig


class MQTTClient:
    """MQTT client for handling connections, subscriptions, and publishing."""

    def __init__(self, config: MQTTConfig) -> None:
        """Initialize MQTT client with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.message_handler: Optional[Callable[[str], None]] = None
        self.async_message_handler: Optional[
            Union[Callable[[str], None], Callable]
        ] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_message_handler(self, handler: Callable[[str], None]) -> None:
        """Set the message handler callback."""
        self.message_handler = handler

    def set_async_message_handler(
        self, handler: Union[Callable[[str], None], Callable]
    ) -> None:
        """Set the async message handler callback."""
        self.async_message_handler = handler

    def _on_connect(
        self, client: mqtt.Client, userdata: Any, flags: Dict, rc: int
    ) -> None:
        """Handle MQTT connection event."""
        if rc == 0:
            self.connected = True
            self.logger.info(f"Connected to MQTT broker {self.config.broker}")
            # Subscribe to the configured topic
            client.subscribe(self.config.subscribe_topic, qos=self.config.qos)
            self.logger.info(
                f"Subscribed to topic: {self.config.subscribe_topic}"
            )
        else:
            self.connected = False
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier",
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorised",
            }
            error_msg = error_messages.get(
                rc, f"Connection failed with code {rc}"
            )
            self.logger.error(f"MQTT connection failed: {error_msg}")

    def _on_disconnect(
        self, client: mqtt.Client, userdata: Any, rc: int
    ) -> None:
        """Handle MQTT disconnection event."""
        self.connected = False
        if rc == 0:
            self.logger.info("Disconnected from MQTT broker")
        else:
            self.logger.warning(
                f"Unexpected disconnection from MQTT broker: {rc}"
            )

    def _on_message(
        self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage
    ) -> None:
        """Handle incoming MQTT messages."""
        try:
            payload = message.payload.decode("utf-8")
            self.logger.debug(
                f"Received message on topic {message.topic}: {payload}"
            )

            # Extract text content based on configuration
            extracted_text = self._extract_text_content(payload)

            if extracted_text:
                # Check if message contains trigger pattern
                if not self._should_trigger_ai(extracted_text):
                    self.logger.debug(
                        f"Message does not contain trigger pattern '{self.config.trigger_pattern}', ignoring"
                    )
                    return
                if self.async_message_handler:
                    try:
                        # Use thread-safe scheduling to run async handler in main event loop
                        if asyncio.iscoroutinefunction(
                            self.async_message_handler
                        ):
                            if self._loop and not self._loop.is_closed():
                                # Schedule the coroutine to run in the main event loop
                                asyncio.run_coroutine_threadsafe(
                                    self.async_message_handler(extracted_text),
                                    self._loop,
                                )
                            else:
                                self.logger.error(
                                    "No event loop available for async handler"
                                )
                        else:
                            self.async_message_handler(extracted_text)
                    except Exception as e:
                        self.logger.error(
                            f"Error scheduling async handler: {e}"
                        )
                elif self.message_handler:
                    self.message_handler(extracted_text)
                else:
                    self.logger.warning("No message handler set")
            else:
                self.logger.warning("No text extracted from message")

        except Exception as e:
            self.logger.error(f"Error processing message: {e}")

    def _extract_text_content(self, payload: str) -> Optional[str]:
        """Extract text content from message payload using JSON path."""
        try:
            # Try to parse as JSON first
            try:
                self.logger.debug(
                    f"Attempting to parse JSON payload: {payload[:100]}..."
                )
                data = json.loads(payload)
                self.logger.debug(f"Successfully parsed JSON: {data}")

                # Use JSONPath to extract content
                jsonpath_expr = parse(self.config.subscribe_path)
                matches = jsonpath_expr.find(data)

                if matches:
                    extracted_value = str(matches[0].value)
                    self.logger.debug(
                        f"JSONPath '{self.config.subscribe_path}' matched: {extracted_value}"
                    )
                    return extracted_value
                else:
                    self.logger.warning(
                        f"No matches found for JSON path: {self.config.subscribe_path}. "
                        f"Available keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}"
                    )
                    return None
            except json.JSONDecodeError as e:
                # If not JSON, treat as plain text
                self.logger.debug(
                    f"JSON decode failed: {e}, payload: {payload[:200]}..."
                )
                if (
                    self.config.subscribe_path == "$.text"
                    or self.config.subscribe_path == "$"
                ):
                    return payload
                else:
                    self.logger.warning(
                        f"Message is not JSON but JSON path is specified: "
                        f"{self.config.subscribe_path}. Payload: {payload[:100]}..."
                    )
                    return None

        except Exception as e:
            self.logger.error(f"Error extracting text content: {e}")
            return None

    def _should_trigger_ai(self, message: str) -> bool:
        """Check if message contains the trigger pattern."""
        try:
            pattern_match = re.search(self.config.trigger_pattern, message)
            if pattern_match:
                self.logger.debug(
                    f"Trigger pattern '{self.config.trigger_pattern}' found in message"
                )
                return True
            return False
        except re.error as e:
            self.logger.error(
                f"Invalid trigger pattern regex '{self.config.trigger_pattern}': {e}"
            )
            return True

    def _on_subscribe(
        self, client: mqtt.Client, userdata: Any, mid: int, granted_qos: int
    ) -> None:
        """Handle subscription confirmation."""
        self.logger.debug(f"Subscription confirmed with QoS: {granted_qos}")

    def _on_publish(
        self, client: mqtt.Client, userdata: Any, mid: int
    ) -> None:
        """Handle publish confirmation."""
        self.logger.debug(f"Message published with mid: {mid}")

    def connect(self) -> None:
        """Connect to MQTT broker."""
        try:
            # Store reference to current event loop for thread-safe async calls
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = None

            self.client = mqtt.Client(client_id=self.config.client_id)

            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            self.client.on_subscribe = self._on_subscribe
            self.client.on_publish = self._on_publish

            # Set authentication if provided
            if self.config.username and self.config.password:
                self.client.username_pw_set(
                    self.config.username, self.config.password
                )
                self.logger.info("MQTT authentication configured")

            # Configure TLS if enabled or port 8883 is used
            if self.config.use_tls or self.config.port == 8883:
                self.logger.info("Configuring TLS/SSL connection")
                try:
                    if (
                        self.config.tls_ca_certs
                        or self.config.tls_certfile
                        or self.config.tls_keyfile
                    ):
                        # Custom certificates provided
                        self.client.tls_set(
                            ca_certs=self.config.tls_ca_certs,
                            certfile=self.config.tls_certfile,
                            keyfile=self.config.tls_keyfile,
                        )
                        self.logger.info(
                            "TLS configured with custom certificates"
                        )
                    else:
                        # Use system default certificates
                        self.client.tls_set()
                        self.logger.info(
                            "TLS configured with system default certificates"
                        )

                    # Handle certificate verification settings
                    if self.config.tls_insecure:
                        import ssl

                        self.client.tls_insecure_set(True)
                        self.logger.warning(
                            "TLS certificate verification disabled (insecure)"
                        )

                except Exception as e:
                    self.logger.error(f"Failed to configure TLS: {e}")
                    raise

            # Connect to broker
            self.logger.info(
                f"Connecting to MQTT broker {self.config.broker}:{self.config.port}"
            )
            self.client.connect(self.config.broker, self.config.port, 5)

            # Start the network loop
            self.client.loop_start()

        except Exception as e:
            self.logger.error(f"Failed to connect to MQTT broker: {e}")
            raise

    def disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        if self.client:
            self.logger.info("Disconnecting from MQTT broker")
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except Exception as e:
                self.logger.warning(f"Error during MQTT disconnect: {e}")
            finally:
                # Force cleanup
                self.connected = False
                self.client = None

    def publish_response(self, response: str) -> None:
        """Publish response message to configured topic."""
        if not self.client or not self.connected:
            self.logger.error("Cannot publish: not connected to MQTT broker")
            return

        try:
            # Check if chunking is enabled and response needs chunking
            if (
                self.config.message_max_length
                and len(response) > self.config.message_max_length
            ):
                self._publish_chunked_response(response)
            else:
                # Format and publish single response
                formatted_response = self._format_response(response)
                self._publish_single_message(formatted_response)

        except Exception as e:
            self.logger.error(f"Error publishing response: {e}")

    def _publish_single_message(self, formatted_response: str) -> None:
        """Publish a single message."""
        if not self.client:
            self.logger.error("MQTT client not available")
            return

        result = self.client.publish(
            self.config.publish_topic,
            formatted_response,
            qos=self.config.qos,
            retain=self.config.retain,
        )

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            self.logger.info(
                f"Response published to {self.config.publish_topic}"
            )
            self.logger.debug(f"Published response: {formatted_response}")
        else:
            self.logger.error(f"Failed to publish response: {result.rc}")

    def _publish_chunked_response(self, response: str) -> None:
        """Publish response as multiple chunked messages."""
        if not self.config.message_max_length:
            raise ValueError("message_max_length must be set for chunking")

        # Calculate chunk size (reserve space for "X/Y: " prefix)
        prefix_space = 10  # Conservative estimate for "999/999: "
        chunk_size = self.config.message_max_length - prefix_space

        if chunk_size <= 0:
            self.logger.error(
                "Message max length too small for chunking (need space for prefix)"
            )
            return

        # Split response into chunks
        chunks = self._chunk_text(response, chunk_size)
        total_chunks = len(chunks)

        self.logger.info(
            f"Splitting response into {total_chunks} chunks "
            f"(max length: {self.config.message_max_length})"
        )

        # Publish each chunk with prefix
        for i, chunk in enumerate(chunks, 1):
            prefixed_chunk = f"{i}/{total_chunks}: {chunk}"
            formatted_chunk = self._format_response(prefixed_chunk)

            if not self.client:
                self.logger.error("MQTT client not available")
                return

            result = self.client.publish(
                self.config.publish_topic,
                formatted_chunk,
                qos=self.config.qos,
                retain=self.config.retain,
            )

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.debug(
                    f"Published chunk {i}/{total_chunks} to {self.config.publish_topic}"
                )
            else:
                self.logger.error(
                    f"Failed to publish chunk {i}/{total_chunks}: {result.rc}"
                )

    def _chunk_text(self, text: str, chunk_size: int) -> list:
        """Split text into chunks of specified size, preferring word boundaries."""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            if end >= len(text):
                # Last chunk
                chunks.append(text[start:])
                break

            # Try to find a good breaking point (space, punctuation)
            break_point = end

            # Look for space within last 20% of chunk
            look_back = min(chunk_size // 5, 50)
            search_start = max(end - look_back, start)

            for i in range(end - 1, search_start - 1, -1):
                if text[i] in " \n\t.!?;,":
                    break_point = i + 1
                    break

            chunks.append(text[start:break_point].rstrip())
            start = break_point

        return [chunk for chunk in chunks if chunk.strip()]

    def _format_response(self, response: str) -> str:
        """Format response using the configured template."""
        try:
            # First sanitize the response if configured
            sanitized_response = self._sanitize_response(response)
            template = self.config.publish_template
            self.logger.debug(
                f"Formatting response with template: {template} (type: {type(template)})"
            )

            if isinstance(template, str):
                # Check if string template is actually JSON
                if template.strip().startswith(
                    "{"
                ) and template.strip().endswith("}"):
                    try:
                        # Try to parse as JSON template with placeholder replacement
                        # First, replace the placeholder with a safe temporary marker
                        temp_template = template.replace(
                            "{response}", "__RESPONSE_PLACEHOLDER__"
                        )
                        json_template = json.loads(temp_template)

                        # Now recursively replace placeholders in the parsed JSON
                        def replace_placeholders(obj: Any) -> Any:
                            if isinstance(obj, str):
                                return obj.replace(
                                    "__RESPONSE_PLACEHOLDER__",
                                    sanitized_response,
                                )
                            elif isinstance(obj, dict):
                                return {
                                    k: replace_placeholders(v)
                                    for k, v in obj.items()
                                }
                            elif isinstance(obj, list):
                                return [
                                    replace_placeholders(item) for item in obj
                                ]
                            else:
                                return obj

                        formatted_json = replace_placeholders(json_template)
                        formatted_response = json.dumps(formatted_json)
                        self.logger.debug(
                            f"JSON template result: {formatted_response}"
                        )
                        return formatted_response
                    except json.JSONDecodeError:
                        # Fall through to simple string template
                        pass

                # Simple string template
                formatted = template.format(response=sanitized_response)
                self.logger.debug(f"String template result: {formatted}")
                return formatted
            elif isinstance(template, dict):
                # JSON template - replace placeholders in the dict
                formatted_template = json.dumps(template)
                self.logger.debug(
                    f"JSON template string: {formatted_template}"
                )
                formatted_response = formatted_template.format(
                    response=sanitized_response
                )
                self.logger.debug(
                    f"JSON template result: {formatted_response}"
                )
                return formatted_response
            else:
                # Fallback to plain response
                self.logger.debug(  # type: ignore[unreachable]
                    f"Using fallback (plain response): {sanitized_response}"
                )
                return sanitized_response

        except Exception as e:
            self.logger.error(f"Error formatting response: {e}")
            return response

    def _sanitize_response(self, response: str) -> str:
        """Sanitize response text by removing formatting, unicode, emojis."""
        if not self.config.sanitize_response:
            return response
        try:
            # Remove emojis and other symbols
            # This regex matches most emoji ranges
            emoji_pattern = re.compile(
                "["
                "\U0001f600-\U0001f64f"  # emoticons
                "\U0001f300-\U0001f5ff"  # symbols & pictographs
                "\U0001f680-\U0001f6ff"  # transport & map symbols
                "\U0001f1e0-\U0001f1ff"  # flags (iOS)
                "\U00002500-\U00002bef"  # chinese char
                "\U00002702-\U000027b0"
                "\U000024c2-\U0001f251"
                "\U0001f926-\U0001f937"
                "\U00010000-\U0010ffff"
                "\u2640-\u2642"
                "\u2600-\u2b55"
                "\u200d"
                "\u23cf"
                "\u23e9"
                "\u231a"
                "\ufe0f"  # dingbats
                "\u3030"
                "]+",
                re.UNICODE,
            )

            # Remove emojis
            text = emoji_pattern.sub(r"", response)

            # Remove extra whitespace and normalize newlines
            text = re.sub(r"\s+", " ", text)  # Multiple spaces to single space
            text = re.sub(r"\n+", " ", text)  # Newlines to spaces
            text = re.sub(r"\r+", " ", text)  # Carriage returns to spaces
            text = re.sub(r"\t+", " ", text)  # Tabs to spaces

            # Remove XML-like tags (including self-closing tags)
            text = re.sub(r"<[^>]*>", "", text)  # Remove all XML/HTML tags

            # Remove markdown formatting
            text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)  # **bold**
            text = re.sub(r"\*(.*?)\*", r"\1", text)  # *italic*
            text = re.sub(r"_(.*?)_", r"\1", text)  # _italic_
            text = re.sub(r"`(.*?)`", r"\1", text)  # `code`
            text = re.sub(r"#{1,6}\s*", "", text)  # # headers
            text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)  # [text](link)

            # Normalize unicode characters to ASCII equivalents where possible
            text = unicodedata.normalize("NFKD", text)
            text = text.encode("ascii", "ignore").decode("ascii")

            # Remove any remaining control characters
            text = "".join(
                char for char in text if unicodedata.category(char) != "Cc"
            )

            # Clean up extra spaces created by removals
            text = " ".join(text.split())

            # Strip leading/trailing whitespace
            text = text.strip()

            self.logger.debug(
                f"Sanitized response: '{response[:50]}...' -> '{text[:50]}...'"
            )
            return text

        except Exception as e:
            self.logger.warning(
                f"Error sanitizing response: {e}, returning original"
            )
            return response

    def is_connected(self) -> bool:
        """Check if client is connected to MQTT broker."""
        return self.connected
