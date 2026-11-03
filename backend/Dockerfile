# Imagen de desarrollo del backend (D-5/D-6). C-13 define una imagen de produccion sin extras de dev.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN useradd --create-home --uid 1000 app
WORKDIR /app

# Dependencias primero para aprovechar la cache de capas.
COPY pyproject.toml ./
COPY app/__init__.py app/__init__.py
RUN pip install -e ".[dev]"

COPY . .
RUN chown -R app:app /app
USER app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
