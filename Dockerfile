# Replication kit. Build and run `make all` against the committed raw snapshot.
#   docker build -t censorzero-v2 .
#   docker run --rm censorzero-v2 make verify
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-install-project

COPY . .
RUN uv sync --frozen

RUN apt-get update && apt-get install -y --no-install-recommends git make && rm -rf /var/lib/apt/lists/*

CMD ["make", "all"]
