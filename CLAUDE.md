# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an MQTT-LLM bridge application that connects MQTT message brokers to OpenAI-compatible APIs (including Ollama, OpenRouter, OpenAI, and others). The application listens for messages on MQTT topics, processes them with a language model, and publishes responses back to MQTT.

## Core Architecture

The application follows a modular architecture with clear separation of concerns:

- **MQTTLLMBridge** (`src/mqtt_llm/bridge.py`): Main orchestrator that coordinates MQTT and OpenAI-compatible clients
- **MQTTClient** (`src/mqtt_llm/mqtt_client.py`): Handles MQTT connections, subscriptions, and publishing using paho-mqtt
- **OpenAIClient** (`src/mqtt_llm/openai_client.py`): Manages HTTP connections to OpenAI-compatible APIs using aiohttp
- **Config classes** (`src/mqtt_llm/config.py`): Pydantic-based configuration management with validation (MQTTConfig, OpenAIConfig, AppConfig)
- **CLI interface** (`src/mqtt_llm/cli.py`): Click-based command-line interface with extensive configuration options

## Development Requirements

* ALWAYS activate the virtual environment (`./venv`) before running ANY commands.
* ALWAYS use `pre-commit` to run tests and checks. Only run them manually if necessary.
* ALWAYS keep line lengths under 80 characters
* ALWAYS end files with a newline character

### Installation and Setup
```bash
# Install in development mode with all dependencies
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

### Running the Application
```bash
# Run with command line arguments
mqtt-llm --mqtt-broker localhost --mqtt-subscribe-topic input/messages --mqtt-publish-topic output/responses --openai-model llama3

# Run with environment variables (see cli.py for all available env vars)
export MQTT_BROKER=localhost
export MQTT_SUBSCRIBE_TOPIC=input/messages
export MQTT_PUBLISH_TOPIC=output/responses
export OPENAI_MODEL=llama3
mqtt-llm

# For OpenRouter or OpenAI APIs:
export OPENAI_API_URL=https://openrouter.ai/api
export OPENAI_API_KEY=your-api-key
export OPENAI_MODEL=anthropic/claude-3-haiku
mqtt-llm

# Dry run to validate configuration
mqtt-llm --dry-run --mqtt-broker localhost --mqtt-subscribe-topic test --mqtt-publish-topic test --openai-model llama3
```

### Testing & Code Quality

All testings and code quality checks are managed by `pre-commit`. Do not run them manually unless necessary.

```bash
# Run all checks/tests
pre-commit run --all-files
```

## Configuration System

The application uses a hierarchical configuration system (CLI args > env vars > defaults) managed through Pydantic models:

- **MQTTConfig**: MQTT broker connection, topics, QoS, message processing options, chunking settings
- **OpenAIConfig**: OpenAI-compatible API URL, model selection, generation parameters, temperature
- **AppConfig**: Top-level configuration combining MQTT and OpenAI settings

All configuration options can be set via environment variables. Key variables:
- `OPENAI_API_URL`: API base URL (default: http://localhost:11434 for Ollama)
- `OPENAI_API_KEY`: API key for authentication
- `OPENAI_MODEL`: Model name (e.g., llama3, gpt-4, claude-3-sonnet)
- `OPENAI_TEMPERATURE`: Sampling temperature (0.0-2.0)
- `OPENAI_SKIP_HEALTH_CHECK`: Skip health check on startup (useful for APIs that don't support /v1/models)
- `MQTT_MESSAGE_MAX_LENGTH`: Maximum message length for auto-chunking (optional)
- See `src/mqtt_llm/cli.py` for complete list.

## Message Processing Flow

1. MQTT messages are received and filtered by trigger pattern (default: `@ai`)
2. Message content is extracted using JSONPath (default: `$.text`)
3. Text is sent to OpenAI-compatible API for processing
4. Response is formatted using publish template (default: `{response}`)
5. If message chunking is enabled and response exceeds max length, response is split into chunks with "X/Y: " prefixes
6. Response(s) are published to configured MQTT topic

## Key Dependencies

- **paho-mqtt**: MQTT client library
- **aiohttp**: Async HTTP client for OpenAI-compatible APIs
- **pydantic**: Configuration validation and parsing
- **click**: Command-line interface framework
- **jsonpath-ng**: JSON path extraction for message processing

## Entry Points

- **Console script**: `mqtt-llm` (defined in `pyproject.toml:38`)
- **Main module**: `python -m mqtt_llm.main`
- **Direct import**: `from mqtt_llm import MQTTLLMBridge`

## Supported APIs

The application works with any OpenAI-compatible API:
- **Ollama**: Local LLM inference (default: http://localhost:11434)
- **OpenRouter**: Access to multiple models via API (https://openrouter.ai/api)
- **OpenAI**: Official OpenAI API (https://api.openai.com)
- **Other compatible APIs**: Any service implementing OpenAI's chat completions format

## Code Quality Configuration

The project uses pyproject.toml for tool configuration:

- **Black**: Line length 79 characters, Python 3.11+ target
- **MyPy**: Strict type checking with external library overrides
- **Pytest**: Configured for tests/ directory with verbose output
- **Flake8**: 79 character line limit, compatible with Black
