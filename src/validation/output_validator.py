import logging
import json
from typing import Dict, List, Optional, Any
from outlines import models
from outlines import generate

from src.api.models import TransformerDefinition
from src.validation.transformers import apply_transformers


logger = logging.getLogger(__name__)


async def validate_output(
    text: str,
    schema: Dict[str, Any],
    transformers: Optional[List[TransformerDefinition]] = None,
) -> Dict[str, Any]:
    """
    Validate and transform LLM output using the given schema.

    Args:
        text: The text to validate
        schema: The JSON schema to validate against
        transformers: The transformers to apply to the validated output

    Returns:
        Dict[str, Any]: The validated and transformed output

    Raises:
        ValueError: If the output is invalid
    """
    try:
        try:
            # First try to parse as JSON directly
            output = json.loads(text)
            logger.debug("Output is valid JSON, parsing directly")
        except json.JSONDecodeError:
            logger.debug("Output is not valid JSON, using Outlines to structure")
            # Use Outlines to structure the text according to the schema
            output = _structure_with_outlines(text, schema)

        # Apply transformers if provided
        if transformers is not None:
            output = await apply_transformers(output, transformers)

        return output

    except Exception as e:
        logger.error(f"Error validating output: {str(e)}")
        raise ValueError(f"Error validating output: {str(e)}")


def _structure_with_outlines(text: str, schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Use Outlines to structure unstructured text according to a schema.

    Args:
        text: The text to structure
        schema: The JSON schema to structure according to

    Returns:
        Dict[str, Any]: The structured output

    Raises:
        ValueError: If the text cannot be structured
    """
    try:
        # Initialize Outlines with a model
        model = models.openai("gpt-3.5-turbo")

        # Create a JSON generator with the schema
        generator = generate.json(model, schema)

        # Generate structured output
        structured_output = generator(text)

        return structured_output

    except Exception as e:
        logger.error(f"Error structuring with Outlines: {str(e)}")
        raise ValueError(f"Error structuring with Outlines: {str(e)}")
