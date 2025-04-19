import logging
import uuid
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, UTC

from src.api.models import SchemaDefinition


logger = logging.getLogger(__name__)


class SchemaRegistry:
    """
    Registry for JSON schemas used in structured output validation.

    This class manages the registration, retrieval, and validation of JSON schemas.
    """

    def __init__(self):
        """Initialize the schema registry."""
        self.schemas: Dict[str, Dict[str, Any]] = {}
        self.schema_definitions: Dict[str, SchemaDefinition] = {}
        logger.info("Schema registry initialized")

    async def register_schema(
        self,
        schema: Dict[str, Any],
        name: str,
        description: Optional[str] = None,
        schema_id: Optional[str] = None,
    ) -> str:
        """
        Register a schema.

        Args:
            schema: The JSON schema
            name: The name of the schema
            description: The description of the schema
            schema_id: The ID of the schema (optional, will be generated if not provided)

        Returns:
            str: The ID of the registered schema

        Raises:
            ValueError: If the schema is invalid
        """
        try:
            json.dumps(schema)
        except Exception as e:
            logger.error(f"Invalid schema: {str(e)}")
            raise ValueError(f"Invalid schema: {str(e)}")

        # Generate an ID if not provided
        if not schema_id:
            schema_id = str(uuid.uuid4())

        # Store the schema
        now = datetime.now(UTC).isoformat()

        schema_def = SchemaDefinition(
            id=schema_id,
            name=name,
            description=description,
            json_schema=schema,
            created_at=now,
            updated_at=now,
        )

        self.schemas[schema_id] = schema
        self.schema_definitions[schema_id] = schema_def

        logger.info(f"Registered schema {schema_id}: {name}")

        return schema_id

    async def get_schema(self, schema_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a schema by ID.

        Args:
            schema_id: The ID of the schema

        Returns:
            Optional[Dict[str, Any]]: The schema, or None if not found
        """
        return self.schemas.get(schema_id)

    async def get_schema_definition(self, schema_id: str) -> Optional[SchemaDefinition]:
        """
        Get a schema definition by ID.

        Args:
            schema_id: The ID of the schema

        Returns:
            Optional[SchemaDefinition]: The schema definition, or None if not found
        """
        return self.schema_definitions.get(schema_id)

    async def list_schemas(self) -> List[SchemaDefinition]:
        """
        List all registered schemas.

        Returns:
            List[SchemaDefinition]: List of all registered schema definitions
        """
        return list(self.schema_definitions.values())

    async def delete_schema(self, schema_id: str) -> bool:
        """
        Delete a schema.

        Args:
            schema_id: The ID of the schema

        Returns:
            bool: True if the schema was deleted, False if it was not found
        """
        if schema_id in self.schemas:
            del self.schemas[schema_id]
            del self.schema_definitions[schema_id]
            logger.info(f"Deleted schema {schema_id}")
            return True

        return False

    async def update_schema(
        self,
        schema_id: str,
        schema: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[SchemaDefinition]:
        """
        Update a schema.

        Args:
            schema_id: The ID of the schema
            schema: The new schema (optional)
            name: The new name (optional)
            description: The new description (optional)

        Returns:
            Optional[SchemaDefinition]: The updated schema definition, or None if not found

        Raises:
            ValueError: If the schema is invalid
        """
        if schema_id not in self.schema_definitions:
            return None

        schema_def = self.schema_definitions[schema_id]

        if schema is not None:
            try:
                json.dumps(schema)
                self.schemas[schema_id] = schema
                schema_def.json_schema = schema
            except Exception as e:
                logger.error(f"Invalid schema: {str(e)}")
                raise ValueError(f"Invalid schema: {str(e)}")

        if name is not None:
            schema_def.name = name

        if description is not None:
            schema_def.description = description

        schema_def.updated_at = datetime.now(UTC).isoformat()

        logger.info(f"Updated schema {schema_id}")

        return schema_def


_schema_registry: Optional[SchemaRegistry] = None


def get_schema_registry() -> SchemaRegistry:
    """
    Get the global schema registry instance.

    Returns:
        SchemaRegistry: The schema registry
    """
    global _schema_registry

    if _schema_registry is None:
        _schema_registry = SchemaRegistry()

    return _schema_registry
