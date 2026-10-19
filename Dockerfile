FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project

COPY . .
RUN uv sync --no-dev \
    && uv run dental pipeline \
    && uv run dental brief --offline

EXPOSE 8501
CMD ["uv", "run", "dental", "dashboard", "--server.address=0.0.0.0", "--server.headless=true"]
