import pytest
from unittest.mock import patch, MagicMock
from src.validation.output_validator import (
    validate_output,
    _structure_with_outlines,
)


@pytest.mark.asyncio
async def test_validate_output_with_valid_json():
    """Test validate_output with valid JSON input."""
    text = '{"name": "John", "age": 30}'
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }

    # Mock the OpenAI client
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"name": "John", "age": 30}'))]
    )

    with (
        patch("outlines.models.openai") as mock_openai,
        patch("outlines.generate.json") as mock_json,
    ):
        # Mock the OpenAI client
        mock_openai.return_value = mock_client

        # Mock the generator to return our test output
        mock_generator = MagicMock()
        mock_generator.return_value = {"name": "John", "age": 30}
        mock_json.return_value = mock_generator

        result = await validate_output(text, schema)
        assert result == {"name": "John", "age": 30}


@pytest.mark.asyncio
async def test_validate_output_with_unstructured_text():
    """Test validate_output with unstructured text input."""
    text = "The person's name is John and he is 30 years old."
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }

    # Mock the OpenAI client
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"name": "John", "age": 30}'))]
    )

    with (
        patch("outlines.models.openai") as mock_openai,
        patch("outlines.generate.json") as mock_json,
    ):
        # Mock the OpenAI client
        mock_openai.return_value = mock_client

        # Mock the generator to return our test output
        mock_generator = MagicMock()
        mock_generator.return_value = {"name": "John", "age": 30}
        mock_json.return_value = mock_generator

        result = await validate_output(text, schema)
        assert result == {"name": "John", "age": 30}


@pytest.mark.asyncio
async def test_validate_output_with_transformers():
    """Test output validation with transformers."""
    from src.validation.transformers import TransformerDefinition, _transformers
    from src.validation.output_validator import validate_output

    # Create a mock transformer function
    async def mock_transform_func(data: dict, config: dict) -> dict:
        return {"name": "john", "age": 30}

    # Register the mock transformer
    _transformers["test_transformer"] = mock_transform_func

    with (
        patch("outlines.models.openai") as mock_openai,
        patch("outlines.generate.json") as mock_json,
    ):
        # Mock the OpenAI model
        mock_model = MagicMock()
        mock_openai.return_value = mock_model

        # Mock the generator to return our test output
        mock_generator = MagicMock()
        mock_generator.return_value = {"name": "John", "age": 30}
        mock_json.return_value = mock_generator

        # Test with a transformer
        result = await validate_output(
            "Generate a person's information",
            {
                "type": "object",
                "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
                "required": ["name", "age"],
            },
            [TransformerDefinition(name="test_transformer", config={})],
        )
        assert result == {"name": "john", "age": 30}

        # Clean up the registered transformer
        del _transformers["test_transformer"]


@pytest.mark.asyncio
async def test_validate_output_with_invalid_json():
    """Test validate_output with invalid JSON input."""
    text = "invalid json"
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }

    with patch("outlines.generate.json") as mock_json:
        # Mock the generator to raise an exception
        mock_generator = MagicMock()
        mock_generator.side_effect = ValueError("Invalid JSON")
        mock_json.return_value = mock_generator

        with pytest.raises(ValueError):
            await validate_output(text, schema)


@pytest.mark.asyncio
async def test_structure_with_outlines():
    """Test structuring output with Outlines."""

    # Mock the Outlines OpenAI model
    mock_model = MagicMock()
    mock_model.return_value = {"name": "John", "age": 30}

    # Mock the Outlines JSON generator
    mock_generator = MagicMock()
    mock_generator.return_value = {"name": "John", "age": 30}

    with (
        patch("outlines.models.openai", return_value=mock_model) as mock_openai,
        patch("outlines.generate.json", return_value=mock_generator) as mock_json,
    ):
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name", "age"],
        }

        result = _structure_with_outlines("Generate a person's information", schema)
        assert result == {"name": "John", "age": 30}

        # Verify the mocks were called correctly
        mock_openai.assert_called_once_with("gpt-3.5-turbo")
        mock_json.assert_called_once_with(mock_model, schema)
        mock_generator.assert_called_once_with("Generate a person's information")
