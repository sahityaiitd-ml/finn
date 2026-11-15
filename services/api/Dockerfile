FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN useradd -m -u 1000 user
USER user
ENV PATH=/home/user/.local/bin:$PATH UV_PROJECT_ENVIRONMENT=/home/user/venv
WORKDIR /home/user/app
COPY --chown=user pyproject.toml uv.lock* ./
RUN uv sync --no-dev
COPY --chown=user . .
EXPOSE 7860
CMD ["/home/user/venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
