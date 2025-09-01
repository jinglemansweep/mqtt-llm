# MQTT-LLM Bridge

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Docker](https://img.shields.io/badge/docker-supported-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Connect MQTT message brokers to OpenAI-compatible APIs (Ollama, OpenRouter, OpenAI) for AI-powered message processing. Extract text from JSON messages, send to LLM, and publish formatted responses.

## Quick Start with Docker

### 1. Create Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit configuration
nano .env
```

### 2. Basic Docker Setup

```bash
# Run with Ollama (local inference)
docker run --rm --env-file .env \
  -e MQTT_BROKER=your-mqtt-broker.local \
  -e MQTT_SUBSCRIBE_TOPIC=chat/input \
  -e MQTT_PUBLISH_TOPIC=chat/output \
  -e OPENAI_MODEL=llama3 \
  ghcr.io/mqtt-llm/mqtt-llm:latest
```

### 3. Docker Compose (Recommended)

```yaml
# docker-compose.yml
version: '3.8'
services:
  mqtt-llm:
    image: ghcr.io/mqtt-llm/mqtt-llm:latest
    env_file: .env
    environment:
      - MQTT_BROKER=mosquitto
      - MQTT_SUBSCRIBE_TOPIC=chat/input
      - MQTT_PUBLISH_TOPIC=chat/output
      - OPENAI_MODEL=llama3
      - OPENAI_API_URL=http://ollama:11434
    depends_on:
      - mosquitto
      - ollama

  mosquitto:
    image: eclipse-mosquitto:2
    ports:
      - "1883:1883"

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
```

```bash
docker-compose up -d
```

## Message Processing Examples

### JSONPath Extraction

The `MQTT_SUBSCRIBE_PATH` setting extracts content from incoming JSON messages:

#### Simple Text Extraction
```bash
# Input message:
{"text": "@ai What's the weather?", "user": "alice"}

# Configuration:
MQTT_SUBSCRIBE_PATH=$.text

# Extracted: "@ai What's the weather?"
```

#### Nested Object Extraction
```bash
# Input message:
{
  "message": {
    "content": "@ai Translate: Hello world",
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "user": {"name": "bob", "id": 123}
}

# Configuration:
MQTT_SUBSCRIBE_PATH=$.message.content

# Extracted: "@ai Translate: Hello world"
```

#### Array Element Extraction
```bash
# Input message:
{
  "messages": [
    {"type": "user", "text": "@ai Help me"},
    {"type": "system", "text": "Processing..."}
  ]
}

# Configuration:
MQTT_SUBSCRIBE_PATH=$.messages[0].text

# Extracted: "@ai Help me"
```

### Response Templating

The `MQTT_PUBLISH_TEMPLATE` formats the LLM response with additional context:

#### Simple Response
```bash
# LLM Response: "The weather is sunny today."

# Template:
MQTT_PUBLISH_TEMPLATE={response}

# Output: "The weather is sunny today."
```

#### JSON Response with Metadata
```bash
# Template:
MQTT_PUBLISH_TEMPLATE={"response": "{response}", "model": "llama3", "timestamp": "2024-01-15T10:30:00Z"}

# Output:
{
  "response": "The weather is sunny today.",
  "model": "llama3",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Chat Application Format
```bash
# Template:
MQTT_PUBLISH_TEMPLATE={"user": "ai", "message": "{response}", "channel": 0}

# Output:
{
  "user": "ai",
  "message": "The weather is sunny today.",
  "channel": 0
}
```

## Configuration Examples

### Example 1: Basic Chat Bot
```bash
# .env file
MQTT_BROKER=mqtt.example.com
MQTT_SUBSCRIBE_TOPIC=chat/messages
MQTT_SUBSCRIBE_PATH=$.text
MQTT_PUBLISH_TOPIC=chat/responses
MQTT_PUBLISH_TEMPLATE={"user": "ai", "text": "{response}"}
MQTT_TRIGGER_PATTERN=@ai

OPENAI_API_URL=http://ollama:11434
OPENAI_MODEL=llama3
OPENAI_SYSTEM_PROMPT=You are a helpful chatbot. Keep responses under 200 characters.
```

### Example 2: Slack/Discord Bot
```bash
MQTT_BROKER=your-broker.local
MQTT_SUBSCRIBE_TOPIC=slack/messages
MQTT_SUBSCRIBE_PATH=$.event.text
MQTT_PUBLISH_TOPIC=slack/responses
MQTT_PUBLISH_TEMPLATE={"channel": "general", "text": "{response}", "username": "AI Bot"}
MQTT_TRIGGER_PATTERN=<@U12345>

OPENAI_API_URL=https://openrouter.ai/api
OPENAI_API_KEY=sk-or-your-key-here
OPENAI_MODEL=anthropic/claude-3-haiku
```

### Example 3: IoT Device Commands
```bash
MQTT_BROKER=iot.local
MQTT_SUBSCRIBE_TOPIC=devices/+/query
MQTT_SUBSCRIBE_PATH=$.query
MQTT_PUBLISH_TOPIC=devices/commands
MQTT_PUBLISH_TEMPLATE={"device_id": "controller", "command": "{response}", "type": "ai_response"}

OPENAI_API_URL=https://api.openai.com
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4
OPENAI_SYSTEM_PROMPT=Convert natural language to IoT commands. Respond only with JSON commands.
```

## Supported APIs

### Local Inference (Ollama)
```bash
OPENAI_API_URL=http://localhost:11434
OPENAI_MODEL=llama3
# No API key needed
```

### OpenRouter (100+ Models)
```bash
OPENAI_API_URL=https://openrouter.ai/api
OPENAI_API_KEY=sk-or-your-key
OPENAI_MODEL=anthropic/claude-3-haiku
# Or: google/gemma-2-9b, microsoft/wizardlm-2-8x22b, etc.
```

### OpenAI Official
```bash
OPENAI_API_URL=https://api.openai.com
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-4
```

## Advanced Features

### Message Chunking
Split long responses into multiple messages:

```bash
MQTT_MESSAGE_MAX_LENGTH=280  # Twitter-like limit

# Long response becomes:
# 1/3: This is a very long response that has been split into multiple
# 2/3: chunks to fit within the configured message length limit. Each
# 3/3: chunk is numbered so you know the sequence and total count.
```

### TLS/SSL Support
```bash
MQTT_USE_TLS=true
MQTT_TLS_CA_CERTS=/certs/ca.crt
MQTT_TLS_CERTFILE=/certs/client.crt
MQTT_TLS_KEYFILE=/certs/client.key
```

### Response Filtering
```bash
MQTT_TRIGGER_PATTERN=@ai|@bot|@assistant  # Multiple triggers
MQTT_SANITIZE_RESPONSE=true              # Remove emojis/formatting
```

## Alternative Installation

For development or if you prefer not using Docker:

```bash
# Install from PyPI
pip install mqtt-llm

# Or install from source
git clone https://github.com/mqtt-llm/mqtt-llm.git
cd mqtt-llm && pip install -e .
```

## Configuration Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `MQTT_BROKER` | MQTT broker address (required) | `mqtt.example.com` |
| `MQTT_SUBSCRIBE_TOPIC` | Topic to listen for messages | `chat/input` |
| `MQTT_SUBSCRIBE_PATH` | JSONPath to extract text | `$.message.text` |
| `MQTT_PUBLISH_TOPIC` | Topic for responses | `chat/output` |
| `MQTT_PUBLISH_TEMPLATE` | Response format template | `{"text": "{response}"}` |
| `MQTT_TRIGGER_PATTERN` | Pattern to trigger AI | `@ai` |
| `MQTT_MESSAGE_MAX_LENGTH` | Max length for chunking | `280` |
| `OPENAI_API_URL` | API endpoint URL | `https://openrouter.ai/api` |
| `OPENAI_API_KEY` | API authentication key | `sk-your-key` |
| `OPENAI_MODEL` | Model to use | `llama3` |
| `OPENAI_TEMPERATURE` | Response creativity (0-2) | `0.7` |
| `OPENAI_MAX_TOKENS` | Max response length | `1000` |

## Testing Your Setup

### 1. Dry Run
```bash
docker run --rm --env-file .env \
  ghcr.io/mqtt-llm/mqtt-llm:latest --dry-run
```

### 2. Send Test Message
```bash
# Publish test message to your MQTT broker
mosquitto_pub -h your-broker -t chat/input -m '{"text": "@ai Hello world"}'

# Watch for response
mosquitto_sub -h your-broker -t chat/output
```

### 3. Health Check
```bash
# Check logs for successful startup
docker logs mqtt-llm-container
```

## Troubleshooting

### Common Issues

**Connection Failed**
```bash
# Check MQTT broker connectivity
mosquitto_pub -h your-broker -t test -m "hello"

# Verify API endpoint
curl -s http://your-ollama:11434/v1/models
```

**No Response**
- Verify trigger pattern matches your message
- Check JSONPath extracts the right content
- Confirm API key and model name are correct

**JSON Parse Errors**
- Ensure publish template uses valid JSON syntax
- Test template with simple `{response}` first

### Debug Mode
```bash
LOG_LEVEL=DEBUG
OPENAI_SKIP_HEALTH_CHECK=false  # Enable API validation
```

## Contributing

We welcome contributions! See our [development guide](CLAUDE.md) for setup instructions.

## License

MIT License - see [LICENSE](LICENSE) file for details.
