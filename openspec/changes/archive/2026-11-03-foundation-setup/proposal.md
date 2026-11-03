# Proposal: foundation-setup (C-01)

## Why

C-05 está completo (C-05a a C-05d, 199 tests): el dominio puro de la agenda existe, pero el repositorio todavía no tiene **nada que corra como aplicación**. No hay FastAPI, ni configuración, ni Docker, ni frontend, ni chequeos de calidad automáticos. C-02 (base de datos), C-03 (login) y todo el resto del camino crítico necesitan un esqueleto común donde enchufarse. C-01 arma ese esqueleto **extendiendo** lo que dejó C-05a, sin rehacerlo, y cierra los pendientes de calidad arrastrados (ruff y mypy sin configurar, avisos y errores de tipo preexistentes).

Evidencia del estado actual (inspección del repo):

- `backend/` tiene `pyproject.toml` (solo `tzdata` y `pytest` como dependencia de desarrollo), `app/{core,domain,infrastructure/in_memory}`, `tests/{unit,contract}` y `scripts/demo_turnos.py`. **No existen** `app/api/`, `app/application/`, `app/core/config.py`, `app/core/errors.py`, `alembic/` ni `backend/Dockerfile`.
- Los errores de dominio (`SlotTakenError`, `AppointmentNotFoundError`) viven en `domain/appointments/errors.py` y heredan directo de `Exception`, sin una base común.
- En la raíz **no existen** `docker-compose.yml`, `.env.example` ni `.gitignore` (solo `backend/.gitignore`). **No existe** `frontend/`.
- `ruff` y `mypy` no están en las dependencias ni configurados; quedan 3 avisos de ruff (UP017 en `app/core/timezone.py`, TRY004 en `slots.py` y `eligibility.py`) y 37 errores de `mypy --strict app tests` (anotaciones faltantes en `tests/unit/domain/appointments/helpers.py` y `test_compute_slots.py`).
- Intérpretes locales: `python` del sistema es 3.11.9 (por debajo de `requires-python >=3.12`); el `.venv` de `backend/` usa 3.13. Docker **no está instalado** en esta máquina.

## What Changes

- **Configuración validada** (`app/core/config.py`, Pydantic Settings): lee todas las variables de `08_arquitectura_propuesta.md` §Variables de entorno; la API, el worker y el beat no arrancan si falta una obligatoria o es inválida (zona horaria inexistente, clave JWT corta, algoritmo distinto de HS256). Se carga a demanda, de modo que los tests de dominio no necesitan variables de entorno.
- **`.env.example`** en la raíz con todas las variables y valores de ejemplo sin secretos reales; `.gitignore` raíz que ignora `.env`, `node_modules/`, `dist/` y cachés. Ninguna variable secreta lleva prefijo `VITE_` y el contenedor del frontend solo recibe `VITE_API_URL` (regla dura 5).
- **API mínima**: `app/main.py` (FastAPI) con CORS limitado a `CORS_ORIGINS`, router `/api/v1` y `GET /api/v1/health` (liveness, sin datos internos).
- **Modelo de errores** (`app/core/errors.py`): base `DomainError` con `code`; los errores de dominio existentes pasan a heredarla sin cambiar su comportamiento; la API traduce cualquier `DomainError` a una respuesta JSON uniforme.
- **Capas vacías listas**: `app/api/`, `app/application/`, `app/infrastructure/{db,email,tasks}/`, `alembic/` configurado (lee `DATABASE_URL`, sin migraciones: llegan en C-02), `tests/integration/` con marca `integration`.
- **App Celery mínima** (`app/infrastructure/tasks/celery_app.py`): broker `REDIS_URL`, `timezone` = `CLINIC_TIMEZONE`, `enable_utc = True`, sin tareas (C-11/C-12). Sujeta a la confirmación de la cátedra (DD-10, ver P-1 del design).
- **Docker**: `backend/Dockerfile` (Python 3.12), `frontend/Dockerfile` (Node LTS) y `docker-compose.yml` con `db`, `redis`, `api`, `worker`, `beat`, `frontend` y `mailpit`; `docker compose up` levanta los siete y falla con un mensaje claro si no existe `.env`.
- **Frontend**: scaffold React + TypeScript estricto + Vite + Vitest + ESLint (`no-explicit-any` como error), con una pantalla mínima que muestra el estado de la API consultando `/health`.
- **Calidad**: ruff (lint y formato) y mypy `--strict` en `app` y `tests`; se corrige UP017, TRY003/TRY004 quedan como excepción justificada por DD-18 y se anotan los tests previos. En el frontend: `tsc --noEmit`, ESLint y Vitest.
- **Documentación**: README con cómo levantar todo con Docker, cómo correr los tests dentro del contenedor (Python 3.12) y localmente.

No incluye: modelos, migraciones ni seed (C-02); login, JWT y `require_role` (C-03); tareas de email y recordatorio (C-11/C-12); pantallas de negocio del frontend (C-06, C-09, C-10); build de producción, HTTPS y CI (C-13); elegir el proveedor SMTP gratuito (SU-02, queda registrado como riesgo para C-11).

## Capabilities

### New Capabilities
- `runtime-configuration`: carga y validación de la configuración desde variables de entorno, contrato de `.env.example` y separación de secretos entre backend y frontend.
- `api-health`: aplicación FastAPI base, prefijo `/api/v1`, CORS y endpoint de salud.
- `error-model`: base común de errores de dominio con código y su traducción uniforme a respuestas HTTP.
- `local-environment`: entorno Docker Compose de los siete servicios, imágenes de backend y frontend, y la app Celery mínima de worker y beat.
- `quality-checks`: chequeos automáticos de backend (pytest, ruff, mypy estricto) y frontend (Vitest, typecheck, ESLint) y su forma de ejecución.
- `frontend-shell`: SPA React + TypeScript + Vite mínima que lee la URL de la API desde `VITE_API_URL` y muestra el estado de la API.

### Modified Capabilities
- (ninguna) Los errores `SlotTakenError` y `AppointmentNotFoundError` cambian de clase base pero conservan código, mensaje y atributos; los escenarios de `appointment-repository` no cambian.

## Impact

- **Código nuevo**: `backend/app/{main.py,api/,application/}`, `backend/app/core/{config.py,errors.py}`, `backend/app/infrastructure/{db,email,tasks}/`, `backend/alembic/`, `backend/Dockerfile`, `frontend/` completo, `docker-compose.yml`, `.env.example`, `.gitignore` raíz.
- **Código tocado (sin cambio de comportamiento)**: `app/core/timezone.py` (UP017), `app/domain/appointments/errors.py` (base `DomainError`), anotaciones de tipo en `tests/unit/domain/appointments/helpers.py` y `test_compute_slots.py`.
- **Dependencias**: runtime `fastapi`, `uvicorn[standard]`, `pydantic-settings`, `sqlalchemy`, `alembic`, `psycopg[binary]`, `celery[redis]`; desarrollo `ruff`, `mypy`, `httpx`. Frontend: `react`, `vite`, `typescript`, `vitest`, `@testing-library/react`, `eslint`, `typescript-eslint`.
- **Reglas del proyecto**: el endpoint de salud sería la segunda excepción a la regla dura 4 (JWT en todo endpoint salvo login); queda pendiente de confirmar (P-2 del design) y, si se acepta, hay que actualizar `CLAUDE.md`/`AGENTS.md`.
- **Entorno**: hace falta Docker Desktop instalado para verificar `docker compose up` y correr los tests en Python 3.12 (hoy no está en la máquina de desarrollo).
