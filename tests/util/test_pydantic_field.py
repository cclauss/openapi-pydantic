from typing import Dict, List, Union

from pydantic import BaseModel, Field
from typing_extensions import Literal

from openapi_pydantic import (
    Discriminator,
    Info,
    MediaType,
    OpenAPI,
    Operation,
    PathItem,
    Reference,
    RequestBody,
    Response,
    Schema,
)
from openapi_pydantic.compat import (
    DEFS_KEY,
    PYDANTIC_MINOR_VERSION,
    PYDANTIC_V2,
    models_json_schema,
    v1_schema,
)
from openapi_pydantic.util import PydanticSchema, construct_open_api_with_schema_class


class DataAModel(BaseModel):
    kind: Literal["a"]


class DataBModel(BaseModel):
    kind: Literal["b"]


class RequestModel(BaseModel):
    data: Union[DataAModel, DataBModel] = Field(discriminator="kind")


def construct_base_open_api() -> OpenAPI:
    return OpenAPI(
        info=Info(
            title="My own API",
            version="v0.0.1",
        ),
        paths={
            "/ping": PathItem(
                post=Operation(
                    requestBody=RequestBody(
                        content={
                            "application/json": MediaType(
                                media_type_schema=PydanticSchema(
                                    schema_class=RequestModel
                                )
                            )
                        }
                    ),
                    responses={"200": Response(description="pong")},
                )
            )
        },
    )


def test_pydantic_discriminator_schema_generation() -> None:
    """https://github.com/kuimono/openapi-schema-pydantic/issues/8."""
    a_kind: Dict[str, Union[str, List[str]]] = {"title": "Kind", "type": "string"}
    b_kind: Dict[str, Union[str, List[str]]] = {"title": "Kind", "type": "string"}

    if PYDANTIC_V2:
        _key_map, json_schema = models_json_schema([(RequestModel, "validation")])
        # In Pydantic v2, string literal types are mapped to consts.
        a_kind["const"] = "a"
        b_kind["const"] = "b"
        if PYDANTIC_MINOR_VERSION < 10:
            # Prior to 2.10, string literal types are also mapped to enums with a
            # single entry.
            a_kind["enum"] = ["a"]
            b_kind["enum"] = ["b"]
    else:
        json_schema = v1_schema([RequestModel])
        # In Pydantic v1, string literal types are mapped to enums with a single entry.
        a_kind["enum"] = ["a"]
        b_kind["enum"] = ["b"]

    assert json_schema == {
        DEFS_KEY: {
            "DataAModel": {
                "properties": {
                    "kind": a_kind,
                },
                "required": ["kind"],
                "title": "DataAModel",
                "type": "object",
            },
            "DataBModel": {
                "properties": {
                    "kind": b_kind,
                },
                "required": ["kind"],
                "title": "DataBModel",
                "type": "object",
            },
            "RequestModel": {
                "properties": {
                    "data": {
                        "oneOf": [
                            {"$ref": f"#/{DEFS_KEY}/DataAModel"},
                            {"$ref": f"#/{DEFS_KEY}/DataBModel"},
                        ],
                        "discriminator": {
                            "mapping": {
                                "a": f"#/{DEFS_KEY}/DataAModel",
                                "b": f"#/{DEFS_KEY}/DataBModel",
                            },
                            "propertyName": "kind",
                        },
                        "title": "Data",
                    }
                },
                "required": ["data"],
                "title": "RequestModel",
                "type": "object",
            },
        }
    }


def test_pydantic_discriminator_openapi_generation() -> None:
    """https://github.com/kuimono/openapi-schema-pydantic/issues/8."""
    open_api = construct_open_api_with_schema_class(construct_base_open_api())
    assert open_api.components is not None
    assert open_api.components.schemas is not None
    json_schema = open_api.components.schemas["RequestModel"]
    assert json_schema.properties == {
        "data": Schema(
            oneOf=[
                Reference(
                    **{
                        "$ref": "#/components/schemas/DataAModel",
                        "summary": None,
                        "description": None,
                    }
                ),
                Reference(
                    **{
                        "$ref": "#/components/schemas/DataBModel",
                        "summary": None,
                        "description": None,
                    }
                ),
            ],
            title="Data",
            discriminator=Discriminator(
                propertyName="kind",
                mapping={
                    "a": "#/components/schemas/DataAModel",
                    "b": "#/components/schemas/DataBModel",
                },
            ),
        )
    }
