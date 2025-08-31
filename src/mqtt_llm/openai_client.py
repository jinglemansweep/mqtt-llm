"""OpenAI-compatible API client for the MQTT-LLM bridge."""

import json
import logging
from typing import Optional

import aiohttp

from .config import OpenAIConfig


class OpenAIClient:
    """Client for interacting with OpenAI-compatible APIs."""

    def __init__(self, config: OpenAIConfig) -> None:
        """Initialize OpenAI-compatible client with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "OpenAIClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(
        self, exc_type: type, exc_val: Exception, exc_tb: object
    ) -> None:
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self) -> None:
        """Initialize HTTP session for API requests."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "mqtt-llm/0.1.0",
        }

        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        self.session = aiohttp.ClientSession(
            headers=headers,
            timeout=timeout,
            connector=aiohttp.TCPConnector(limit=10),
        )

        self.logger.info(
            f"OpenAI client initialized for {self.config.api_url}"
        )

    async def disconnect(self) -> None:
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
            self.logger.info("OpenAI client session closed")

    async def generate_response(self, message: str) -> str:
        """Generate response from OpenAI-compatible API."""
        if not self.session:
            raise RuntimeError(
                "OpenAI client not connected. Call connect() first."
            )

        try:
            # Prepare messages for chat completions format
            messages = []
            if self.config.system_prompt:
                messages.append(
                    {"role": "system", "content": self.config.system_prompt}
                )
            messages.append({"role": "user", "content": message})

            # Prepare the request payload for OpenAI format
            payload = {
                "model": self.config.model,
                "messages": messages,
                "max_tokens": self.config.max_tokens,
                "stream": False,
            }

            # Add temperature if configured
            if (
                hasattr(self.config, "temperature")
                and self.config.temperature is not None
            ):
                payload["temperature"] = self.config.temperature

            # Make API request to chat/completions endpoint
            url = f"{self.config.api_url.rstrip('/')}/v1/chat/completions"
            self.logger.debug(f"Making request to: {url}")
            self.logger.debug(
                f"Request payload: {json.dumps(payload, indent=2)}"
            )

            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    choices = data.get("choices", [])
                    if choices and len(choices) > 0:
                        generated_response: str = (
                            choices[0].get("message", {}).get("content", "")
                        )
                    else:
                        generated_response = ""

                    self.logger.info(
                        f"Generated response for model {self.config.model}"
                    )
                    self.logger.debug(f"Response: {generated_response}")

                    return generated_response
                else:
                    error_text = await response.text()
                    self.logger.error(
                        f"OpenAI API error {response.status}: {error_text}"
                    )
                    raise Exception(
                        f"OpenAI API request failed with status "
                        f"{response.status}: {error_text}"
                    )

        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP client error: {e}")
            raise Exception(f"Failed to connect to OpenAI API: {e}")
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            raise Exception(f"Invalid JSON response from OpenAI API: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error in generate_response: {e}")
            raise

    async def chat_response(self, messages: list) -> str:
        """Generate chat response from OpenAI-compatible API."""
        if not self.session:
            raise RuntimeError(
                "OpenAI client not connected. Call connect() first."
            )

        try:
            # Add system message if provided and not already present
            formatted_messages = list(messages)
            if self.config.system_prompt:
                # Check if system message already exists
                has_system = any(
                    msg.get("role") == "system" for msg in formatted_messages
                )
                if not has_system:
                    system_message = {
                        "role": "system",
                        "content": self.config.system_prompt,
                    }
                    formatted_messages.insert(0, system_message)

            # Prepare the request payload for OpenAI format
            payload = {
                "model": self.config.model,
                "messages": formatted_messages,
                "max_tokens": self.config.max_tokens,
                "stream": False,
            }

            # Add temperature if configured
            if (
                hasattr(self.config, "temperature")
                and self.config.temperature is not None
            ):
                payload["temperature"] = self.config.temperature

            # Make API request
            url = f"{self.config.api_url.rstrip('/')}/v1/chat/completions"
            self.logger.debug(f"Making chat request to: {url}")
            self.logger.debug(
                f"Request payload: {json.dumps(payload, indent=2)}"
            )

            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    choices = data.get("choices", [])
                    if choices and len(choices) > 0:
                        generated_response: str = (
                            choices[0].get("message", {}).get("content", "")
                        )
                    else:
                        generated_response = ""

                    self.logger.info(
                        f"Generated chat response for model {self.config.model}"
                    )
                    self.logger.debug(f"Response: {generated_response}")

                    return generated_response
                else:
                    error_text = await response.text()
                    self.logger.error(
                        f"OpenAI chat API error {response.status}: {error_text}"
                    )
                    raise Exception(
                        f"OpenAI chat API request failed with status "
                        f"{response.status}: {error_text}"
                    )

        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP client error: {e}")
            raise Exception(f"Failed to connect to OpenAI API: {e}")
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            raise Exception(f"Invalid JSON response from OpenAI API: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error in chat_response: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if OpenAI-compatible API is available and responsive."""
        if not self.session:
            await self.connect()

        if not self.session:
            raise RuntimeError("HTTP session not available")

        try:
            # Try to get models list from OpenAI-compatible endpoint
            base_url = self.config.api_url.rstrip("/")
            url = f"{base_url}/v1/models"
            self.logger.debug(f"Health check URL: {url}")

            async with self.session.get(url) as response:
                self.logger.debug(f"Health check status: {response.status}")

                if response.status == 200:
                    try:
                        data = await response.json()
                    except json.JSONDecodeError as e:
                        self.logger.warning(
                            f"Failed to parse models response as JSON: {e}"
                        )
                        # If we can't parse the response but got 200, assume healthy
                        return True

                    if data and isinstance(data, dict):
                        models = data.get("data", [])
                        model_names = []
                        for model in models:
                            if model and isinstance(model, dict):
                                model_id = model.get("id")
                                if model_id:
                                    model_names.append(model_id)
                    else:
                        model_names = []

                    self.logger.info(
                        f"OpenAI API is healthy. Available models: {len(model_names)} found"
                    )
                    self.logger.debug(
                        f"Model list: {model_names[:10]}..."
                    )  # Show first 10

                    # If no models returned, assume healthy (some APIs might not support model listing)
                    if not model_names:
                        self.logger.info(
                            "No models returned, assuming API is healthy"
                        )
                        return True

                    # Check if configured model is available (case-insensitive partial match)
                    model_found = any(
                        self.config.model.lower() in model_name.lower()
                        or model_name.lower() in self.config.model.lower()
                        for model_name in model_names
                    )

                    if not model_found:
                        self.logger.warning(
                            f"Configured model '{self.config.model}' not found "
                            f"in available models. Will attempt to use anyway."
                        )

                    return True
                elif response.status == 401:
                    self.logger.error(
                        "API authentication failed. Check your API key."
                    )
                    return False
                elif response.status == 403:
                    self.logger.error(
                        "API access forbidden. Check your API key permissions."
                    )
                    return False
                else:
                    error_text = await response.text()
                    self.logger.error(
                        f"OpenAI health check failed with status {response.status}: {error_text}"
                    )
                    return False

        except aiohttp.ClientError as e:
            self.logger.error(f"OpenAI health check network error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"OpenAI health check unexpected error: {e}")
            return False

    async def list_models(self) -> list:
        """List available models from OpenAI-compatible API."""
        if not self.session:
            await self.connect()

        if not self.session:
            raise RuntimeError("HTTP session not available")

        try:
            url = f"{self.config.api_url.rstrip('/')}/v1/models"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    models = (
                        data.get("data", [])
                        if data and isinstance(data, dict)
                        else []
                    )
                    return models  # type: ignore[no-any-return]
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to list models: {error_text}")

        except Exception as e:
            self.logger.error(f"Error listing models: {e}")
            raise
