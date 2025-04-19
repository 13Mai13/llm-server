import pytest
from src.validation.schema_registry import SchemaRegistry
from src.api.models import SchemaDefinition


@pytest.fixture
def schema_registry():
    """Create a fresh schema registry for each test."""
    return SchemaRegistry()


@pytest.fixture
def sample_schema():
    """Return a sample schema for testing."""
    return {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }


@pytest.mark.asyncio
async def test_register_schema(schema_registry, sample_schema):
    """Test registering a new schema."""
    schema_id = await schema_registry.register_schema(
        schema=sample_schema, name="test_schema", description="Test schema"
    )

    assert schema_id is not None
    assert schema_id in schema_registry.schemas
    assert schema_id in schema_registry.schema_definitions

    schema_def = schema_registry.schema_definitions[schema_id]
    assert schema_def.name == "test_schema"
    assert schema_def.description == "Test schema"
    assert schema_def.json_schema == sample_schema


@pytest.mark.asyncio
async def test_register_schema_with_id(schema_registry, sample_schema):
    """Test registering a schema with a specific ID."""
    schema_id = "test-id"
    result_id = await schema_registry.register_schema(
        schema=sample_schema,
        name="test_schema",
        description="Test schema",
        schema_id=schema_id,
    )

    assert result_id == schema_id
    assert schema_id in schema_registry.schemas
    assert schema_id in schema_registry.schema_definitions


@pytest.mark.asyncio
async def test_get_schema(schema_registry, sample_schema):
    """Test getting a schema by ID."""
    schema_id = await schema_registry.register_schema(
        schema=sample_schema, name="test_schema"
    )

    retrieved_schema = await schema_registry.get_schema(schema_id)
    assert retrieved_schema == sample_schema


@pytest.mark.asyncio
async def test_get_schema_not_found(schema_registry):
    """Test getting a non-existent schema."""
    retrieved_schema = await schema_registry.get_schema("non-existent")
    assert retrieved_schema is None


@pytest.mark.asyncio
async def test_get_schema_definition(schema_registry, sample_schema):
    """Test getting a schema definition by ID."""
    schema_id = await schema_registry.register_schema(
        schema=sample_schema, name="test_schema", description="Test schema"
    )

    schema_def = await schema_registry.get_schema_definition(schema_id)
    assert isinstance(schema_def, SchemaDefinition)
    assert schema_def.id == schema_id
    assert schema_def.name == "test_schema"
    assert schema_def.description == "Test schema"
    assert schema_def.json_schema == sample_schema


@pytest.mark.asyncio
async def test_list_schemas(schema_registry, sample_schema):
    """Test listing all schemas."""
    # Register multiple schemas
    await schema_registry.register_schema(schema=sample_schema, name="schema1")
    await schema_registry.register_schema(schema=sample_schema, name="schema2")

    schemas = await schema_registry.list_schemas()
    assert len(schemas) == 2
    assert all(isinstance(s, SchemaDefinition) for s in schemas)


@pytest.mark.asyncio
async def test_delete_schema(schema_registry, sample_schema):
    """Test deleting a schema."""
    schema_id = await schema_registry.register_schema(
        schema=sample_schema, name="test_schema"
    )

    assert await schema_registry.delete_schema(schema_id) is True
    assert schema_id not in schema_registry.schemas
    assert schema_id not in schema_registry.schema_definitions


@pytest.mark.asyncio
async def test_delete_schema_not_found(schema_registry):
    """Test deleting a non-existent schema."""
    assert await schema_registry.delete_schema("non-existent") is False


@pytest.mark.asyncio
async def test_update_schema(schema_registry, sample_schema):
    """Test updating a schema."""
    schema_id = await schema_registry.register_schema(
        schema=sample_schema, name="test_schema", description="old description"
    )

    new_schema = {
        "type": "object",
        "properties": {"title": {"type": "string"}, "content": {"type": "string"}},
        "required": ["title", "content"],
    }

    updated_def = await schema_registry.update_schema(
        schema_id=schema_id,
        schema=new_schema,
        name="updated_schema",
        description="new description",
    )

    assert updated_def is not None
    assert updated_def.json_schema == new_schema
    assert updated_def.name == "updated_schema"
    assert updated_def.description == "new description"
    assert updated_def.updated_at > updated_def.created_at
