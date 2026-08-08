# Q-SHIELD API (FastAPI) — uv workspace monorepo
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# System deps: compile qiskit-aer (no manylinux wheel for every arch/Python yet)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        ninja-build \
        gfortran \
        libopenblas-dev \
        liblapack-dev \
        libx11-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md ./
COPY packages ./packages
COPY backend ./backend
COPY configs ./configs

RUN uv sync --frozen --no-dev

EXPOSE 8000

# Mount artifacts/data at runtime (see docker-compose.yml)
CMD ["uvicorn", "qshield_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
