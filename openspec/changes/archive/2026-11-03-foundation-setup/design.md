# Design: foundation-setup (C-01)

## Context

Motivación, alcance y evidencia del estado actual: ver `proposal.md`. Requisitos: ver `specs/runtime-configuration`, `specs/api-health`, `specs/error-model`, `specs/local-environment`, `specs/quality-checks` y `specs/frontend-shell`.

Lo que condiciona el enfoque (verificado en el repo):

- El esqueleto de C-05 (`backend/app/{core,domain,infrastructure/in_memory}`, `tests/{unit,contract}`) ya funciona con 199 tests y **no se reorganiza**: C-01 agrega carpetas y archivos al lado.
- `domain/` importa `app.core.timezone` (DD-20). `app/core/` es por lo tanto una capa compartida que no puede importar FastAPI, SQLAlchemy, Celery ni Redis en los módulos que usa el dominio (regla dura 2). `core/config.py` sí usa Pydantic Settings, pero el dominio nunca lo importa.
- `tests/contract/test_import_order.py` importa cada paquete en un intérprete nuevo: ningún paquete nuevo puede romper esa prueba.
- La convención DD-18 (entrada inválida del llamador → `ValueError`) choca con la regla TRY004 de ruff, que pide `TypeError` tras un `isinstance`.
- Python local: 3.11.9 en el sistema y 3.13 en `backend/.venv`; el proyecto exige `>=3.12`. Docker no está instalado en la máquina de desarrollo.
- Governance BAJO: decisiones técnicas autónomas; las que cambian el stack o contradicen la KB quedan como preguntas al usuario (sección final).

## Goals / Non-Goals

**Goals:**

- Que C-02 pueda escribir modelos y migraciones, y C-03 su login, sin tocar Docker, configuración ni tooling.
- Que `docker compose up` sea el único paso para levantar todo, y un comando más para correr los tests en Python 3.12.
- Que lint, formato y tipos estrictos queden en verde desde ahora, para que cada change siguiente solo tenga que mantenerlos.
- Cero cambios de comportamiento en las 10 capabilities archivadas.

**Non-Goals:**

- Readiness (chequear base y Redis desde `/health`): la API no usa la base hasta C-02. Se agregará un endpoint separado si C-13 lo necesita.
- Build de producción del frontend, servidor estático, HTTPS y CI (C-13).
- Lockfile de Python: se usan rangos de versión en `pyproject.toml` (el frontend sí tendrá `package-lock.json`, que npm genera solo).
- Hot reload garantizado en Windows con volúmenes montados (se configura, pero no se promete).

## Decisions

### D-1 — Estructura que se agrega (sin mover nada)

```
backend/
├── app/
│   ├── main.py                      # crea la app FastAPI (create_app) e incluye routers
│   ├── api/
│   │   ├── router.py                # APIRouter con prefijo /api/v1
│   │   ├── health.py                # GET /health
│   │   └── errors.py                # handlers: DomainError → JSON; Exception → 500
│   ├── application/__init__.py      # vacío (C-08)
│   ├── core/
│   │   ├── config.py                # Settings + get_settings() con lru_cache
│   │   └── errors.py                # DomainError
│   └── infrastructure/
│       ├── db/__init__.py           # vacío (C-02)
│       ├── email/__init__.py        # vacío (C-11)
│       └── tasks/celery_app.py      # app Celery sin tareas
├── alembic/ + alembic.ini           # env.py lee DATABASE_URL de get_settings(); versions/ vacío
├── tests/
│   ├── unit/core/test_config.py, test_errors.py
│   ├── unit/api/test_health.py, test_error_handlers.py
│   ├── unit/infrastructure/test_celery_app.py
│   ├── unit/test_env_example.py
│   └── integration/__init__.py, conftest.py   # marca integration (C-02 la llena)
├── Dockerfile
└── .dockerignore
frontend/                            # Vite react-ts + Vitest + ESLint
docker-compose.yml, .env.example, .gitignore   # raíz
```

`app/main.py` expone `create_app()` (para tests) y `app = create_app()` a nivel módulo para uvicorn. `create_app()` es lo único que llama a `get_settings()` (para CORS); importar `app.domain` o `app.core.timezone` nunca dispara la carga de configuración.

**Alternativa descartada**: crear `app/` desde la plantilla de un generador (cookiecutter de FastAPI): reorganizaría lo que ya existe y trae piezas (auth, ORM) que corresponden a C-02/C-03.

### D-2 — Configuración con Pydantic Settings, cargada a demanda

`Settings(BaseSettings)` con un campo por variable de la spec; `SecretStr` para `JWT_SECRET_KEY`, `SMTP_PASSWORD` y `DATABASE_URL` (contiene la contraseña), de modo que la representación y los mensajes de validación no muestren el valor. Validadores: zona con `zoneinfo.ZoneInfo`, longitud de la clave, `Literal["HS256"]`, rangos numéricos, `CORS_ORIGINS` partido por comas y sin espacios. `get_settings()` con `functools.lru_cache`; los tests construyen `Settings(...)` explícitamente o usan `monkeypatch.setenv` + `get_settings.cache_clear()`.

No lee `.env` directo desde Python: en Docker las variables llegan por `env_file`; localmente el que quiera puede exportarlas. Así hay una sola forma de cargar y no hay dos fuentes que diverjan.

Decisión registrada en apply (Context7, `pydantic-settings`): `CORS_ORIGINS` se declara `Annotated[list[str], NoDecode, BeforeValidator(split_comma)]` (sin JSON); los campos usan el nombre exacto de la variable para que el error la nombre y `hide_input_in_errors=True` evita mostrar el valor recibido. Original: se consultará la documentación vigente de `pydantic-settings` (lista separada por comas en un campo `list[str]`, que por defecto se espera en JSON) con Context7 al implementar; la decisión de usar un validador `mode="before"` o un tipo `str` con propiedad derivada se registra en la task correspondiente.

**Alternativas descartadas**: `os.environ` con validación manual (repetitivo y sin tipos); cargar la configuración al importar el módulo (rompería los 199 tests de dominio, que hoy corren sin entorno).

### D-3 — `DomainError` en `app/core/errors.py` y la tabla de estados en la API

```python
class DomainError(Exception):
    code: ClassVar[str] = "DOMAIN_ERROR"
```

`SlotTakenError` y `AppointmentNotFoundError` cambian `Exception` por `DomainError`; su `code`, mensaje y atributos quedan igual (la batería de contrato es la red de seguridad). `app/core/errors.py` solo usa la librería estándar, así que `domain/` puede importarlo sin violar la regla dura 2.

La traducción a HTTP vive en `app/api/errors.py`: `STATUS_BY_CODE = {"APPOINTMENT_NOT_FOUND": 404, "SLOT_TAKEN": 409}`, 400 por defecto. Los changes siguientes agregan códigos a esa tabla. Un handler aparte para `Exception` devuelve 500 con `{"error": {"code": "INTERNAL_ERROR", "message": "Error interno"}}` y registra la traza solo en el log.

Los resultados de rechazo de las reglas puras (`validate_appointment` devuelve un resultado, no una excepción, DD-32) no cambian: C-08 decide cómo se traducen.

**Alternativas descartadas**: estado HTTP como atributo del error (mete HTTP en el dominio); mover los errores existentes a `core/errors.py` (cambia imports archivados sin beneficio).

### D-4 — Celery mínimo, aislado en `infrastructure/tasks/`

`celery_app.py` crea `Celery("odonto")` con `broker=REDIS_URL`, `timezone=CLINIC_TIMEZONE`, `enable_utc=True` (como pide `11_recordatorios_email.md`) y sin `include` de tareas ni `beat_schedule`. `worker` y `beat` usan la misma imagen que `api` con otro `command`; beat guarda su archivo de programación en `/tmp` para no ensuciar el volumen montado.

Todo lo de Celery queda en esa carpeta y en dos servicios del compose: si la cátedra no lo acepta (P-1), el reemplazo no toca dominio, API ni frontend. Celery no trae tipos: mypy lleva un override `ignore_missing_imports` solo para el módulo `celery`.

**Alternativa descartada**: no crear `worker`/`beat` hasta C-11. El alcance de C-01 en `CHANGES.md` pide los siete servicios y dejar el compose completo evita tocarlo en C-11.

### D-5 — Docker Compose

| Servicio | Imagen / build | Notas |
|---|---|---|
| `db` | `postgres:16-alpine` | `POSTGRES_*` del `.env`; volumen `pgdata`; healthcheck `pg_isready`; sin puertos publicados |
| `redis` | `redis:7-alpine` | healthcheck `redis-cli ping`; sin puertos publicados |
| `api` | `./backend` | `uvicorn app.main:app --host 0.0.0.0 --reload`; puerto 8000; `depends_on` db y redis `service_healthy`; healthcheck con `python -c` + `urllib` contra `/api/v1/health` (la imagen slim no trae curl) |
| `worker` | `./backend` | `celery -A app.infrastructure.tasks.celery_app worker` |
| `beat` | `./backend` | `celery -A ... beat -s /tmp/celerybeat-schedule` |
| `frontend` | `./frontend` | `vite --host 0.0.0.0`; puerto 5173; `environment: VITE_API_URL: ${VITE_API_URL}` (sin `env_file`) |
| `mailpit` | `axllent/mailpit` | 1025 interno; 8025 publicado |

`api`, `worker` y `beat` usan `env_file: .env` (en su forma corta, que exige el archivo: sin `.env` compose falla antes de crear contenedores, que es el escenario de error buscado). El frontend **no** usa `env_file`: recibe solo `VITE_API_URL`, así ningún secreto entra a su contenedor ni al bundle. Se monta `./backend:/app` y `./.env.example:/.env.example:ro` en `api` para el test de contrato del ejemplo (D-7).

No publicar 5432 ni 6379 evita choques con un PostgreSQL local (en esta máquina hay uno instalado, `PostgreSQL/18`) y reduce superficie. Para inspeccionar la base: `docker compose exec db psql`.

`backend/Dockerfile`: `python:3.12-slim`, `pip install -e ".[dev]"`, usuario no root. Las dependencias de desarrollo van en la imagen de desarrollo para poder correr los tests adentro; C-13 hará una imagen de producción sin ellas.

`frontend/Dockerfile`: `node:22-alpine` (LTS), `npm ci`, `npm run dev -- --host 0.0.0.0`. `node_modules` en volumen anónimo para no pisarlo con el del anfitrión.

**Alternativa descartada**: publicar los puertos de base y Redis para correr los tests de integración desde el anfitrión: obligaría a tener Python 3.12 local, que justamente se quiere evitar.

### D-6 — Python 3.12 en Docker y cómo correr los tests

La imagen fija 3.12 (el mínimo de `requires-python`, la versión que valida la cátedra). Comando documentado: `docker compose run --rm api pytest` (y `ruff check .`, `ruff format --check .`, `mypy`). Localmente sigue funcionando el `.venv` 3.13 del backend y `probar.bat`; con el `python` 3.11 del sistema no (el README lo aclara).

`pytest` agrega `markers = ["integration: ..."]` y `addopts = "-m 'not integration'"`; los de integración se piden con `pytest -m integration`.

### D-7 — Chequeos sobre `.env.example` como test del backend

`tests/unit/test_env_example.py` lee el archivo (ruta en `ENV_EXAMPLE_PATH`, por defecto `<repo>/.env.example` resuelto desde la ubicación del test, o `/.env.example` en el contenedor) y verifica: cada campo de `Settings` figura; `JWT_SECRET_KEY` y `SMTP_PASSWORD` vacías; ninguna variable `VITE_` contiene `SECRET`, `PASSWORD`, `TOKEN`, `KEY` ni `DATABASE`. La lógica de "nombre sensible" es una función pura probada aparte con `VITE_JWT_SECRET_KEY` (escenario de error) para no depender de editar el archivo real. Si el archivo no se encuentra, el test **falla** (no se saltea): esconderlo sería peor que un fallo claro.

Que el frontend no recibe secretos se verifica en la task de verificación con `docker compose config` (escenario de `runtime-configuration`), no con un test automatizado, porque requiere Docker.

### D-8 — Ruff y mypy: reglas y excepciones

`pyproject.toml`:

- `[tool.ruff]` `target-version = "py312"`, `line-length = 100`; `lint.select = ["E", "W", "F", "I", "UP", "B", "SIM", "TRY"]`.
- `lint.ignore = ["TRY003", "TRY004"]` con comentario: los mensajes en español dentro de `ValueError` y el uso de `ValueError` tras `isinstance` son la convención DD-18 (errores del llamador), aplicada en todo el dominio; cambiarla a `TypeError` cambiaría escenarios archivados. Se ignoran globalmente porque la convención es global, no de dos archivos.
- **UP017 se corrige** (`timezone.utc` → `datetime.UTC`): es un cambio equivalente en 3.11+, sin efecto de comportamiento; los tests de `clinic-timezone` son la red.
- `[tool.mypy]` `strict = true`, `python_version = "3.12"`, `files = ["app", "tests"]`, plugin `pydantic.mypy`; override `ignore_missing_imports` para `celery.*`.
- **Los tests se anotan** (los 37 errores de `helpers.py` y `test_compute_slots.py`) en lugar de limitar mypy a `app/`: la regla dura 1 pide type hints en todo el código, y los helpers de test son código que usan los demás tests. Es un cambio mecánico sin efecto en el comportamiento.

Registro de apply: al correr ruff con estas reglas aparecieron, además de los UP017, avisos mecánicos que se corrigieron sin excepciones nuevas: B905 (`zip(..., strict=False)` en un test, las listas tienen largos distintos a propósito), F401 (import sin usar), I001 (orden de imports) y E501 (líneas largas, resueltas con `ruff format`). Mypy estricto sobre `app` y `tests` quedó limpio tras anotar los dos archivos de tests.

Antes de aplicar la configuración, la primera task corre ruff con estas reglas sobre el código actual: si aparecen avisos distintos de los 3 conocidos, se corrigen si son mecánicos o se registran en esta sección antes de agregar otra excepción.

**Alternativas descartadas**: `# noqa` por línea (ensucia el dominio y hay que repetirlo en cada función nueva); limitar mypy a `app/` (deja los tests fuera de la regla dura 1).

### D-9 — Frontend mínimo

Plantilla `react-ts` de Vite (apply: la plantilla actual trae oxlint y TypeScript 7; se reemplazó oxlint por ESLint y se fijó `typescript@~5.9` porque `typescript-eslint` aún no soporta TS 7); `tsconfig` con `strict`, `noUncheckedIndexedAccess` y `noImplicitOverride`. ESLint (configuración plana) con `typescript-eslint` `recommendedTypeChecked`, `@typescript-eslint/no-explicit-any: "error"` y las reglas de hooks de React. Vitest con `jsdom` y Testing Library.

`src/config.ts` exporta `apiUrl(path)` que lee `import.meta.env.VITE_API_URL`, quita la barra final y devuelve `null` si falta. `src/App.tsx` usa un hook `useApiHealth()` con tres estados (`checking`, `up`, `down`) más el caso "sin configurar". Los tests mockean `fetch` (sin red) y cubren los escenarios de `frontend-shell`. Scripts: `dev`, `build`, `test` (`vitest run`), `typecheck` (`tsc -b --noEmit`), `lint`.

Se cargan `frontend-design:frontend-design` y la parte de React de `vercel-react-best-practices` al implementar; la pantalla es mínima y sin librería de componentes (decisión de UI que se toma en C-06/C-09).

### D-10 — Orden de implementación

1. Tooling (ruff, mypy, anotaciones, UP017) con los 199 tests en verde: deja la base limpia antes de agregar código.
2. `core/errors.py` + herencia de los errores existentes (contrato en verde).
3. `core/config.py` (TDD sobre los escenarios de configuración).
4. API (`main`, health, CORS, handlers).
5. Celery y Alembic.
6. `.env.example`, `.gitignore`, test del ejemplo.
7. Dockerfiles y compose.
8. Frontend.
9. README y verificación con Docker.

## Risks / Trade-offs

- [Docker no instalado en la máquina de desarrollo] → los escenarios de `local-environment` no se pueden verificar localmente. Mitigación: P-3; mientras tanto, todo lo demás (tests, lint, tipos, frontend) se verifica sin Docker y la task de verificación con Docker queda explícita y sin marcar hasta correrla.
- [La cátedra rechaza Celery (DD-10)] → cambiar `infrastructure/tasks/` y dos servicios del compose. Mitigación: D-4 (aislado y sin tareas todavía).
- [Hot reload con volúmenes en Windows] → los cambios pueden no detectarse dentro del contenedor. Mitigación: `WATCHFILES_FORCE_POLLING=true` en `api` y `server.watch.usePolling` en Vite; no es un requisito.
- [Dependencias sin lockfile en Python] → una versión nueva puede romper la imagen. Mitigación: rangos con tope de versión mayor en `pyproject.toml`; C-13 decide si agrega lockfile.
- [Proveedor SMTP gratuito sin definir (SU-02)] → no afecta C-01 (Mailpit cubre desarrollo); queda como riesgo registrado para C-11.
- [Cambiar la clase base de errores archivados] → riesgo bajo; la batería de contrato de C-05d corre antes y después.
- [Excepción de la regla dura 4 para `/health`] → si el usuario no la acepta (P-2), el healthcheck de Docker debe pasar a chequear el puerto en vez de la ruta y la spec `api-health` cambia.

## Migration Plan

No hay datos ni despliegue previos. Rollback: revertir el commit; el dominio y sus tests no dependen de nada nuevo salvo la clase base `DomainError`.

## Preguntas para el usuario (P-1 y P-2 resueltas; P-3 pendiente de instalación)

> Cada una trae una recomendación. Hasta que se confirmen, el diseño aplica la recomendación y queda marcado como pendiente.

### P-1 — ¿Usamos Celery para las tareas en segundo plano aunque la cátedra todavía no lo confirmó? (DD-10) — **confirmado por el usuario (Celery, sin consultar a la cátedra)**

El sistema necesita algo que mande los emails "por detrás" y que dispare el recordatorio todos los días. Elegimos Celery, pero la decisión está anotada como "a confirmar con el profesor".

**Recomendación**: seguir con Celery en C-01, pero solo como un esqueleto vacío (los servicios arrancan, sin ninguna tarea). Consultar al profesor antes de empezar C-11, que es cuando se escriben las tareas de verdad. Si dice que no, cambiarlo solo afecta una carpeta y dos servicios del compose.

### P-2 — ¿El chequeo de salud de la API puede ser público, sin iniciar sesión? — **aceptado por el usuario**

Una regla del proyecto dice que todos los endpoints piden sesión salvo el login. Docker y la pantalla inicial necesitan preguntar "¿la API está viva?" sin estar logueados.

**Recomendación**: que `/api/v1/health` sea público, que responda solo `{"status": "ok"}` (sin versiones, ni datos, ni configuración) y actualizar la regla 4 de `CLAUDE.md`/`AGENTS.md` a "salvo el login y el chequeo de salud".

### P-3 — ¿Podés instalar Docker Desktop en la máquina de desarrollo? — **no instalado todavía; las tasks con Docker quedan pendientes**

Hoy no está instalado, y sin él no se puede comprobar que "un comando levanta todo" ni correr los tests en Python 3.12 (la versión mínima del proyecto; la de tu sistema es 3.11).

**Recomendación**: instalar Docker Desktop (gratis para uso personal y educativo) antes de `/opsx:apply`. Si no es posible, implementar igual y dejar sin marcar solo la task de verificación con Docker, aclarándolo en el informe.
