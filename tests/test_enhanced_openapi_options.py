"""
Tests for enhanced OpenAPI schema options:
- Custom schema examples via Field
- Discriminator mappings for polymorphic models
- Deprecated flag propagation for schema fields
"""
from typing import Annotated, Literal

import pytest
from fastapi import Body, FastAPI, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field


def test_field_examples_in_schema():
    """Test that Field(examples=...) propagates to OpenAPI schema."""
    app = FastAPI()

    class Item(BaseModel):
        name: str = Field(examples=["test1", "test2"])
        price: float = Field(examples=[19.99, 29.99])

    @app.post("/items/")
    def create_item(item: Item):
        return item

    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    item_schema = schema["components"]["schemas"]["Item"]

    # Check that examples are in the schema properties
    assert item_schema["properties"]["name"]["examples"] == ["test1", "test2"]
    assert item_schema["properties"]["price"]["examples"] == [19.99, 29.99]


def test_field_deprecated_in_schema():
    """Test that Field(deprecated=True) propagates to OpenAPI schema."""
    app = FastAPI()

    class Item(BaseModel):
        name: str
        old_field: str = Field(deprecated=True)

    @app.post("/items/")
    def create_item(item: Item):
        return item

    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    item_schema = schema["components"]["schemas"]["Item"]

    # Check that deprecated is in the schema
    assert item_schema["properties"]["old_field"]["deprecated"] is True


def test_discriminator_mapping_in_schema():
    """Test that discriminator mapping is generated in OpenAPI schema."""
    app = FastAPI()

    class Cat(BaseModel):
        pet_type: Literal["cat"] = "cat"
        meows: int

    class Dog(BaseModel):
        pet_type: Literal["dog"] = "dog"
        barks: float

    Pet = Annotated[
        Annotated[Cat, Field(discriminator="pet_type")]
        | Annotated[Dog, Field(discriminator="pet_type")],
        Field(discriminator="pet_type"),
    ]

    @app.post("/pets/")
    def create_pet(pet: Pet):
        return pet

    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()

    # Find the Pet schema in the paths
    pet_schema = schema["paths"]["/pets/"]["post"]["requestBody"]["content"]["application/json"]["schema"]

    # Check discriminator is present
    assert "discriminator" in pet_schema
    assert pet_schema["discriminator"]["propertyName"] == "pet_type"
    assert "mapping" in pet_schema["discriminator"]
    assert "cat" in pet_schema["discriminator"]["mapping"]
    assert "dog" in pet_schema["discriminator"]["mapping"]


def test_discriminator_with_tag_mapping():
    """Test discriminator with Tag-based mapping."""
    from pydantic import Tag

    app = FastAPI()

    class Cat(BaseModel):
        pet_type: Literal["cat"] = "cat"
        meows: int

    class Dog(BaseModel):
        pet_type: Literal["dog"] = "dog"
        barks: float

    Pet = Annotated[
        Annotated[Cat, Tag("cat")] | Annotated[Dog, Tag("dog")],
        Field(discriminator="pet_type"),
    ]

    @app.post("/pets/")
    def create_pet(pet: Pet):
        return pet

    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    pet_schema = schema["paths"]["/pets/"]["post"]["requestBody"]["content"]["application/json"]["schema"]

    # Check discriminator mapping
    assert pet_schema["discriminator"]["mapping"] == {
        "cat": "#/components/schemas/Cat",
        "dog": "#/components/schemas/Dog",
    }


def test_query_parameter_examples():
    """Test that Query(examples=...) propagates to OpenAPI schema."""
    app = FastAPI()

    @app.get("/items/")
    def get_items(q: str = Query(examples=["query1", "query2"])):
        return {"q": q}

    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    param_schema = schema["paths"]["/items/"]["get"]["parameters"][0]

    assert param_schema["schema"]["examples"] == ["query1", "query2"]


def test_query_parameter_deprecated():
    """Test that Query(deprecated=True) propagates to OpenAPI schema."""
    app = FastAPI()

    @app.get("/items/")
    def get_items(
        q: str = Query(default="test", deprecated=True),
        new_q: str = Query(default="new"),
    ):
        return {"q": q, "new_q": new_q}

    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    params = schema["paths"]["/items/"]["get"]["parameters"]

    # Find the deprecated parameter
    deprecated_param = next(p for p in params if p["name"] == "q")
    assert deprecated_param["deprecated"] is True

    # Find the non-deprecated parameter
    non_deprecated_param = next(p for p in params if p["name"] == "new_q")
    assert "deprecated" not in non_deprecated_param


def test_body_examples():
    """Test that Body(examples=...) propagates to OpenAPI schema."""
    app = FastAPI()

    class Item(BaseModel):
        name: str

    @app.post("/items/")
    def create_item(item: Item = Body(examples=[{"name": "test"}])):
        return item

    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    body_schema = schema["paths"]["/items/"]["post"]["requestBody"]["content"]["application/json"]

    # Examples are inside the schema when using Body with a model
    assert body_schema["schema"]["examples"] == [{"name": "test"}]


def test_combined_examples_and_deprecated():
    """Test model with both examples and deprecated fields."""
    app = FastAPI()

    class Item(BaseModel):
        name: str = Field(examples=["test1", "test2"])
        price: float = Field(deprecated=True)
        description: str

    @app.post("/items/")
    def create_item(item: Item):
        return item

    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    item_schema = schema["components"]["schemas"]["Item"]

    # Check examples
    assert item_schema["properties"]["name"]["examples"] == ["test1", "test2"]

    # Check deprecated
    assert item_schema["properties"]["price"]["deprecated"] is True

    # Check description is not affected
    assert "deprecated" not in item_schema["properties"]["description"]


def test_discriminator_response_model():
    """Test discriminator in response model."""
    app = FastAPI()

    class Cat(BaseModel):
        pet_type: Literal["cat"] = "cat"
        meows: int

    class Dog(BaseModel):
        pet_type: Literal["dog"] = "dog"
        barks: float

    Pet = Annotated[
        Annotated[Cat, Field(discriminator="pet_type")]
        | Annotated[Dog, Field(discriminator="pet_type")],
        Field(discriminator="pet_type"),
    ]

    @app.get("/pets/{pet_id}", response_model=Pet)
    def get_pet(pet_id: str) -> Pet:
        if pet_id == "cat":
            return Cat(pet_type="cat", meows=5)
        return Dog(pet_type="dog", barks=3.0)

    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()

    # Check response schema
    response_schema = schema["paths"]["/pets/{pet_id}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]

    assert "discriminator" in response_schema
    assert response_schema["discriminator"]["propertyName"] == "pet_type"


def test_inline_model_examples():
    """Test inline model with examples."""
    app = FastAPI()

    @app.post("/items/")
    def create_item(
        item: Annotated[
            dict,
            Body(
                examples=[
                    {"name": "test1", "price": 10.0},
                    {"name": "test2", "price": 20.0},
                ]
            ),
        ]
    ):
        return item

    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    body_schema = schema["paths"]["/items/"]["post"]["requestBody"]["content"]["application/json"]

    # Examples are inside the schema for inline dict types
    assert body_schema["schema"]["examples"] == [
        {"name": "test1", "price": 10.0},
        {"name": "test2", "price": 20.0},
    ]
