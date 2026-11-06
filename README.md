# Sistema Odontológico: agenda de turnos

Trabajo de integración de Metodología I (Tecnicatura Universitaria en Programación): del Discovery al primer change con Spec-Driven Development (OpenSpec) y Active Stack.

Sistema de gestión de turnos y agenda de pacientes para consultorios odontológicos, pensado para el mercado argentino. Un consultorio puede tener uno o varios odontólogos y la agenda se maneja por profesional.

## Video explicativo

[Ver el video explicativo en YouTube](https://youtu.be/Wz8IocynNSU)

## Qué hay en este repositorio

| Carpeta o archivo | Contenido |
|---|---|
| `docs/discovery/` | Informe de Discovery (investigación de mercado, `.md` y `.pdf`) |
| `discovery/` | Respuestas del checklist de Discovery |
| `knowledge-base/` | Base de conocimiento: visión, descripción, actores, modelo de datos, reglas, funcionalidades, flujos, arquitectura, decisiones y preguntas abiertas (más un archivo extra sobre recordatorios por email y su índice) |
| `CHANGES.md` | Roadmap de 13 changes con dependencias, camino crítico y riesgos |
| `.atl/skill-registry.md` | Registro de skills con la decisión de cada recomendación |
| `AGENTS.md` y `CLAUDE.md` | Reglas del proyecto para los agentes (mismo contenido) |
| `.active-orchestrator-state.json` | Estado de la fundación del proyecto |
| `openspec/specs/` | Especificaciones vigentes (`appointment-creation`) |
| `openspec/changes/archive/` | Change archivado `crear-turno-sin-solapamientos` (proposal, design, tasks y specs) |
| `backend/app/` | Backend: lógica de dominio, configuración, API base (`/api/v1/health`) y esqueleto de Celery |
| `frontend/` | SPA React + TypeScript + Vite con la pantalla inicial que muestra el estado de la API |
| `docker-compose.yml`, `.env.example` | Entorno de desarrollo de un solo comando y variables de ejemplo (sin secretos) |
| `backend/tests/` | Tests automatizados, uno por cada escenario de la especificación |
| `docs/opsx/` | Resumen de Explore y registro de Verify del change |
| `docs/engram/` | Evidencia de la memoria del agente (Engram) |
| `.claude/skills/revisor-escenarios-turnos/` | Skill propia del agente para revisar escenarios de agenda |
| `docs/skills-mcp/` | Ficha de investigación, referencia de la skill creadora, configuración de ejemplo del MCP y evidencias |

El código está en `backend/` porque el stack del proyecto tiene backend y frontend separados (FastAPI y React). Hoy hay lógica de dominio, configuración, API base de salud y un frontend mínimo; la base de datos, el login y la agenda llegan en los próximos changes.

## Cómo levantar el entorno y correr los chequeos

### Con Docker (recomendado)

Requisito: Docker Desktop. No hace falta instalar Python, PostgreSQL ni Redis: el contenedor del backend usa Python 3.12 (el `python` 3.11 del sistema no sirve para este proyecto).

1. Copiar el archivo de ejemplo y completar la clave JWT (la API no arranca sin ella):

   ```bash
   cp .env.example .env
   python -c "import secrets; print(secrets.token_urlsafe(48))"   # pegar el resultado en JWT_SECRET_KEY
   ```

2. Levantar los siete servicios (`db`, `redis`, `api`, `worker`, `beat`, `frontend`, `mailpit`):

   ```bash
   docker compose up
   ```

| Servicio | URL en la máquina |
|---|---|
| API (docs en `/docs`, salud en `/api/v1/health`) | http://localhost:8000 |
| Frontend | http://localhost:5173 |
| Mailpit (emails de desarrollo) | http://localhost:8025 |

PostgreSQL y Redis no publican puertos: solo los ven los demás contenedores (`docker compose exec db psql -U odonto`).

### Emails de confirmación

Al agendar o reprogramar un turno, el servidor encola el envío de la confirmación (texto plano) y el `worker` la manda por SMTP. En desarrollo y en la demo el servidor SMTP es Mailpit: abrir http://localhost:8025 para ver los emails; no sale ningún email real. Si Redis o el `worker` están caídos, el turno se guarda igual y la confirmación queda `pending`: `beat` la reencola cada 10 minutos.

El adaptador SMTP se configura solo con las variables `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_USE_TLS` y `EMAIL_FROM` del `.env` local (nunca en el repositorio ni en el frontend); cambiar de servidor no requiere tocar el código. La variable opcional `EMAIL_REDIRECT_TO` manda todos los emails a una única casilla con la línea "Email de demostración"; vacía, van al email del paciente.

Tras actualizar el código: reconstruir la imagen (`docker compose build api worker beat`), aplicar la migración que agrega la antigüedad de las notificaciones (`docker compose exec api alembic upgrade head`) y reiniciar `worker` y `beat`.

3. Chequeos del backend dentro del contenedor:

   ```bash
   docker compose run --rm api pytest
   docker compose run --rm api ruff check .
   docker compose run --rm api ruff format --check .
   docker compose run --rm api mypy
   ```

   Los tests de integración no corren por defecto; se piden con `pytest -m integration`.

### Base de datos: migración, datos de demostración y tests contra PostgreSQL

El backend agregó la dependencia `argon2-cffi`: tras actualizar el código, reconstruir la imagen (`docker compose build api worker beat`) y volver a levantar.

Agregar al `.env` (los valores de ejemplo están en `.env.example`): `SEED_DEMO_PASSWORD` (contraseña ficticia de las cuentas de demo; no se escribe en el código) y `TEST_DATABASE_URL` (una base **aparte** del mismo servidor, cuyo nombre termina en `_test`; los tests de integración se niegan a correr sobre otra).

```bash
docker compose exec api alembic upgrade head       # crea las 8 tablas, los enumerados y el constraint de exclusión
docker compose exec api python -m scripts.seed     # carga datos ficticios; se puede repetir sin duplicar nada
docker compose exec api alembic downgrade base     # deja la base sin tablas ni tipos del sistema
docker compose exec api pytest -m integration      # tests contra la base *_test (la crea y la migra sola)
```

El seed crea: 1 administrador, 1 recepcionista, 2 profesionales (cada uno con su cuenta de odontólogo) con horario de lunes a viernes, la configuración del consultorio (30 minutos, zona de `CLINIC_TIMEZONE`) y 10 pacientes, todo con emails `@example.com`. Las contraseñas se guardan solo como hash argon2.

### Sin Docker (solo backend, Python 3.12 o superior)

```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1        # PowerShell; en Git Bash o Linux: source .venv/Scripts/activate (o .venv/bin/activate)
pip install -e ".[dev]"
pytest && ruff check . && ruff format --check . && mypy
```

### Frontend

```bash
cd frontend
npm ci
npm test            # Vitest
npm run typecheck   # TypeScript estricto
npm run lint        # ESLint (any explícito es error)
```

## El change implementado

`crear-turno-sin-solapamientos`: dado un profesional, su horario, sus licencias y sus turnos, el sistema responde si se puede crear un turno nuevo o no, con un solo motivo de rechazo en orden fijo (anticipación mínima de 6 horas, grilla de 30 minutos, horario de trabajo, licencia y solapamiento). Los turnos que empiezan justo cuando termina otro no se consideran solapados.

Para ver el recorrido completo: `docs/opsx/explore-crear-turno-sin-solapamientos.md`, `openspec/changes/archive/` y `docs/opsx/verify-crear-turno-sin-solapamientos.md`.

## Herramientas del agente: skill propia y MCP

Estas incorporaciones son herramientas de desarrollo para el agente (Claude Code). No forman parte del producto. Detalle de la investigación en `docs/skills-mcp/investigacion.md`.

### Skill propia: `revisor-escenarios-turnos`

Está en `.claude/skills/revisor-escenarios-turnos/` y viene con el repositorio: al clonarlo y abrirlo con Claude Code ya está disponible. Revisa los escenarios de un change de agenda contra la base de conocimiento. Cómo se creó y cómo reproducir `skill-creator`: `docs/skills-mcp/skill-creator.md`.

### MCP: Context7 (documentación actualizada de librerías)

- **Para qué**: consultar la documentación vigente de librerías (por ejemplo `zoneinfo` de Python, pytest, Pydantic, FastAPI) mientras se prepara un change.
- **Herramientas**: `resolve-library-id` (obtiene el identificador de la librería) y `query-docs` (consulta la documentación). Siempre se usan en ese orden.
- **Requisitos**: Claude Code y Node.js con `npx` (se probó con Node v24.19.0).
- **Variables de entorno**: ninguna. Context7 funciona sin clave de API; la clave es opcional y solo da más límite de uso. Si se llega a usar una, va en la configuración local del usuario y nunca en el repositorio.
- **Configuración**: servidor local (`stdio`) declarado a nivel usuario en `~/.claude.json`, clave `mcpServers.context7`. El ejemplo sin secretos está en `docs/skills-mcp/mcp-context7.example.json`. Para reproducirla, agregar ese bloque a la configuración de Claude Code (a nivel usuario, o como `.mcp.json` en la carpeta del proyecto) y reiniciar la sesión.
- **Comprobar la conexión**: ejecutar `claude mcp list` en una terminal. Debe aparecer `context7: npx -y --package=@upstash/context7-mcp@2.2.5 -- context7-mcp - ✔ Connected`.
- **Comprobar que funciona**: pedirle al agente una consulta concreta, por ejemplo "consultá en Context7 cómo convierte `zoneinfo` un datetime UTC a hora local". Debe llamar a `resolve-library-id` y después a `query-docs`.
- **Límites de uso**: solo se consulta documentación pública. No se envían datos de pacientes (ni siquiera ficticios), claves ni código propio en las consultas, porque el texto de la consulta viaja al servicio externo de Context7.
- **Problemas de instalación**: en esta instalación no apareció ninguno. Una advertencia de uso: `query-docs` exige antes un identificador obtenido con `resolve-library-id`.
- **Evidencia de uso real**: `docs/skills-mcp/evidencias/mcp-context7-uso.md`.

### MCP: Postgres MCP Pro (`postgres-odonto`, base de desarrollo en solo lectura)

- **Para qué**: inspeccionar la base de desarrollo (esquema, constraints, índices, planes de ejecución, salud) sin salir de la sesión del agente. Elegido contra DBHub en `docs/skills-mcp/investigacion.md`.
- **Herramientas**: `list_schemas`, `list_objects`, `get_object_details`, `execute_sql`, `explain_query`, `get_top_queries`, `analyze_workload_indexes`, `analyze_query_indexes` y `analyze_db_health`.
- **Requisitos**: Claude Code, Docker Desktop y el stack levantado (`docker compose up`), porque el servidor corre en un contenedor que se une a la red de compose (la base no publica puertos). El nombre de la red es `sistema-odontologico_default`; se confirma con `docker network ls`.
- **Variables de entorno**: `DATABASE_URI`, con la forma `postgresql://<usuario>:<contraseña>@db:5432/<base>` (usuario, contraseña y base de tu `.env`). Va en la configuración local de Claude Code, a nivel usuario (`~/.claude.json`), nunca en el repositorio ni en archivos versionados.
- **Configuración**: `claude mcp add postgres-odonto -s user -e DATABASE_URI=<uri> -- docker run -i --rm --network sistema-odontologico_default -e DATABASE_URI crystaldba/postgres-mcp --access-mode=restricted`. Ejemplo sin secretos: `docs/skills-mcp/mcp-postgres-odonto.example.json`. Reiniciar la sesión después de agregarlo.
- **Comprobar la conexión**: `claude mcp get postgres-odonto` debe mostrar `Status: ✔ Connected`.
- **Comprobar que funciona**: pedirle al agente "listá las tablas de `public` con `postgres-odonto`" o "mostrá las constraints de `appointments`". Debe aparecer `ex_appointments_no_overlap`.
- **Límites de uso**: apunta solo a la base de **desarrollo** con datos ficticios, nunca a producción. Corre con `--access-mode=restricted` (solo lectura, con validación de las consultas): se comprobó que rechaza un `DELETE`. Ese modo también rechaza la función `tstzrange`; para auditar superposiciones se usan comparaciones de `starts_at` y `ends_at`. No se usa para cambiar datos ni el esquema: eso pasa por Alembic. La contraseña no se incluye en consultas, docs ni capturas.
- **Problemas de instalación**: si da `Failed to connect`, verificar que el stack esté levantado y que la red exista; si cambia el nombre de la carpeta del proyecto, cambia el nombre de la red.
- **Evidencia de uso real**: `docs/skills-mcp/evidencias/mcp-postgres-odonto-uso.md`.

## Stack previsto

Backend: Python, FastAPI, JWT, SQLAlchemy, PostgreSQL, Redis, Celery y Docker Compose. Frontend: React, TypeScript y Vite. Todo gratuito, con datos de pacientes ficticios. El detalle está en `knowledge-base/02_descripcion_general.md`.
