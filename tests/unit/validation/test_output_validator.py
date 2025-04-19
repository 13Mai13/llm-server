import pytest
from unittest.mock import patch, MagicMock
from src.validation.output_validator import (
    validate_output,
    _structure_with_outlines,
)
from src.api.models import TransformerDefinition


@pytest.mark.asyncio
async def test_validate_output_with_valid_json():
    """Test validate_output with valid JSON input."""
    text = '{"name": "John", "age": 30}'
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }

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

    with patch(
        "src.validation.output_validator._structure_with_outlines"
    ) as mock_structure:
        mock_structure.return_value = {"name": "John", "age": 30}
        result = await validate_output(text, schema)
        assert result == {"name": "John", "age": 30}
        mock_structure.assert_called_once_with(text, schema)


@pytest.mark.asyncio
async def test_validate_output_with_transformers():
    """Test validate_output with transformers."""
    text = '{"name": "John", "age": 30}'
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }
    transformers = [TransformerDefinition(name="lowercase_strings", config={})]

    with patch("src.validation.output_validator.apply_transformers") as mock_transform:
        mock_transform.return_value = {"name": "john", "age": 30}
        result = await validate_output(text, schema, transformers)
        assert result == {"name": "john", "age": 30}
        mock_transform.assert_called_once_with(
            {"name": "John", "age": 30}, transformers
        )


@pytest.mark.asyncio
async def test_validate_output_with_invalid_json():
    """Test validate_output with invalid JSON input."""
    text = "invalid json"
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }

    with pytest.raises(ValueError):
        await validate_output(text, schema)


def test_structure_with_outlines():
    """Test _structure_with_outlines function."""
    text = "The person's name is John and he is 30 years old."
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }

    with patch("outlines.models.openai") as mock_model:
        mock_generator = MagicMock()
        mock_generator.return_value = {"name": "John", "age": 30}
        mock_model.return_value = mock_generator

        with patch("outlines.generate.json") as mock_json:
            mock_json.return_value = mock_generator
            result = _structure_with_outlines(text, schema)
            assert result == {"name": "John", "age": 30}
            mock_json.assert_called_once_with(mock_model.return_value, schema)
