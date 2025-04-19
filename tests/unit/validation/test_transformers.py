import pytest
from src.validation.transformers import (
    apply_transformers,
    lowercase_strings,
    remove_whitespace,
    format_dates,
    summarize,
    filter_fields,
)
from src.api.models import TransformerDefinition


@pytest.mark.asyncio
async def test_apply_transformers():
    """Test applying multiple transformers."""
    data = {
        "name": "John Doe",
        "age": 30,
        "description": "  A test description  ",
        "date": "2023-01-01",
    }

    transformers = [
        TransformerDefinition(name="lowercase_strings", config={}),
        TransformerDefinition(name="remove_whitespace", config={}),
        TransformerDefinition(
            name="format_dates", config={"format": "%Y/%m/%d", "fields": ["date"]}
        ),
    ]

    result = await apply_transformers(data, transformers)

    assert result["name"] == "john doe"
    assert result["description"] == "a test description"
    assert result["date"] == "2023/01/01"
    assert result["age"] == 30


@pytest.mark.asyncio
async def test_apply_transformers_unknown_transformer():
    """Test applying an unknown transformer."""
    data = {"name": "John"}
    transformers = [TransformerDefinition(name="unknown_transformer", config={})]

    with pytest.raises(ValueError, match="Transformer not found"):
        await apply_transformers(data, transformers)


@pytest.mark.asyncio
async def test_lowercase_strings():
    """Test lowercase_strings transformer."""
    data = {
        "name": "John Doe",
        "age": 30,
        "nested": {"title": "Test Title", "items": ["Item 1", "Item 2"]},
    }

    result = await lowercase_strings(data, {})

    assert result["name"] == "john doe"
    assert result["age"] == 30
    assert result["nested"]["title"] == "test title"
    assert result["nested"]["items"] == ["item 1", "item 2"]


@pytest.mark.asyncio
async def test_remove_whitespace():
    """Test remove_whitespace transformer."""
    data = {
        "name": "  John  Doe  ",
        "description": "  A test  description  ",
        "nested": {"title": "  Test  Title  ", "items": ["  Item 1  ", "  Item 2  "]},
    }

    result = await remove_whitespace(data, {})

    assert result["name"] == "John Doe"
    assert result["description"] == "A test description"
    assert result["nested"]["title"] == "Test Title"
    assert result["nested"]["items"] == ["Item 1", "Item 2"]


@pytest.mark.asyncio
async def test_format_dates():
    """Test format_dates transformer."""
    data = {
        "date1": "2023-01-01",
        "date2": "01/01/2023",
        "date3": "Jan 1, 2023",
        "not_a_date": "not a date",
    }

    result = await format_dates(
        data,
        {"format": "%Y/%m/%d", "fields": ["date1", "date2", "date3", "not_a_date"]},
    )

    assert result["date1"] == "2023/01/01"
    assert result["date2"] == "2023/01/01"
    assert result["date3"] == "2023/01/01"
    assert result["not_a_date"] == "not a date"


@pytest.mark.asyncio
async def test_summarize():
    """Test summarize transformer."""
    data = {
        "title": "Test Title",
        "content": "This is a test content",
        "author": "John Doe",
        "date": "2023-01-01",
    }

    result = await summarize(
        data,
        {"fields": ["title", "content"], "target_field": "summary", "max_length": 30},
    )

    assert "summary" in result
    assert len(result["summary"]) <= 33  # Because you add ... to the end of the summary
    assert "Test Title" in result["summary"]
    assert "This is a test" in result["summary"]


@pytest.mark.asyncio
async def test_filter_fields():
    """Test filter_fields transformer."""
    data = {
        "name": "John",
        "age": 30,
        "email": "john@example.com",
        "phone": "123-456-7890",
    }

    result = await filter_fields(data, {"fields": ["name", "age"]})

    assert set(result.keys()) == {"name", "age"}
    assert result["name"] == "John"
    assert result["age"] == 30
