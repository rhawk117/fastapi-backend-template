from typing import Any, TypedDict

from fastapi import FastAPI
from fastapi.routing import APIRoute
from pydantic import BaseModel

from backend.schemas.errors import ErrorContent


class ExternalDocs(TypedDict):
    description: str
    url: str

def create_operation_id(route: APIRoute) -> str:
    """Generates a unique id for the route to help normalize
    the API service names.
    https://fastapi.tiangolo.com/advanced/generate-clients/#custom-generate-unique-id-function

    Returns:
        str -- the adjusted operation ID
    """
    return f'{route.tags[0]}-{route.name}'


def Problem(  # noqa: N802
    description: str,
    *,
    model: type[BaseModel] | None = None,
    headers: dict | None = None,
) -> dict:
    """
    Convience wrapper for annotating api routes with
    error response models for better OpenAPI spec generation.
    """
    if not model:
        model = ErrorContent

    return {
        'model': model,
        'description': description,
        'headers': headers or {},
    }


def Tag(  # noqa: N802
    name: str,
    tag_description: str,
    external_docs: ExternalDocs | None = None,
) -> dict[str, Any]:
    tag_metadata: dict[str, Any] = {'name': name, 'description': tag_description}
    if external_docs:
        tag_metadata.update({'externalDocs': dict(external_docs)})

    return tag_metadata




def get_openapi_schema(app: FastAPI) -> dict:
    """Normalizes service names from "userGetAllUsers" to "getAllUsers"

    Taken directly from
    https://fastapi.tiangolo.com/advanced/generate-clients/#preprocess-the-openapi-specification-for-the-client-generator
    """
    openapi_spec = app.openapi()

    path_schema: dict[str, dict] = openapi_spec['paths']
    for path_data in path_schema.values():
        for operation in path_data.values():
            tag = operation['tags'][0]
            operation_id = operation['operationId']
            to_remove = f'{tag}-'
            new_operation_id = operation_id[len(to_remove) :]
            operation['operationId'] = new_operation_id

    return openapi_spec
