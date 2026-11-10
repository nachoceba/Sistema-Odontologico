# Sistema Odontológico: agenda de turnos

Trabajo de integración de Metodología I (Tecnicatura Universitaria en Programación): del Discovery a un sistema completo con Spec-Driven Development (OpenSpec) y Active Stack.

Sistema de gestión de turnos y agenda de pacientes para consultorios odontológicos, pensado para el mercado argentino. Un consultorio puede tener uno o varios odontólogos y la agenda se maneja por profesional. Login por rol (administrador, recepción y odontólogo), pacientes, profesionales con horarios y licencias, agenda de turnos sin superposiciones (garantizada por la base de datos), email de confirmación al agendar o reprogramar y recordatorio el día anterior. Todo gratuito y con datos de pacientes ficticios.

## Video explicativo

[Ver el video explicativo en YouTube](https://youtu.be/Wz8IocynNSU)

## Qué hay en este repositorio

| Carpeta o archivo | Contenido |
|---|---|
| `backend/` | API FastAPI en capas (`domain` puro, `application`, `infrastructure`), migraciones Alembic, tareas Celery, seed ficticio y tests |
| `frontend/` | SPA React + TypeScript + Vite (login, agenda, pacientes, profesionales, usuarios) y su imagen nginx para la demo |
| `docker-compose.yml` | Entorno de desarrollo de un solo comando |
| `docker-compose.demo.yml` | Modo demo: se suma al archivo anterior (frontend en nginx, API sin recarga) |
| `.env.example` | Variables de ejemplo, sin secretos |
| `knowledge-base/` | Base de conocimiento: visión, actores, modelo de datos, reglas, flujos, arquitectura, decisiones (DD) y preguntas abiertas |
| `CHANGES.md` | Roadmap de 14 changes con dependencias, estado y riesgos |
| `openspec/specs/` y `openspec/changes/archive/` | Especificaciones vigentes y changes archivados (proposal, design, tasks y specs) |
| `AGENTS.md` y `CLAUDE.md` | Reglas del proyecto para los agentes (mismo contenido) |
| `docs/adopcion-recepcion.md` | Checklist de adopción para la recepción y el dueño |
| `docs/discovery/`, `discovery/`, `docs/opsx/`, `docs/engram/`, `docs/skills-mcp/`, `.atl/`, `.claude/skills/` | Discovery, registros del flujo de trabajo con agentes, memoria y herramientas del agente |

## Requisitos

Docker Desktop con una versión reciente de Docker Compose (el modo demo usa las directivas `!reset` y `!override`; se probó con v5.6.1). No hace falta instalar Python, PostgreSQL, Redis ni Node: todo corre en contenedores (el backend usa Python 3.12).

## Puesta en marcha

1. Copiar el archivo de ejemplo y completar dos valores **solo en el `.env` local** (nunca en `.env.example` ni en el repositorio; `.env` está ignorado por git):

   ```bash
   cp .env.example .env
   python -c "import secrets; print(secrets.token_urlsafe(48))"   # pegar el resultado en JWT_SECRET_KEY
   ```

   - `JWT_SECRET_KEY`: clave para firmar los tokens (mínimo 32 caracteres). Sin valor, nada arranca.
   - `SEED_DEMO_PASSWORD`: una contraseña propia para las cuentas de demostración que crea el seed (DD-40). Sin valor, el paso de preparación falla y nada arranca.
   - Recomendado: cambiar también la contraseña de la base (`POSTGRES_PASSWORD` y, con la misma contraseña, `DATABASE_URL` y `TEST_DATABASE_URL`).

2. Levantar todo con un comando:

   ```bash
   docker compose up
   ```

   Antes de que arranquen `api` y `worker`, el servicio `migrate` aplica las migraciones y el seed ficticio y termina (código 0); si falla (por ejemplo, falta `SEED_DEMO_PASSWORD`) nada más arranca y `docker compose logs migrate` muestra el motivo. Volver a levantar no duplica datos ni pisa cambios.

| Servicio | URL en la máquina |
|---|---|
| Frontend (desarrollo, Vite con recarga) | http://localhost:5173 |
| API (docs en `/docs`, salud en `/api/v1/health`) | http://localhost:8000 |
| Mailpit (emails de desarrollo) | http://localhost:8025 |

PostgreSQL y Redis no publican puertos: solo los ven los demás contenedores (`docker compose exec db psql -U odonto`).

Cuentas del seed (todas con la contraseña de `SEED_DEMO_PASSWORD`): `admin@example.com` (administrador), `recepcion@example.com` (recepción), `dra.a@example.com` y `dr.b@example.com` (odontólogos). El seed también crea 2 profesionales con horario de lunes a viernes, la configuración del consultorio (30 minutos, zona de `CLINIC_TIMEZONE`) y 10 pacientes con emails `@example.com`.

### Actualizar a una versión nueva

`docker compose up --build`. Si el `.env` es anterior a C-13, agregar `http://localhost:8080` a `CORS_ORIGINS` (ver Modo demo) y completar `SEED_DEMO_PASSWORD`.

## Modo demo

Sirve el frontend ya construido con nginx y la API sin recarga de código ni montaje del código del anfitrión. Los emails siguen yendo a Mailpit: no se usa ningún servidor SMTP ni cuenta externa.

```bash
docker compose -f docker-compose.yml -f docker-compose.demo.yml up --build
```

| Servicio | URL |
|---|---|
| Frontend (nginx, archivos estáticos) | http://localhost:8080 |
| API | http://localhost:8000 |
| Mailpit | http://localhost:8025 |

- **CORS**: el navegador llama a la API directo (puerto 8000), así que `CORS_ORIGINS` del `.env` debe incluir `http://localhost:8080` (el ejemplo ya lo trae: `http://localhost:5173,http://localhost:8080`). Sin eso, la pantalla de login muestra "API no disponible".
- La URL de la API se fija al construir la imagen con `VITE_API_URL` (por defecto `http://localhost:8000/api/v1`); si cambia, reconstruir con `--build`.
- La construcción de la imagen falla si falta `VITE_API_URL` o si el bundle contiene el nombre o el patrón de un secreto (`npm run check:bundle`).
- **Volver a desarrollo**: `docker compose -f docker-compose.yml -f docker-compose.demo.yml down` y después `docker compose up --build` (sin el archivo de la demo).

## Smoke test de punta a punta

Con el entorno levantado (desarrollo o demo):

```bash
docker compose exec api pytest -m smoke
```

Recorre, por HTTP contra la API y Mailpit: login de las tres cuentas del seed, agendar un turno de mañana, rechazo de una franja ocupada (`SLOT_TAKEN`) y del odontólogo que intenta agendar (403), confirmación en Mailpit, cancelar (la franja vuelve a quedar libre), agendar otro turno, reprogramarlo, pasada de recordatorios forzada (un solo recordatorio, el del turno reprogramado) y una segunda pasada que no agrega nada. Si mañana ningún profesional atiende, agrega un tramo a un profesional y al final le restituye los originales. Deja dos pacientes `Smoke… Prueba` desactivados y sus turnos cancelados; los datos del seed no cambian. Si falta `SEED_DEMO_PASSWORD`, o la API o Mailpit no responden, falla de entrada nombrándolos. No corre en `pytest` ni en `pytest -m integration`.

La pasada de recordatorios también se puede forzar a mano desde la consola (no existe ninguna ruta de la API para hacerlo):

```bash
docker compose exec worker celery -A app.infrastructure.tasks.celery_app call enviar_recordatorios --kwargs='{"forzar": true}'
```

## Reserva online de turnos (C-15)

Los pacientes reservan sin iniciar sesión en `/turnos`: eligen profesional y franja libre y completan DNI, nombre, apellido y email (el teléfono es opcional). La reserva queda pendiente de confirmación y ocupa la franja; el sistema envía un email con un enlace a `/turnos/confirmar`, y el turno queda firme cuando el paciente toca el botón de esa página. Recepción ve la reserva como "Pendiente de confirmación" (solo puede cancelarla) y, ya confirmada, como "Online". En desarrollo y demo el email se lee en Mailpit (http://localhost:8025). El plazo se ajusta con `ONLINE_BOOKING_HOLD_MINUTES` y el enlace se arma con `PUBLIC_APP_URL` (ver la tabla de variables). Las reservas sin confirmar vencen solas: una tarea cada 5 minutos las cancela y avisa al paciente por email (change C-16).

## Servicios

| Servicio | Qué hace |
|---|---|
| `db` | PostgreSQL 16 (constraint de exclusión de turnos con `btree_gist`) |
| `redis` | Broker de Celery |
| `migrate` | Una sola vez por `up`: `alembic upgrade head` y seed ficticio idempotente |
| `api` | FastAPI en el puerto 8000 (en desarrollo con recarga automática) |
| `worker` | Celery: envía los emails de confirmación y de recordatorio |
| `beat` | Celery Beat: dispara `enviar_recordatorios` cada hora en punto (solo actúa a la hora configurada) `reencolar_pendientes` cada 10 minutos y `vencer_reservas_pendientes` cada 5 minutos (cancela las reservas online sin confirmar y avisa al paciente) |
| `frontend` | Vite en el 5173 (desarrollo) o nginx en el 8080 (demo) |
| `mailpit` | Servidor SMTP y bandeja web de desarrollo; no sale ningún email real |

Si Redis o el `worker` están caídos, el turno se guarda igual y la confirmación queda `pending`: `beat` la reencola. Si la hora de recordatorios pasa con `beat` o el `worker` caídos, ese día no salen recordatorios.

## Variables de entorno

Los valores van solo en el `.env` local; `.env.example` declara todas sin secretos. Las marcadas como sensibles nunca deben ir al repositorio ni al frontend.

| Variable | Descripción | Sensible |
|---|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Credenciales del contenedor de PostgreSQL | Sí (la contraseña) |
| `DATABASE_URL` | Cadena de conexión a PostgreSQL | Sí |
| `TEST_DATABASE_URL` | Base aparte (nombre terminado en `_test`) para los tests de integración | Sí |
| `REDIS_URL` | Conexión a Redis | No |
| `JWT_SECRET_KEY` | Clave de firma de los tokens (mínimo 32 caracteres) | Sí |
| `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` | Algoritmo (`HS256`) y vida del token (30 minutos) | No |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USE_TLS`, `EMAIL_FROM` | Servidor SMTP (en desarrollo y demo, Mailpit) y remitente | No |
| `SMTP_USER`, `SMTP_PASSWORD` | Credenciales SMTP (vacías con Mailpit) | Sí |
| `EMAIL_REDIRECT_TO` | Opcional: manda todos los emails a una sola casilla | No |
| `CLINIC_TIMEZONE` | Zona horaria del consultorio | No |
| `CORS_ORIGINS` | Orígenes del navegador permitidos, con esquema y sin `*` | No |
| `SEED_DEMO_PASSWORD` | Contraseña de las cuentas de demostración del seed | Sí |
| `VITE_API_URL` | URL pública de la API para el navegador (única variable del frontend) | No |
| `ONLINE_BOOKING_HOLD_MINUTES` | Minutos que una reserva online espera su confirmación (de 5 a 1440; por defecto 60) | No |
| `PUBLIC_APP_URL` | Dirección pública del frontend, sin barra final, para el enlace del email de confirmación (por defecto `http://localhost:5173`) | No |

## Chequeos

Backend, dentro del contenedor (con el entorno levantado: `docker compose exec api …`; sin él: `docker compose run --rm api …`):

```bash
docker compose exec api pytest                  # tests por defecto (sin base ni red)
docker compose exec api pytest -m integration   # contra PostgreSQL, Redis y Mailpit (base *_test, la crea y la migra sola)
docker compose exec api pytest -m smoke         # recorrido de punta a punta (ver arriba)
docker compose exec api mypy --strict app/
docker compose exec api ruff check .
docker compose exec api ruff format --check .
```

Frontend:

```bash
cd frontend
npm ci
npm test               # Vitest
npm run typecheck      # TypeScript estricto
npm run lint           # ESLint (any explícito es error)
npm run build && npm run check:bundle   # el bundle no contiene secretos
```

Sin Docker (solo backend, Python 3.12 o superior): `cd backend && python -m venv .venv && pip install -e ".[dev]" && pytest`.

## Seguridad

Todo endpoint exige JWT y rol salvo el login, `GET /api/v1/health` y los cuatro de la reserva online bajo `/api/v1/public/`, que llevan límite de pedidos por IP y nunca devuelven datos de pacientes. Una matriz única ruta × rol (`backend/tests/unit/api/test_permission_matrix.py`) debe ser igual al conjunto de rutas registradas, y comprueba 401 sin token y 403 por rol. CORS permite solo los orígenes de `CORS_ORIGINS` y solo los métodos y encabezados que usa el frontend, sin credenciales de navegador. El registro de accesos de la API no guarda la parte `?…` de la dirección (la búsqueda de pacientes). El código del frontend solo lee `VITE_API_URL` y el bundle se revisa para que no contenga secretos.

## Estado de los changes y decisiones abiertas

Los 17 changes del roadmap están implementados y archivados (C-17 agrega el tratamiento a cada turno, C-14 es la mejora de la capa visual, C-15 los turnos online con confirmación por email y C-16 el vencimiento automático de las reservas online sin confirmar; ver `CHANGES.md`); la lista de decisiones está en `knowledge-base/09_decisiones_y_supuestos.md`. Quedan abiertas, antes de usar datos reales:

- **SU-02, SMTP de producción**: hoy los emails van a Mailpit; falta elegir un servidor SMTP y revisar su cupo (el adaptador se configura solo por variables).
- **SU-01, zona horaria**: se asume `America/Argentina/Buenos_Aires` sin horario de verano; confirmar con el dueño.
- **Sesión y login (DD-46, DD-47)**: el token vive en `sessionStorage` y el login no tiene límite de intentos; evaluar cookie httpOnly y límite de intentos antes de usar datos reales.
- **R-10, revisión legal**: la v1 usa solo datos ficticios y no declara cumplimiento de la Ley 25.326; hace falta una revisión legal antes de cargar pacientes reales.
- **R-8, adopción**: ver `docs/adopcion-recepcion.md`.
- No hay HTTPS, dominio ni despliegue en la nube: el sistema corre en local con Docker Compose.

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

### Cómo revisar la capa visual (C-14)

La mejora visual no cambia textos, permisos ni pedidos a la API; se revisa en tres capas:

1. **Tests de contraste y tokens**: `cd frontend && npm test -- src/ui` corre `contrast.test.ts` (la función `contrastRatio`, WCAG 2.2) y `tokens.test.ts`, que lee `src/styles.css` y falla si falta un token, si un par de colores no llega a 4,5:1 (texto) o 3:1 (foco, borde de campo, marcas de estado), si hay colores sueltos fuera de `:root`, si un selector se repite o si se carga una fuente externa.
2. **Lista de verificación con el navegador integrado**, a 375, 768 y 1280 px: sin desplazamiento horizontal de la página; ningún control de menos de 24 × 24 px; primer Tab en "Saltar al contenido" y foco visible; el diente decorativo solo en la barra, el login y los avisos (nunca en tablas ni en la grilla) y quieto con `prefers-reduced-motion`; ningún pedido a dominios externos. Las mediciones del change están en `docs/skills-mcp/evidencias/ui-visual-refresh.md`. La skill `diseno-ui-odontologico` guía la revisión.
3. **Referencias de Stitch**: imágenes de referencia del proyecto "Sistema Odontologico" en Stitch (servicio externo, con datos ficticios); sirven para comparar a ojo y no reemplazan las mediciones. Se implementa a mano, sin importar el código generado.

## Stack

Backend: Python, FastAPI, JWT, SQLAlchemy, PostgreSQL, Redis, Celery y Docker Compose. Frontend: React, TypeScript y Vite. Todo gratuito, con datos de pacientes ficticios. El detalle está en `knowledge-base/02_descripcion_general.md`.
