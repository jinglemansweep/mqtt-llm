# MQTT-LLM Bridge

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-alpha-orange.svg)

An MQTT-to-LLM bridge application that connects MQTT message brokers to OpenAI-compatible APIs. This application enables you to send messages via MQTT and receive AI-generated responses, supporting local inference with Ollama, cloud APIs like OpenRouter and OpenAI, and any other OpenAI-compatible service.

## Features

- 🔌 **Universal API Support**: Works with Ollama, OpenRouter, OpenAI, and any OpenAI-compatible API
- 🚀 **Easy Setup**: Simple installation and configuration
- ⚙️ **Flexible Configuration**: Environment variables, CLI arguments, or configuration files
- 🔒 **Secure**: TLS/SSL support for MQTT connections with certificate validation
- 📊 **Robust**: Health checks, error handling, and comprehensive logging
- 🎯 **Message Filtering**: Configurable trigger patterns and JSONPath extraction
- 🔄 **Template Support**: Customizable response formatting
- 📝 **Message Chunking**: Automatic splitting of long responses with "1/x:" prefix
- 🧪 **Well Tested**: Comprehensive test suite with pre-commit hooks

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/mqtt-llm/mqtt-llm.git
cd mqtt-llm

# Install the package
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### Basic Usage

```bash
# Using Ollama (default)
mqtt-llm --mqtt-broker localhost \
         --mqtt-subscribe-topic "input/messages" \
         --mqtt-publish-topic "output/responses" \
         --openai-model llama3

# Using OpenRouter
mqtt-llm --mqtt-broker mqtt.example.com \
         --mqtt-subscribe-topic "ai/input" \
         --mqtt-publish-topic "ai/output" \
         --openai-api-url https://openrouter.ai/api \
         --openai-api-key "your-api-key" \
         --openai-model "anthropic/claude-3-haiku"

# Using OpenAI
mqtt-llm --mqtt-broker mqtt.example.com \
         --mqtt-subscribe-topic "ai/input" \
         --mqtt-publish-topic "ai/output" \
         --openai-api-url https://api.openai.com \
         --openai-api-key "your-api-key" \
         --openai-model "gpt-4"
```

### Configuration via Environment Variables

```bash
# MQTT Configuration
export MQTT_BROKER=mqtt.example.com
export MQTT_SUBSCRIBE_TOPIC=ai/input
export MQTT_PUBLISH_TOPIC=ai/output
export MQTT_USE_TLS=true

# API Configuration (OpenRouter example)
export OPENAI_API_URL=https://openrouter.ai/api
export OPENAI_API_KEY=your-api-key
export OPENAI_MODEL=anthropic/claude-3-haiku
export OPENAI_TEMPERATURE=0.7

# Run the application
mqtt-llm
```

## Supported APIs

### Local Inference
- **Ollama**: Run models locally (default configuration)

### Cloud APIs
- **OpenRouter**: Access to 100+ models from various providers
- **OpenAI**: Official OpenAI API (GPT-4, GPT-3.5, etc.)
- **Any OpenAI-compatible API**: Services implementing the chat completions format

### API Configuration Examples

#### Ollama (Local)
```bash
# Default configuration - no additional setup needed
mqtt-llm --openai-model llama3
```

#### OpenRouter
```bash
export OPENAI_API_URL=https://openrouter.ai/api
export OPENAI_API_KEY=sk-or-...
export OPENAI_MODEL=anthropic/claude-3-haiku
# or: microsoft/wizardlm-2-8x22b, google/gemma-2-9b, etc.
```

#### OpenAI
```bash
export OPENAI_API_URL=https://api.openai.com
export OPENAI_API_KEY=sk-...
export OPENAI_MODEL=gpt-4
```

## Message Processing Flow

1. **Receive**: MQTT messages are received on the subscribe topic
2. **Filter**: Messages are filtered using a trigger pattern (default: `@ai`)
3. **Extract**: Text content is extracted using JSONPath (default: `$.text`)
4. **Process**: Text is sent to the configured LLM API for processing
5. **Format**: Response is formatted using a template (default: `{response}`)
6. **Publish**: Response is published to the configured MQTT topic

### Message Format Examples

**Input Message:**
```json
{
  "text": "@ai What is the capital of France?",
  "user": "alice",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Output Message:**
```json
"The capital of France is Paris."
```

## Configuration Options

### MQTT Configuration
- `MQTT_BROKER`: MQTT broker hostname/IP (required)
- `MQTT_PORT`: MQTT broker port (default: 1883)
- `MQTT_USERNAME`: MQTT username for authentication
- `MQTT_PASSWORD`: MQTT password for authentication
- `MQTT_SUBSCRIBE_TOPIC`: Topic to listen for messages (required)
- `MQTT_PUBLISH_TOPIC`: Topic to publish responses (required)
- `MQTT_USE_TLS`: Enable TLS/SSL (default: false)
- `MQTT_TRIGGER_PATTERN`: Pattern to trigger AI processing (default: "@ai")
- `MQTT_SUBSCRIBE_PATH`: JSONPath for text extraction (default: "$.text")
- `MQTT_MESSAGE_MAX_LENGTH`: Maximum message length for chunking (optional)

### API Configuration
- `OPENAI_API_URL`: API base URL (default: http://localhost:11434)
- `OPENAI_API_KEY`: API key for authentication
- `OPENAI_MODEL`: Model name to use (required)
- `OPENAI_TEMPERATURE`: Sampling temperature 0.0-2.0
- `OPENAI_MAX_TOKENS`: Maximum response tokens (default: 1000)
- `OPENAI_SYSTEM_PROMPT`: System prompt (default: "You are a helpful assistant.")
- `OPENAI_SKIP_HEALTH_CHECK`: Skip API health check (default: false)

## Advanced Features

### Message Chunking
When responses exceed a configured length, they are automatically split into smaller chunks:

```bash
# Enable message chunking with 280 character limit
export MQTT_MESSAGE_MAX_LENGTH=280
```

**How it works:**
- Long responses are split at word boundaries when possible
- Each chunk is prefixed with "X/Y: " (e.g., "1/3: ", "2/3: ", "3/3: ")
- Works with message templates - the prefix is included in the response field
- Configurable via CLI: `--mqtt-message-max-length 280`

**Example Output:**
```
1/3: This is a very long response that has been split into multiple
2/3: chunks to fit within the configured message length limit. Each
3/3: chunk is numbered so you know the sequence and total count.
```

### TLS/SSL Support
```bash
# Enable TLS with custom certificates
export MQTT_USE_TLS=true
export MQTT_TLS_CA_CERTS=/path/to/ca.crt
export MQTT_TLS_CERTFILE=/path/to/client.crt
export MQTT_TLS_KEYFILE=/path/to/client.key
```

### Message Templates
```bash
# Custom response template
export MQTT_PUBLISH_TEMPLATE='{"response": "{response}", "model": "gpt-4", "timestamp": "2024-01-15T10:30:00Z"}'
```

### Health Check Options
```bash
# Skip health check for APIs that don't support /v1/models
export OPENAI_SKIP_HEALTH_CHECK=true
```

## Development

### Setup Development Environment
```bash
# Clone and install with dev dependencies
git clone https://github.com/mqtt-llm/mqtt-llm.git
cd mqtt-llm
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests
```bash
# Run all tests and quality checks
pre-commit run --all-files

# Run only tests
pytest

# Run with coverage
pytest --cov=mqtt_llm
```

### Code Quality
The project uses several tools to maintain code quality:
- **Black**: Code formatting (79 character line limit)
- **MyPy**: Static type checking
- **Flake8**: Code linting
- **isort**: Import sorting
- **Bandit**: Security analysis
- **Pytest**: Unit testing

## Architecture

The application follows a modular architecture:

- **MQTTLLMBridge**: Main orchestrator coordinating MQTT and API clients
- **MQTTClient**: Handles MQTT connections and message processing
- **OpenAIClient**: Manages HTTP connections to OpenAI-compatible APIs
- **Config Classes**: Pydantic-based configuration with validation
- **CLI Interface**: Click-based command-line interface

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pre-commit run --all-files`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📖 [Documentation](https://github.com/mqtt-llm/mqtt-llm/wiki)
- 🐛 [Bug Reports](https://github.com/mqtt-llm/mqtt-llm/issues)
- 💬 [Discussions](https://github.com/mqtt-llm/mqtt-llm/discussions)

## Acknowledgments

- Built with [paho-mqtt](https://eclipse.org/paho/) for MQTT connectivity
- Powered by [aiohttp](https://docs.aiohttp.org/) for async HTTP requests
- Configuration handled by [Pydantic](https://pydantic-docs.helpmanual.io/)
- CLI interface built with [Click](https://click.palletsprojects.com/)
