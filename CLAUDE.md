# Sistema Odontológico — Instrucciones para Agentes

> Este archivo (y su copia `CLAUDE.md`) es lo PRIMERO que todo agente lee al entrar al repo.
> Generado a partir de `knowledge-base/` y `CHANGES.md`. No editar a mano sin re-sincronizar ambos archivos.

Sistema de gestión de agenda de turnos para un consultorio odontológico, con recordatorios por email. Proyecto académico (Metodología I): todo gratuito y con datos de pacientes ficticios.

---

## Stack Tecnológico

| Capa | Tecnología | Nota |
|------|------------|------|
| Backend | Python + FastAPI | API REST documentada con OpenAPI |
| Validación | Pydantic | Esquemas de entrada y salida |
| ORM / migraciones | SQLAlchemy 2.0 (síncrono) + Alembic | Migraciones versionadas |
| Base de datos | PostgreSQL | Constraint de exclusión para superposición (`btree_gist`) |
| Autenticación | JWT | Email + contraseña con hash seguro; token de vida corta |
| Autorización | `require_role` (dependencia de FastAPI) | Chequeo de rol en la capa de aplicación; no hay RLS |
| Tareas asincrónicas | Redis + Celery + Celery Beat | Emails y recordatorio programado |
| Email | SMTP | Mailpit en desarrollo; proveedor gratuito a definir |
| Frontend | React + TypeScript + Vite | SPA que consume la API REST |
| Contenedores | Docker / Docker Compose | Un comando levanta `migrate` (migraciones y seed, una vez), `db`, `redis`, `api`, `worker`, `beat`, `frontend`, `mailpit`; `docker-compose.demo.yml` suma el modo demo (frontend en nginx, puerto 8080) |
| Tests | pytest (backend) y Vitest (frontend) | Foco en la capa de dominio |

Arquitectura en capas del backend: `api/` → `application/` → `domain/` (funciones puras) → `infrastructure/`.

Detalle completo: [knowledge-base/02_descripcion_general.md](knowledge-base/02_descripcion_general.md)

---

## Base de Conocimiento

La fuente de verdad del dominio vive en `knowledge-base/`. **Leé el archivo relevante ANTES de implementar.**

| Archivo | Cuándo leerlo |
|---------|---------------|
| [01_vision_y_objetivos.md](knowledge-base/01_vision_y_objetivos.md) | Entender propósito y alcance |
| [02_descripcion_general.md](knowledge-base/02_descripcion_general.md) | Stack, arquitectura e integraciones |
| [03_actores_y_roles.md](knowledge-base/03_actores_y_roles.md) | Auth, RBAC, permisos |
| [04_modelo_de_datos.md](knowledge-base/04_modelo_de_datos.md) | Entidades, constraints, migraciones, seed |
| [05_reglas_de_negocio.md](knowledge-base/05_reglas_de_negocio.md) | Reglas codificadas (RN-XX) |
| [06_funcionalidades.md](knowledge-base/06_funcionalidades.md) | Historias de usuario por épica |
| [07_flujos_principales.md](knowledge-base/07_flujos_principales.md) | Flujos extremo a extremo |
| [08_arquitectura_propuesta.md](knowledge-base/08_arquitectura_propuesta.md) | Capas, estructura de directorios, variables de entorno |
| [09_decisiones_y_supuestos.md](knowledge-base/09_decisiones_y_supuestos.md) | Decisiones DD y supuestos SU |
| [10_preguntas_abiertas.md](knowledge-base/10_preguntas_abiertas.md) | ⚠️ Inconsistencias a resolver ANTES de codear |
| [11_recordatorios_email.md](knowledge-base/11_recordatorios_email.md) | Emails de confirmación y recordatorio |

> ⚠️ Queda abierto en `10_preguntas_abiertas.md` el proveedor SMTP gratuito de producción y su cupo (SU-02); desarrollo y demo usan Mailpit. También siguen abiertos el endurecimiento de sesión y login y la adopción con una recepcionista real. (SU-06, quién edita los horarios, quedó resuelta en C-03.)

Contexto de mercado (no normativo): [docs/discovery/informe-discovery.md](docs/discovery/informe-discovery.md).

---

## Skills Disponibles

<!-- Fuente: .atl/skill-registry.md -->

| Agente | Rol | Skills que carga |
|--------|-----|------------------|
| **Backend Core** | FastAPI / SQLAlchemy / Alembic / PostgreSQL | `supabase-postgres-best-practices` (solo la parte de PostgreSQL: esquema, índices, constraints), `tdd` |
| **Backend Aux / Dominio** | Funciones puras de `domain/`, Celery, email | `revisor-escenarios-turnos` (al preparar specs de agenda), `tdd` |
| **Frontend** | React + TypeScript + Vite | `frontend-design:frontend-design`, `diseno-ui-odontologico` (al tocar estilos o pantallas), `vercel-react-best-practices` (solo la parte de React), `tdd` |
| **Orquestación** | OPSX / SDD / docs | `kb-creator`, `roadmap-generator`, `agent-instruction`, `skill-creator` |

Cargá la skill correspondiente al contexto ANTES de escribir código.

> La skill `supabase` se desinstaló porque no aplica a este stack (no hay Supabase, RLS ni Next.js). De `supabase-postgres-best-practices` ignorar lo específico de Supabase (RLS, `auth.uid()`). De `vercel-react-best-practices` usar solo las reglas de React; ignorar lo de Next.js y Server Components.

> Los compact rules de cada skill los resuelve el orquestador desde `.atl/skill-registry.md` (generado por `skill-registry`). Esta tabla solo mapea skill→rol.

### Skill propia: `revisor-escenarios-turnos`

Herramienta de desarrollo para el agente (no forma parte del producto), creada con `skill-creator`. Investigación y diseño en [docs/skills-mcp/investigacion.md](docs/skills-mcp/investigacion.md).

- **Ubicación**: `.claude/skills/revisor-escenarios-turnos/SKILL.md`, versionada en el repo y registrada en `.atl/skill-registry.md`.
- **Cuándo usarla**: al explorar o escribir proposal, specs, design o tasks de un change de turnos, horarios, licencias, slots, zona horaria o estados (por ejemplo C-05b, C-07, C-08, C-09), antes de cerrar la spec.
- **Qué necesita**: los escenarios o la spec borrador, y leer en el momento `05_reglas_de_negocio.md`, `10_preguntas_abiertas.md`, `09_decisiones_y_supuestos.md`, `04_modelo_de_datos.md` y la entrada del change en `CHANGES.md`.
- **Cómo revisar el resultado**: cada hallazgo cita una regla (RN, DD o SU) o dice "sin respaldo en la KB"; los códigos citados existen en el archivo; las decisiones de dominio nuevas quedan como preguntas al usuario y no se incorporan solas; hay al menos un escenario esperado, uno de error de negocio y uno de borde.
- **Límite**: solo revisa. No escribe código ni modifica la KB.

### Skill propia: `diseno-ui-odontologico`

Herramienta de desarrollo para el agente (no forma parte del producto), creada con `skill-creator`. Diseño en [docs/skills-mcp/investigacion-diseno-ui.md](docs/skills-mcp/investigacion-diseno-ui.md) y evidencia en [docs/skills-mcp/evidencias/ui-visual-refresh.md](docs/skills-mcp/evidencias/ui-visual-refresh.md).

- **Ubicación**: `.claude/skills/diseno-ui-odontologico/SKILL.md`, versionada en el repo y registrada en `.atl/skill-registry.md`.
- **Cuándo usarla**: al crear o cambiar estilos, tokens, componentes visuales o pantallas del frontend (por ejemplo C-14), y al revisar una pantalla por contraste, foco, tamaño de objetivos, anchos o motivo dental.
- **Qué necesita**: la pantalla o el archivo a revisar, `frontend/src/styles.css` y `design.md` de C-14 (criterios C-1 a C-10 y paleta); para medir, el navegador integrado.
- **Cómo revisar el resultado**: cada hallazgo cita el criterio (C-1 a C-10) y una medida (contraste con `contrastRatio`, tamaño en px, ancho de página); no cambia textos, acciones por rol ni pedidos a la API; las decisiones de diseño nuevas vuelven al usuario como pregunta.
- **Límite**: solo revisa y propone. No agrega librerías de componentes sin la aprobación del usuario (MIT, Apache o BSD) y nunca pone el diente animado en la grilla ni sin `prefers-reduced-motion`.

### Herramienta de revisión: navegador integrado (`mcp__Claude_Browser__*`)

Es el panel de navegador de la app de escritorio de Claude, no una skill del repo; antes de usarlo se carga la skill `built-in-browser`.

- **Propósito**: revisar la capa visual con la app levantada: tamaños de controles, ancho de página, color del foco calculado, recorrido con Tab y pedidos de red.
- **Herramientas que se usan**: `resize_window` (375, 768 y 1280 px), `computer` (captura y teclas), `javascript_tool` (solo lectura de estilos y medidas), `read_network_requests` y `read_page`.
- **Reglas**: solo `localhost` y entornos de desarrollo con datos ficticios; nunca la contraseña real de nadie ni credenciales del `.env` en la página; al terminar, `resize_window` con `preset: "desktop"`.
- **Cómo revisar el resultado**: anotar cada medida en la evidencia del change; ningún pedido a dominios externos.

### Integración MCP: Stitch (referencias de diseño)

Servicio externo de Google elegido por el usuario (P-2), no una skill. Instalación y notas en [docs/skills-mcp/investigacion-diseno-ui.md](docs/skills-mcp/investigacion-diseno-ui.md).

- **Propósito**: generar imágenes de referencia visual antes de tocar pantallas; se implementa a mano, sin importar HTML ni código generado.
- **Herramientas que se usan**: `create_project`, `create_design_system`, `update_design_system`, `generate_screen_from_text`, `get_screen`, `list_screens`, `edit_screens` y `download_file` (solo la imagen).
- **Reglas de datos**: solo descripciones con datos ficticios; nunca código, rutas internas, claves, `.env` ni datos de pacientes. Solo el proyecto propio "Sistema Odontologico": NUNCA `list_projects`, `delete_project` ni tocar otros proyectos de la cuenta.
- **Cómo revisar el resultado**: comparar con el inventario de pantallas y con las specs funcionales; lo que la API no tiene se descarta; las referencias no reemplazan ninguna medición.

### Integración MCP: Context7

Es una integración con un servicio externo, no una skill (no figura en `.atl/skill-registry.md`). Configuración y comprobación en el [README](README.md#herramientas-del-agente-skill-propia-y-mcp).

- **Propósito**: consultar la documentación vigente de librerías en lugar de responder de memoria.
- **Capacidades que se usan**: `resolve-library-id` y después `query-docs` (siempre en ese orden).
- **Cuándo usarlo**: al preparar o implementar algo que depende de detalles de una librería del stack (por ejemplo `zoneinfo`, pytest, Pydantic, FastAPI, SQLAlchemy). No hace falta para lógica propia del dominio.
- **Límites de acceso**: solo lectura de documentación pública. NUNCA incluir en las consultas datos de pacientes, claves, tokens ni código propio: el texto de la consulta viaja a un servicio externo. No usa base de datos ni credenciales.
- **Cómo revisar el resultado**: contrastar lo que devuelve con la versión de la librería que usa el proyecto (por ejemplo Python 3.12 o superior) y registrar en la spec o el design qué se consultó cuando influya en una decisión.

### Integración MCP: Postgres MCP Pro (`postgres-odonto`)

Integración con un servidor local, no una skill. Configuración y comprobación en el [README](README.md#mcp-postgres-mcp-pro-postgres-odonto-base-de-desarrollo-en-solo-lectura).

- **Propósito**: inspeccionar la base de desarrollo (esquema, constraints, índices, planes, salud) con datos reales en lugar de suponer a partir de las migraciones.
- **Capacidades que se usan**: `list_objects`, `get_object_details`, `execute_sql` (solo `SELECT`), `explain_query` y `analyze_db_health`.
- **Cuándo usarlo**: al verificar que la base cumple una regla (por ejemplo el constraint `ex_appointments_no_overlap`), al revisar el plan de una consulta nueva (por ejemplo las de agenda) o al diagnosticar datos de desarrollo. No hace falta para lógica de dominio.
- **Límites de acceso**: solo la base de desarrollo con datos ficticios, nunca producción. Modo `--access-mode=restricted` (solo lectura). NUNCA escribir datos ni cambiar el esquema por el MCP: eso va por Alembic y por la API. NUNCA pegar la contraseña de `DATABASE_URI` en consultas, docs ni capturas. El modo restringido rechaza `tstzrange`: para superposiciones comparar `starts_at` y `ends_at`.
- **Cómo revisar el resultado**: un resultado vacío no prueba una regla si la tabla no tiene datos (ver la evidencia sobre turnos); el aviso de "índices poco usados" no vale con una base casi vacía; contrastar con la migración y con la KB (`04_modelo_de_datos.md`). Evidencia en `docs/skills-mcp/evidencias/mcp-postgres-odonto-uso.md`.

---

## Roadmap de Changes

El plan de implementación completo está en [CHANGES.md](CHANGES.md). Resumen:

- **Total**: 16 changes en 8 fases (0 Fundación, 1 Datos y acceso, 2 Dominio y catálogos, 3 Agenda de turnos MVP, 4 Notificaciones por email, 5 Salida a producción, 6 Mejora de la capa visual, 7 Extensiones).
- **Camino crítico** (7): `C-01 → C-02 → C-03 → C-08 → C-11 → C-12 → C-13`, con una cadena paralela de igual longitud `C-01 → C-02 → C-03 → C-07 → C-09 → C-10 → C-13`.
- **Estado del roadmap**: C-01 a C-15 archivados; C-15 `public-patient-booking` (reserva online con confirmación por email) archivado el 2026-11-10 en `openspec/changes/archive/2026-11-10-public-patient-booking/` (1907 tests por defecto, 378 de integración, 7 de smoke y 508 de frontend; decisiones DD-128 a DD-139), y C-16 `online-booking-expiry` (vencimiento automático) pendiente; C-14 `ui-visual-refresh` archivado el 2026-11-07 en `openspec/changes/archive/2026-11-07-ui-visual-refresh/` (446 tests de frontend, decisiones DD-117 a DD-127).
- **Changes ya archivados**: `C-01` `foundation-setup` (archivo en `openspec/changes/archive/2026-11-03-foundation-setup/`, specs principales en `openspec/specs/runtime-configuration/spec.md`, `openspec/specs/api-health/spec.md`, `openspec/specs/error-model/spec.md`, `openspec/specs/local-environment/spec.md`, `openspec/specs/quality-checks/spec.md` y `openspec/specs/frontend-shell/spec.md`). `C-03` `auth-login-rbac` (archivo en `openspec/changes/archive/2026-11-03-auth-login-rbac/`, specs principales nuevas en `openspec/specs/user-authentication/spec.md`, `openspec/specs/access-control/spec.md`, `openspec/specs/user-account-repository/spec.md` y `openspec/specs/frontend-auth/spec.md`; modificadas `openspec/specs/error-model/spec.md` y `openspec/specs/frontend-shell/spec.md`). `C-04` `user-management` (archivo en `openspec/changes/archive/2026-11-03-user-management/`, specs principales nuevas en `openspec/specs/user-management/spec.md`, `openspec/specs/professional-repository/spec.md` y `openspec/specs/frontend-user-management/spec.md`; modificadas `openspec/specs/user-account-repository/spec.md`, `openspec/specs/error-model/spec.md` y `openspec/specs/user-authentication/spec.md`; 605 tests por defecto y 193 de integración; decisiones DD-56 a DD-61). `C-05a` `crear-turno-sin-solapamientos` (recorte de C-05, 33 tests; archivo en `openspec/changes/archive/2026-09-30-crear-turno-sin-solapamientos/`, spec principal en `openspec/specs/appointment-creation/spec.md`). C-05 completo: C-05a a C-05d archivados.
  `C-05b` `calcular-slots-disponibles` (recorte de C-05, 71 tests en total con los de C-05a; archivo en `openspec/changes/archive/2026-11-03-calcular-slots-disponibles/`, specs principales en `openspec/specs/slot-availability/spec.md` y `openspec/specs/clinic-timezone/spec.md`).
  `C-05c` `completar-dominio-agenda` (recorte de C-05, 131 tests en total; archivo en `openspec/changes/archive/2026-11-03-completar-dominio-agenda/`, specs principales en `openspec/specs/schedule-validation/spec.md`, `openspec/specs/appointment-status-transitions/spec.md` y `openspec/specs/patient-booking-eligibility/spec.md`).
  `C-05d` `puertos-repositorios-dominio` (último recorte de C-05, 199 tests en total; archivo en `openspec/changes/archive/2026-11-03-puertos-repositorios-dominio/`, specs principales en `openspec/specs/appointment-repository/spec.md`, `openspec/specs/schedule-repository/spec.md`, `openspec/specs/patient-repository/spec.md` y `openspec/specs/clinic-settings-repository/spec.md`; decisiones DD-31 a DD-36; `mypy --strict app/` limpio; mypy y ruff ya están en `pyproject.toml` y Python 3.12 se verifica en el contenedor (resuelto en C-01)).
  `C-09` `agenda-views` (archivo en `openspec/changes/archive/2026-11-05-agenda-views/`; specs principales nuevas en `openspec/specs/frontend-agenda/spec.md`; modificadas `openspec/specs/appointment-api/spec.md`, `openspec/specs/appointment-use-cases/spec.md` y `openspec/specs/frontend-auth/spec.md`; 1349 tests por defecto, 279 de integración y 249 de frontend; decisiones DD-79 a DD-83).
  `C-10` `appointment-management-ui` (archivo en `openspec/changes/archive/2026-11-06-appointment-management-ui/`; specs principales nuevas en `openspec/specs/frontend-appointment-management/spec.md`; modificadas `openspec/specs/frontend-agenda/spec.md`; 379 tests de frontend; decisiones DD-84 a DD-86).
  `C-11` `email-confirmation-infra` (archivo en `openspec/changes/archive/2026-11-06-email-confirmation-infra/`; specs principales nuevas en `openspec/specs/email-sending/spec.md`, `openspec/specs/email-templates/spec.md`, `openspec/specs/notification-sending/spec.md` y `openspec/specs/notification-tasks/spec.md`; modificadas `openspec/specs/clinic-settings-repository/spec.md`, `openspec/specs/database-schema/spec.md`, `openspec/specs/frontend-appointment-management/spec.md`, `openspec/specs/local-environment/spec.md` y `openspec/specs/notification-registration/spec.md`; 1475 tests por defecto, 306 de integración y 380 de frontend; decisiones DD-87 a DD-95).
  `C-12` `reminders-cron` (archivo en `openspec/changes/archive/2026-11-06-reminders-cron/`; specs principales nuevas en `openspec/specs/reminder-scheduling/spec.md`; modificadas `openspec/specs/appointment-repository/spec.md`, `openspec/specs/notification-registration/spec.md`, `openspec/specs/notification-sending/spec.md`, `openspec/specs/notification-tasks/spec.md` y `openspec/specs/local-environment/spec.md`; 1548 tests por defecto, 331 de integración y 380 de frontend; decisiones DD-96 a DD-103).
  `C-13` `deploy-and-hardening` (archivo en `openspec/changes/archive/2026-11-07-deploy-and-hardening/`; specs principales nuevas en `openspec/specs/demo-packaging/spec.md`, `openspec/specs/access-logging/spec.md` y `openspec/specs/end-to-end-smoke/spec.md`; modificadas `openspec/specs/local-environment/spec.md`, `openspec/specs/api-health/spec.md`, `openspec/specs/runtime-configuration/spec.md` y `openspec/specs/access-control/spec.md`; 1713 tests por defecto, 331 de integración, 6 de smoke y 392 de frontend; decisiones DD-104 a DD-116).
  `C-15` `public-patient-booking` (archivo en `openspec/changes/archive/2026-11-10-public-patient-booking/`; specs principales nuevas en `openspec/specs/public-booking/spec.md`, `openspec/specs/public-booking-api/spec.md` y `openspec/specs/frontend-public-booking/spec.md`; modificadas `openspec/specs/access-control/spec.md`, `openspec/specs/database-schema/spec.md`, `openspec/specs/appointment-api/spec.md`, `openspec/specs/appointment-use-cases/spec.md`, `openspec/specs/frontend-auth/spec.md`, `openspec/specs/frontend-agenda/spec.md`, `openspec/specs/frontend-appointment-management/spec.md`, `openspec/specs/reminder-scheduling/spec.md`, `openspec/specs/notification-tasks/spec.md`, `openspec/specs/email-templates/spec.md` y `openspec/specs/runtime-configuration/spec.md`; 1907 tests por defecto, 378 de integración, 7 de smoke y 508 de frontend; decisiones DD-128 a DD-139).
  `C-02` `db-schema-and-seed` (archivo en `openspec/changes/archive/2026-11-03-db-schema-and-seed/`; specs principales nuevas `openspec/specs/database-schema/spec.md` y `openspec/specs/seed-data/spec.md`; modificadas `openspec/specs/appointment-repository/spec.md`, `openspec/specs/schedule-repository/spec.md`, `openspec/specs/patient-repository/spec.md` y `openspec/specs/clinic-settings-repository/spec.md`; 315 tests por defecto y 151 de integración).
  `C-08` `appointment-use-cases` (archivo en `openspec/changes/archive/2026-11-03-appointment-use-cases/`; specs principales nuevas en `openspec/specs/appointment-use-cases/spec.md`, `openspec/specs/appointment-api/spec.md`, `openspec/specs/appointment-unit-of-work/spec.md` y `openspec/specs/notification-registration/spec.md`; modificadas `openspec/specs/error-model/spec.md` y `openspec/specs/access-control/spec.md`; 876 tests por defecto y 221 de integración; decisiones DD-62 a DD-67).
  `C-07` `professional-schedules` (archivo en `openspec/changes/archive/2026-11-04-professional-schedules/`; specs principales nuevas en `openspec/specs/schedule-conflicts/spec.md`, `openspec/specs/professional-schedule-use-cases/spec.md`, `openspec/specs/professional-schedule-api/spec.md` y `openspec/specs/frontend-professional-schedules/spec.md`; modificadas `openspec/specs/professional-repository/spec.md`, `openspec/specs/schedule-repository/spec.md` y `openspec/specs/error-model/spec.md`; 1101 tests por defecto, 237 de integración y 117 de frontend; decisiones DD-68 a DD-72).
  `C-06` `patients-crud` (archivo en `openspec/changes/archive/2026-11-04-patients-crud/`; specs principales nuevas en `openspec/specs/patient-data-rules/spec.md`, `openspec/specs/patient-management/spec.md`, `openspec/specs/patient-api/spec.md` y `openspec/specs/frontend-patient-management/spec.md`; modificadas `openspec/specs/patient-repository/spec.md` y `openspec/specs/error-model/spec.md`; 1320 tests por defecto, 277 de integración y 160 de frontend; decisiones DD-73 a DD-78).

**Antes de cualquier `/opsx:propose`**: leé [CHANGES.md](CHANGES.md), identificá las dependencias del change y los archivos de "Leer antes".

---

## Reglas Duras (específicas del proyecto)

> Reglas globales ya definidas en `~/.claude/CLAUDE.md` (orquestador, governance, TDD, engram): el proyecto las hereda. Acá viven solo las reglas **específicas de este proyecto** + las universales que el global no cubra.

**Stack y arquitectura**

1. Python con type hints en todo el código; en el frontend, TypeScript estricto, sin `any`.
2. NUNCA importar FastAPI, SQLAlchemy, Celery ni Redis desde `domain/` → funciones puras; el I/O solo va en `infrastructure/`.
3. La no superposición de turnos se garantiza con el constraint de exclusión en la migración de Alembic y se valida también en el dominio; NUNCA confiar solo en la aplicación.
4. Todo endpoint exige JWT y chequeo de rol (`require_role`), salvo el login, el chequeo de salud público (`GET /api/v1/health`, que solo responde `{"status": "ok"}` sin datos) y los cuatro endpoints de turnos online bajo `/api/v1/public/` (C-15: profesionales, franjas, reservar y confirmar), que no usan sesión pero llevan límite de pedidos por IP, validación estricta y campo trampa en la reserva, nunca devuelven datos de pacientes y nunca modifican una ficha existente; cada endpoint protegido lleva su test de permisos por rol y cada endpoint público, su test de acceso sin token y de límite de pedidos.
5. NUNCA commitear `.env` ni claves → solo `.env.example`; los secretos (`JWT_SECRET_KEY`, `SMTP_PASSWORD`, base de datos) jamás van al frontend ni a variables `VITE_`.

**Regla de dominio**

6. NUNCA permitir que un profesional tenga dos turnos superpuestos: la regla se valida en el código y además la base de datos la bloquea; todo cambio en la agenda debe incluir un test de ese caso.

**Universales (no cubiertas por el global)**

7. NUNCA commitear ni pushear sin pedido explícito del usuario → proponer el mensaje y esperar.
8. NUNCA agregar `Co-Authored-By` ni marca de IA en commits o PRs.
9. Verificar con pytest, Vitest, typecheck y lint; levantar Docker solo para los tests de integración.

---

## Flujo de Trabajo

```
1. Leer la KB relevante (knowledge-base/)        → entender el dominio
2. Identificar el change en CHANGES.md           → respetar dependencias
3. /opsx:propose C-NN-nombre                     → proposal + design + specs + tasks
4. Implementar las tasks (cargando skills)       → respetando las reglas duras
5. /opsx:archive C-NN-nombre + marcar [x]        → cerrar el change
```

Aplicar TODAS las reglas duras en cada paso. Ante conflicto entre la KB y este archivo, las reglas duras prevalecen.
