"""Tests for message chunking functionality."""

from unittest.mock import Mock, patch

import pytest

from mqtt_llm.config import MQTTConfig
from mqtt_llm.mqtt_client import MQTTClient


def test_chunk_text_short_text() -> None:
    """Test that short text is not chunked."""
    config = MQTTConfig(
        broker="test",
        subscribe_topic="test/input",
        publish_topic="test/output",
        message_max_length=100,
    )
    client = MQTTClient(config)

    text = "Short message"
    result = client._chunk_text(text, 50)

    assert result == ["Short message"]


def test_chunk_text_long_text() -> None:
    """Test that long text is properly chunked."""
    config = MQTTConfig(
        broker="test",
        subscribe_topic="test/input",
        publish_topic="test/output",
        message_max_length=100,
    )
    client = MQTTClient(config)

    text = "This is a very long message that should be split into multiple chunks because it exceeds the maximum length limit."
    result = client._chunk_text(text, 30)

    assert len(result) > 1
    # Check that each chunk is within the limit
    for chunk in result:
        assert len(chunk) <= 30
    # Check that all text is preserved when joined
    assert "".join(
        chunk.strip() + " " for chunk in result
    ).strip() == text.replace("  ", " ")


def test_chunk_text_word_boundaries() -> None:
    """Test that chunking prefers word boundaries."""
    config = MQTTConfig(
        broker="test",
        subscribe_topic="test/input",
        publish_topic="test/output",
        message_max_length=100,
    )
    client = MQTTClient(config)

    text = "word1 word2 word3 word4 word5"
    result = client._chunk_text(text, 15)

    # Should prefer to break at spaces
    for chunk in result[:-1]:  # All but last chunk
        # Should not end with a partial word (unless forced)
        assert not (chunk.endswith("ord") or chunk.endswith("wo"))


def test_publish_response_no_chunking() -> None:
    """Test normal publish without chunking."""
    config = MQTTConfig(
        broker="test",
        subscribe_topic="test/input",
        publish_topic="test/output",
    )
    client = MQTTClient(config)
    client.connected = True

    mock_mqtt_client = Mock()
    mock_mqtt_client.publish.return_value.rc = 0  # Success
    client.client = mock_mqtt_client

    response = "Short response"
    client.publish_response(response)

    # Should call publish once
    mock_mqtt_client.publish.assert_called_once()
    call_args = mock_mqtt_client.publish.call_args[0]
    assert call_args[1] == "Short response"  # Should be the formatted response


def test_publish_response_with_chunking() -> None:
    """Test publish with chunking enabled."""
    config = MQTTConfig(
        broker="test",
        subscribe_topic="test/input",
        publish_topic="test/output",
        message_max_length=50,
    )
    client = MQTTClient(config)
    client.connected = True

    mock_mqtt_client = Mock()
    mock_mqtt_client.publish.return_value.rc = 0  # Success
    client.client = mock_mqtt_client

    # Long response that should be chunked
    response = "This is a very long response that should be split into multiple chunks because it exceeds the configured maximum length."
    client.publish_response(response)

    # Should call publish multiple times
    assert mock_mqtt_client.publish.call_count > 1

    # Check that each published message has the chunk prefix
    for call_args in mock_mqtt_client.publish.call_args_list:
        published_message = call_args[0][1]  # Second argument is the message
        # Should contain chunk prefix like "1/3: " or "2/3: "
        assert "/" in published_message and ": " in published_message


def test_publish_response_chunking_preserves_formatting() -> None:
    """Test that chunking works with template formatting."""
    config = MQTTConfig(
        broker="test",
        subscribe_topic="test/input",
        publish_topic="test/output",
        message_max_length=80,
        publish_template='{"response": "{response}", "type": "ai"}',
    )
    client = MQTTClient(config)
    client.connected = True

    mock_mqtt_client = Mock()
    mock_mqtt_client.publish.return_value.rc = 0  # Success
    client.client = mock_mqtt_client

    response = "This is a very long response that should be split into multiple chunks because it exceeds the maximum length limit."
    client.publish_response(response)

    # Should call publish multiple times
    assert mock_mqtt_client.publish.call_count > 1

    # Each message should be valid JSON with chunk prefix in the response field
    import json

    for call_args in mock_mqtt_client.publish.call_args_list:
        published_message = call_args[0][1]
        parsed = json.loads(published_message)
        assert "response" in parsed
        assert "/" in parsed["response"] and ": " in parsed["response"]
        assert parsed["type"] == "ai"


def test_config_validation_message_max_length() -> None:
    """Test configuration validation for message_max_length."""
    # Valid configuration
    config = MQTTConfig(
        broker="test",
        subscribe_topic="test/input",
        publish_topic="test/output",
        message_max_length=100,
    )
    assert config.message_max_length == 100

    # None should be allowed (no chunking)
    config = MQTTConfig(
        broker="test",
        subscribe_topic="test/input",
        publish_topic="test/output",
        message_max_length=None,
    )
    assert config.message_max_length is None

    # Invalid: zero or negative
    with pytest.raises(ValueError):
        MQTTConfig(
            broker="test",
            subscribe_topic="test/input",
            publish_topic="test/output",
            message_max_length=0,
        )

    with pytest.raises(ValueError):
        MQTTConfig(
            broker="test",
            subscribe_topic="test/input",
            publish_topic="test/output",
            message_max_length=-1,
        )


def test_chunking_with_very_small_limit() -> None:
    """Test chunking behavior with very small message limits."""
    config = MQTTConfig(
        broker="test",
        subscribe_topic="test/input",
        publish_topic="test/output",
        message_max_length=10,  # Very small limit that forces chunking but is too small for prefix
    )
    client = MQTTClient(config)
    client.connected = True

    mock_mqtt_client = Mock()
    mock_mqtt_client.publish.return_value.rc = 0
    client.client = mock_mqtt_client

    with patch.object(client.logger, "error") as mock_error:
        response = "This response is long enough to trigger chunking"
        client.publish_response(response)

        # Should log error about message being too small for chunking
        mock_error.assert_called_once()
        assert "too small for chunking" in str(mock_error.call_args)
