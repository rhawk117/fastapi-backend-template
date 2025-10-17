from typing import Any

import msgspec
from fastapi.responses import JSONResponse

from app.core.pydantic import BaseModel


class FasterJsonResponse(JSONResponse):
    """
    A faster JSON response class using msgspec for serialization
    msgspec is up to 3-10x faster than the standard json library
    which is used by FastAPI's default JSONResponse class and
    makes a significant difference for large payloads.
    """
    media_type = 'application/json'

    def render(self, content: Any) -> bytes:
        if isinstance(content, bytes):
            return content

        if isinstance(content, BaseModel):
            content = content.model_dump()

        return msgspec.json.encode(content)
