# Tasks: foundation-setup (C-01)

> Las tasks aplican las recomendaciones de P-1, P-2 y P-3 de `design.md`. Si el usuario responde distinto, actualizar specs, design y estas tasks antes de seguir (`/opsx:update`).
> Strict TDD: en cada task con código, test rojo → verde → triangular → refactor. Comandos de backend desde `backend/` con el `.venv` (Python 3.13) hasta que exista la imagen Docker; después también dentro del contenedor (Python 3.12).

## 0. Confirmaciones previas

- [x] 0.1 Confirmar con el usuario P-1 (Celery como esqueleto), P-2 (`/health` público) y P-3 (Docker Desktop) y registrar las respuestas en la sección de preguntas de `design.md`; verificar que ninguna queda marcada "pendiente"
- [x] 0.2 Si P-2 se acepta, actualizar la regla dura 4 en `CLAUDE.md` y `AGENTS.md` ("salvo el login y el chequeo de salud") y verificar que ambos archivos quedan con el mismo texto

## 1. Tooling de calidad del backend sobre el código existente

- [x] 1.1 Red de seguridad: correr `pytest` y registrar `199 passed` como línea de base
- [x] 1.2 Agregar a `[project.optional-dependencies].dev` `ruff`, `mypy` y `httpx` (con rangos de versión), e instalar con `pip install -e ".[dev]"`; verificar que `ruff --version` y `mypy --version` responden
- [x] 1.3 Agregar `[tool.ruff]` y `[tool.mypy]` según D-8 (select, `ignore = ["TRY003", "TRY004"]` con comentario que cita DD-18, `strict`, `files = ["app", "tests"]`); correr `ruff check .` y verificar que los únicos avisos previos son UP017 (los TRY004 quedan ignorados); si aparecen otros, corregirlos si son mecánicos o registrarlos en D-8 antes de seguir
- [x] 1.4 Corregir UP017 en `app/core/timezone.py` (`datetime.UTC`); verificar `ruff check .` sin avisos y los tests de `clinic-timezone` en verde
- [x] 1.5 Correr `ruff format .` y verificar `ruff format --check .` limpio y `pytest` sigue en 199
- [x] 1.6 Anotar `tests/unit/domain/appointments/helpers.py` y `test_compute_slots.py` (y lo que reste) hasta que `mypy` (estricto, app y tests) termine sin errores; verificar `pytest` en 199
- [x] 1.7 Escenario "Función sin anotar": comprobar a mano que una función sin anotar en `tests/` hace fallar `mypy` y revertirla; anotar el resultado en el informe de apply

## 2. Modelo de errores (`error-model`)

- [x] 2.1 TDD: tests de `DomainError` (código por defecto, subclase con código propio) y de que `SlotTakenError` / `AppointmentNotFoundError` pertenecen a la familia conservando código, mensaje y atributos; implementar `app/core/errors.py` (solo librería estándar) y cambiar la base de ambos errores; verificar tests nuevos y toda la batería de contrato en verde
- [x] 2.2 Verificar que `ValueError` de una función de dominio (por ejemplo `to_local` con instante sin zona) no es `DomainError` (escenario "Errores de programación fuera de la familia") y que `test_import_order.py` sigue en verde

## 3. Configuración (`runtime-configuration`)

- [x] 3.1 Agregar `pydantic-settings` a las dependencias e instalar; consultar en Context7 cómo parsear una lista separada por comas en un campo de `pydantic-settings` y registrar la decisión en D-2
- [x] 3.2 TDD de `app/core/config.py`: escenarios "Configuración completa", "Falta una variable obligatoria", "Clave JWT demasiado corta sin revelar su valor", "Zona horaria inexistente", "Algoritmo JWT no permitido", "Varios orígenes CORS" y "Credenciales SMTP vacías"; verificar con `pytest tests/unit/core/test_config.py`
- [x] 3.3 Verificar el escenario "Tests de dominio sin entorno": correr `pytest` con un entorno sin las variables del sistema y comprobar que pasa toda la batería
- [x] 3.4 `ruff check .`, `ruff format --check .` y `mypy` en verde

## 4. API base (`api-health`, traducción de `error-model`)

- [x] 4.1 Agregar `fastapi` y `uvicorn[standard]`; TDD con `TestClient` de `GET /api/v1/health` (200 `{"status": "ok"}` sin autorización), `POST` → 405, `GET /health` → 404, y la ruta presente en el esquema OpenAPI; implementar `app/main.py` (`create_app`), `app/api/router.py` y `app/api/health.py`
- [x] 4.2 TDD de CORS: origen permitido recibe `Access-Control-Allow-Origin`; origen no permitido no lo recibe
- [x] 4.3 TDD de `app/api/errors.py`: `APPOINTMENT_NOT_FOUND` → 404, `SLOT_TAKEN` → 409, código sin tabla → 400, excepción no de dominio → 500 sin traza ni mensaje interno (con una ruta de prueba registrada solo en el test)
- [x] 4.4 Escenario "Responde aunque la base no esté disponible": test con `DATABASE_URL` apuntando a un host inexistente que sigue devolviendo 200
- [x] 4.5 Crear `app/application/__init__.py` e `app/infrastructure/{db,email}/__init__.py` vacíos con docstring que diga qué change los llena; verificar `test_import_order.py` en verde y `ruff`/`mypy` limpios

## 5. Celery y Alembic

- [x] 5.1 Agregar `celery[redis]`; TDD de `app/infrastructure/tasks/celery_app.py`: broker igual a `REDIS_URL`, `timezone` igual a `CLINIC_TIMEZONE`, `enable_utc` verdadero y ninguna tarea propia registrada; override de mypy para `celery.*`; verificar tests, `ruff` y `mypy`
- [x] 5.2 Agregar `sqlalchemy`, `alembic` y `psycopg[binary]`; crear `alembic.ini` y `alembic/` con `env.py` que toma la URL de `get_settings()` y `versions/` vacío; verificar que `alembic --help` funciona y que `mypy` y `ruff` no se quejan de `env.py` (o excluirlo de mypy con justificación en D-8)
- [x] 5.3 Crear `tests/integration/` con `conftest.py`, registrar el marcador `integration` y `addopts = "-m 'not integration'"`; verificar con un test marcado temporal que no corre por defecto y sí con `pytest -m integration`, y quitarlo

## 6. `.env.example`, `.gitignore` y contrato del ejemplo

- [x] 6.1 Crear `.env.example` en la raíz con todas las variables de `08_arquitectura_propuesta.md` (secretos vacíos, credenciales de base ficticias, comentario de cómo generar `JWT_SECRET_KEY` con `python -c "import secrets; print(secrets.token_urlsafe(48))"`)
- [x] 6.2 Crear `.gitignore` raíz (`.env`, `node_modules/`, `dist/`, cachés de Python, ruff y mypy); verificar con `git check-ignore .env` y `git status` limpio de cachés
- [x] 6.3 TDD de `tests/unit/test_env_example.py` (D-7): toda variable de `Settings` figura, secretos vacíos, única variable `VITE_` es `VITE_API_URL`, y la función de nombres sensibles rechaza `VITE_JWT_SECRET_KEY`; el test falla si no encuentra el archivo
- [x] 6.4 Crear `backend/.dockerignore` (`.venv`, cachés) y verificar `pytest`, `ruff` y `mypy` completos en verde

## 7. Frontend (`frontend-shell`, parte frontend de `quality-checks`)

- [x] 7.1 Cargar `frontend-design:frontend-design` y `vercel-react-best-practices` (solo React); generar el scaffold Vite `react-ts` en `frontend/`, `tsconfig` estricto (D-9), Vitest + jsdom + Testing Library, ESLint con `no-explicit-any` como error; verificar `npm run typecheck`, `npm run lint` y `npm test` en verde con la app de ejemplo
- [x] 7.2 TDD de `src/config.ts`: URL configurada, barra final sin doble barra, URL faltante → `null`
- [x] 7.3 TDD de la pantalla inicial con `fetch` simulado: "Verificando…", "API disponible", "API no disponible" (error de red y 500) y "Falta configurar la URL de la API" sin solicitud; quitar el contenido de ejemplo de la plantilla
- [x] 7.4 Comprobar a mano que `const x: any = 1` hace fallar el lint y que asignar un número a un `string` hace fallar `typecheck`; revertir y anotar el resultado en el informe de apply

## 8. Docker (`local-environment`)

- [x] 8.1 Crear `backend/Dockerfile` (D-5, `python:3.12-slim`, usuario no root, `pip install -e ".[dev]"`) y `frontend/Dockerfile` (`node:22-alpine`, `npm ci`)
- [x] 8.2 Crear `docker-compose.yml` con los siete servicios según D-5 (healthchecks, `depends_on` con `service_healthy`, `env_file: .env` solo en api/worker/beat, frontend solo con `VITE_API_URL`, sin puertos de db y redis, montaje de `.env.example` en api); verificar que `docker compose config` resuelve sin errores con un `.env` de prueba
- [x] 8.3 Documentar en `README.md`: copiar `.env.example` a `.env` y generar la clave, `docker compose up`, URLs (8000, 5173, 8025), tests en el contenedor (`docker compose run --rm api pytest`, `ruff`, `mypy`), chequeos del frontend, y aclarar que el `python` 3.11 del sistema no sirve; actualizar la tabla "Qué hay en este repositorio", "Resultado esperado" y "Stack previsto"; verificar que cada comando documentado existe en los archivos creados

## 9. Verificación integrada con Docker (requiere P-3)

- [x] 9.1 Sin `.env`: `docker compose up` falla mencionando `.env`; con `.env` y `JWT_SECRET_KEY` vacía: `api` termina con error que menciona `JWT_SECRET_KEY` **Verificado 2026-11-03: sin .env falla mencionando .env; con la clave vacía worker y beat terminan con error y la api muestra el error pero no termina (--reload), ver spec local-environment**
- [x] 9.2 Con `.env` válido: `docker compose up -d`, los siete servicios en marcha, `db`/`redis`/`api` sanos, `GET http://localhost:8000/api/v1/health` → 200, frontend en `http://localhost:5173` muestra "API disponible", Mailpit en `http://localhost:8025`, log de `worker` listo y conectado a `redis`, `docker compose ps` sin puertos publicados para db y redis
- [x] 9.3 `docker compose config` muestra que el servicio `frontend` no tiene `JWT_SECRET_KEY`, `SMTP_PASSWORD`, `DATABASE_URL` ni `POSTGRES_PASSWORD`
- [x] 9.4 `docker compose run --rm api python --version` informa 3.12 y `docker compose run --rm api pytest`, `ruff check .`, `ruff format --check .` y `mypy` pasan dentro del contenedor
