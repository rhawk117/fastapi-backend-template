import contextlib
import uuid
from collections.abc import Generator
from contextvars import ContextVar

correlation_id: ContextVar[str | None] = ContextVar('correlation_id', default=None)


def generate_id() -> str:
    return uuid.uuid4().hex


def get_correlation_id(*, default: str) -> str:
    return correlation_id.get() or default


@contextlib.contextmanager
def correlation(*, id: str | None = None) -> Generator[str]:
    id = id or generate_id()

    correlation_token = correlation_id.set(id)
    try:
        yield id
    finally:
        correlation_id.reset(correlation_token)
