import logging
from typing import Dict, List, Any, Optional, Callable, Awaitable
import re

from src.api.models import TransformerDefinition


logger = logging.getLogger(__name__)

# Type definitions
TransformerFunc = Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[Dict[str, Any]]]


# Registry of transformers
_transformers: Dict[str, TransformerFunc] = {}


def register_transformer(name: str) -> Callable[[TransformerFunc], TransformerFunc]:
    """
    Decorator to register a transformer function.

    Args:
        name: The name of the transformer

    Returns:
        Callable: The decorator function
    """

    def decorator(func: TransformerFunc) -> TransformerFunc:
        _transformers[name] = func
        logger.info(f"Registered transformer: {name}")
        return func

    return decorator


async def apply_transformers(
    data: Dict[str, Any],
    transformers: List[TransformerDefinition],
) -> Dict[str, Any]:
    """
    Apply a list of transformers to data.

    Args:
        data: The data to transform
        transformers: The transformers to apply

    Returns:
        Dict[str, Any]: The transformed data

    Raises:
        ValueError: If a transformer is not found
    """
    result = data

    for transformer_def in transformers:
        transformer_name = transformer_def.name
        transformer_config = transformer_def.config or {}

        if transformer_name not in _transformers:
            logger.error(f"Transformer not found: {transformer_name}")
            raise ValueError(f"Transformer not found: {transformer_name}")

        transformer = _transformers[transformer_name]
        result = await transformer(result, transformer_config)

    return result


# Built-in transformers


@register_transformer("lowercase_strings")
async def lowercase_strings(
    data: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Transform all string values to lowercase.

    Args:
        data: The data to transform
        config: Configuration for the transformer

    Returns:
        Dict[str, Any]: The transformed data
    """
    result = {}

    def _process_value(value: Any) -> Any:
        if isinstance(value, str):
            return value.lower()
        elif isinstance(value, list):
            return [_process_value(item) for item in value]
        elif isinstance(value, dict):
            return {k: _process_value(v) for k, v in value.items()}
        else:
            return value

    for key, value in data.items():
        result[key] = _process_value(value)

    return result


@register_transformer("remove_whitespace")
async def remove_whitespace(
    data: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Remove extra whitespace from string values.

    Args:
        data: The data to transform
        config: Configuration for the transformer

    Returns:
        Dict[str, Any]: The transformed data
    """
    result = {}

    def _process_value(value: Any) -> Any:
        if isinstance(value, str):
            # Replace multiple spaces with a single space
            value = re.sub(r"\s+", " ", value)
            # Trim leading/trailing whitespace
            return value.strip()
        elif isinstance(value, list):
            return [_process_value(item) for item in value]
        elif isinstance(value, dict):
            return {k: _process_value(v) for k, v in value.items()}
        else:
            return value

    for key, value in data.items():
        result[key] = _process_value(value)

    return result


@register_transformer("format_dates")
async def format_dates(
    data: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Format date strings according to a specified format.

    Args:
        data: The data to transform
        config: Configuration for the transformer
          - format: The format string (e.g. "%Y-%m-%d")
          - fields: List of field names to format

    Returns:
        Dict[str, Any]: The transformed data
    """
    import datetime

    result = data.copy()
    date_format = config.get("format", "%Y-%m-%d")
    fields = config.get("fields", [])

    if not fields:
        return result

    def _try_parse_date(value: str) -> Optional[datetime.datetime]:
        """Try to parse a date string in common formats."""
        formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%b %d, %Y",
            "%B %d, %Y",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
        ]

        for fmt in formats:
            try:
                return datetime.datetime.strptime(value, fmt)
            except ValueError:
                continue

        return None

    for field in fields:
        if field in result and isinstance(result[field], str):
            date_obj = _try_parse_date(result[field])
            if date_obj:
                result[field] = date_obj.strftime(date_format)

    return result


@register_transformer("extract_entities")
async def extract_entities(
    data: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Extract entities from text using regular expressions.

    Args:
        data: The data to transform
        config: Configuration for the transformer
          - patterns: Dict mapping entity names to regex patterns
          - source_field: Field containing text to extract from
          - target_field: Field to store extracted entities

    Returns:
        Dict[str, Any]: The transformed data
    """
    result = data.copy()
    patterns = config.get("patterns", {})
    source_field = config.get("source_field")
    target_field = config.get("target_field", "entities")

    if (
        not source_field
        or source_field not in result
        or not isinstance(result[source_field], str)
    ):
        return result

    text = result[source_field]
    entities = {}

    for entity_type, pattern in patterns.items():
        matches = re.findall(pattern, text)
        if matches:
            entities[entity_type] = matches

    result[target_field] = entities
    return result


@register_transformer("summarize")
async def summarize(
    data: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Add a summary field based on specified fields.

    Args:
        data: The data to transform
        config: Configuration for the transformer
          - fields: List of fields to include in summary
          - target_field: Field to store summary
          - max_length: Maximum length of summary

    Returns:
        Dict[str, Any]: The transformed data
    """
    result = data.copy()
    fields = config.get("fields", [])
    target_field = config.get("target_field", "summary")
    max_length = config.get("max_length", 100)

    summary_parts = []

    for field in fields:
        if field in result and isinstance(result[field], str):
            summary_parts.append(result[field])

    if summary_parts:
        summary = " ".join(summary_parts)

        # Truncate to max_length
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."

        result[target_field] = summary

    return result


@register_transformer("filter_fields")
async def filter_fields(
    data: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Filter the data to include only specified fields.

    Args:
        data: The data to transform
        config: Configuration for the transformer
          - fields: List of fields to include

    Returns:
        Dict[str, Any]: The transformed data
    """
    fields = config.get("fields", [])

    if not fields:
        return data

    return {k: v for k, v in data.items() if k in fields}
