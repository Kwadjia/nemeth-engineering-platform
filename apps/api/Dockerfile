FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first so source changes do not invalidate the layer.
COPY pyproject.toml README.md ./
RUN mkdir -p nemeth && printf '__version__ = "0.0.0"\n' > nemeth/__init__.py \
    && pip install -e ".[dev]"

COPY . .
RUN pip install -e ".[dev]"

EXPOSE 8000
CMD ["uvicorn", "nemeth.main:app", "--host", "0.0.0.0", "--port", "8000"]
