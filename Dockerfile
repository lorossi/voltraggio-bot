FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
  UV_LINK_MODE=copy \
  UV_PYTHON_DOWNLOADS=never \
  PYTHONUNBUFFERED=1

WORKDIR /app

# install the dependencies first, so they are cached between builds
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --locked --no-install-project --no-default-groups

# then install the project itself
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --locked --no-default-groups

ENV PATH="/app/.venv/bin:$PATH"

# the settings live in a mounted volume, so they survive container rebuilds
CMD ["voltraggio-bot", "--settings", "data/settings.json"]
