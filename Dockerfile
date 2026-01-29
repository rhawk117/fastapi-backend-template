FROM ghcr.io/astral-sh/uv:python3.13-alpine AS builder

ARG APP_USER=nonroot

RUN apk add --no-cache \
    build-base pkgconfig libffi-dev openssl-dev musl-dev \
    rust cargo git curl bash postgresql-dev

RUN addgroup -S ${APP_USER} 2>/dev/null || true \
 && adduser  -S -D -H -G ${APP_USER} ${APP_USER} 2>/dev/null || true

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_TOOL_BIN_DIR=/usr/local/bin

RUN --mount=type=bind,source=pyproject.toml,target=/app/pyproject.toml,ro \
    --mount=type=bind,source=uv.lock,target=/app/uv.lock,ro \
    --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

FROM python:3.13-alpine AS runtime

ARG APP_USER=nonroot

RUN apk add --no-cache \
    bash ca-certificates tzdata libstdc++ libffi openssl postgresql-libs \
 && update-ca-certificates

RUN addgroup -S ${APP_USER} 2>/dev/null || true \
 && adduser  -S -D -H -G ${APP_USER} ${APP_USER} 2>/dev/null || true

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app


ENV VIRTUAL_ENV=/app/.venv \
    PATH=/app/.venv/bin:${PATH} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER ${APP_USER}
EXPOSE 8000

ENTRYPOINT ["python", "-m", "server.run"]