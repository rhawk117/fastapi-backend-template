import uuid
from contextvars import ContextVar

correlation_id: ContextVar[str | None] = ContextVar('correlation_id', default=None)


def generate_id(*, length: int = 32) -> str:
    base = uuid.uuid4().hex
    if length >= 32:
        return base

    return base[:length]
