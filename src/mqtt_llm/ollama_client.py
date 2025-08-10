"""Ollama API client for the MQTT-LLM bridge."""

import json
import logging
from typing import Optional

import aiohttp

from .config import OllamaConfig


class OllamaClient:
    """Client for interacting with Ollama API."""

    def __init__(self, config: OllamaConfig) -> None:
        """Initialize Ollama client with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "OllamaClient":
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
            f"Ollama client initialized for {self.config.api_url}"
        )

    async def disconnect(self) -> None:
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
            self.logger.info("Ollama client session closed")

    async def generate_response(self, message: str) -> str:
        """Generate response from Ollama API."""
        if not self.session:
            raise RuntimeError(
                "Ollama client not connected. Call connect() first."
            )

        try:
            # Prepare the request payload
            payload = {
                "model": self.config.model,
                "prompt": message,
                "system": self.config.system_prompt,
                "stream": False,
                "options": {
                    "num_predict": self.config.max_tokens,
                },
            }

            # Make API request
            url = f"{self.config.api_url.rstrip('/')}/api/generate"
            self.logger.debug(f"Making request to: {url}")
            self.logger.debug(
                f"Request payload: {json.dumps(payload, indent=2)}"
            )

            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    generated_response: str = data.get("response", "")

                    self.logger.info(
                        f"Generated response for model {self.config.model}"
                    )
                    self.logger.debug(f"Response: {generated_response}")

                    return generated_response
                else:
                    error_text = await response.text()
                    self.logger.error(
                        f"Ollama API error {response.status}: {error_text}"
                    )
                    raise Exception(
                        f"Ollama API request failed with status "
                        f"{response.status}: {error_text}"
                    )

        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP client error: {e}")
            raise Exception(f"Failed to connect to Ollama API: {e}")
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            raise Exception(f"Invalid JSON response from Ollama API: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error in generate_response: {e}")
            raise

    async def chat_response(self, messages: list) -> str:
        """Generate chat response from Ollama API using chat endpoint."""
        if not self.session:
            raise RuntimeError(
                "Ollama client not connected. Call connect() first."
            )

        try:
            # Prepare the request payload for chat endpoint
            payload = {
                "model": self.config.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "num_predict": self.config.max_tokens,
                },
            }

            # Add system message if provided
            if self.config.system_prompt:
                system_message = {
                    "role": "system",
                    "content": self.config.system_prompt,
                }
                if "messages" in payload and isinstance(
                    payload["messages"], list
                ):
                    payload["messages"].insert(0, system_message)

            # Make API request
            url = f"{self.config.api_url.rstrip('/')}/api/chat"
            self.logger.debug(f"Making chat request to: {url}")
            self.logger.debug(
                f"Request payload: {json.dumps(payload, indent=2)}"
            )

            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    message = data.get("message", {})
                    generated_response: str = message.get("content", "")

                    self.logger.info(
                        f"Generated chat response for model {self.config.model}"
                    )
                    self.logger.debug(f"Response: {generated_response}")

                    return generated_response
                else:
                    error_text = await response.text()
                    self.logger.error(
                        f"Ollama chat API error {response.status}: {error_text}"
                    )
                    raise Exception(
                        f"Ollama chat API request failed with status "
                        f"{response.status}: {error_text}"
                    )

        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP client error: {e}")
            raise Exception(f"Failed to connect to Ollama API: {e}")
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            raise Exception(f"Invalid JSON response from Ollama API: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error in chat_response: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if Ollama API is available and responsive."""
        if not self.session:
            await self.connect()

        if not self.session:
            raise RuntimeError("HTTP session not available")

        try:
            url = f"{self.config.api_url.rstrip('/')}/api/tags"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and isinstance(data, dict):
                        models = data.get("models", [])
                        model_names = []
                        for model in models:
                            if model and isinstance(model, dict):
                                name = model.get("name")
                                if name:
                                    model_names.append(name)
                    else:
                        model_names = []

                    self.logger.info(
                        f"Ollama API is healthy. Available models: {model_names}"
                    )

                    # Check if configured model is available
                    if self.config.model not in model_names:
                        self.logger.warning(
                            f"Configured model '{self.config.model}' not found "
                            f"in available models: {model_names}"
                        )
                        return False

                    return True
                else:
                    self.logger.error(
                        f"Ollama health check failed with status: {response.status}"
                    )
                    return False

        except Exception as e:
            self.logger.error(f"Ollama health check failed: {e}")
            return False

    async def list_models(self) -> list:
        """List available models from Ollama API."""
        if not self.session:
            await self.connect()

        if not self.session:
            raise RuntimeError("HTTP session not available")

        try:
            url = f"{self.config.api_url.rstrip('/')}/api/tags"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    models = (
                        data.get("models", [])
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
