# CHANGES — Secuencia de Implementación

> Índice canónico de todos los changes del proyecto Sistema Odontológico (agenda de turnos + recordatorios por email).
> Stack definido por la cátedra: Python + FastAPI, JWT, SQLAlchemy, PostgreSQL, Redis y Docker en el backend; React + TypeScript + Vite en el frontend.
> Cada change es atómico: un agente puede implementarlo en una sesión (~4-6 horas).
> **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**

Stack: FastAPI + SQLAlchemy + PostgreSQL + Redis (Celery) + Docker Compose; React + TypeScript + Vite. Prioridad de calidad: mantenibilidad (capas domain / application / infrastructure). Todo gratuito, datos de pacientes ficticios.

---

## Cómo usar este documento

1. Identificá el próximo change con `Estado: [ ]` cuyas dependencias estén todas en `[x]` (usá los GATES de abajo).
2. Leé los archivos de la sección **Leer antes** del change (y su Scope) antes de proponer.
3. Ejecutá `/opsx:propose C-NN-nombre` y luego `/opsx:apply`.
4. Al terminar y validar, ejecutá `/opsx:archive C-NN-nombre`.
5. Marcá el checkbox `[x]` en el **Estado** del change en este archivo.

---

## Árbol de dependencias

```
C-01 foundation-setup     [x] archivado (2026-11-03)
 ├── C-02 db-schema-and-seed        [x] archivado (2026-11-03)
 │    └── C-03 auth-login-rbac            [x] archivado (2026-11-03)
 │         ├── C-04 user-management           [x] archivado (2026-11-03)
 │         ├── C-06 patients-crud               [x] archivado (2026-11-04)
 │         ├── C-07 professional-schedules      [x] archivado (2026-11-04)  (+ C-05)
 │         │    └── C-09 agenda-views           [x] archivado (2026-11-05)  (+ C-05, C-08)
 │         └── C-08 appointment-use-cases       [x] archivado (2026-11-03)  (+ C-05)
 │              ├── C-11 email-confirmation-infra  [x] archivado (2026-11-06)  (+ C-08)
 │              │    └── C-12 reminders-cron
 │              └── C-10 appointment-management-ui   [x] archivado (2026-11-06)  (+ C-06, C-09)
 └── C-05 domain-scheduling-core   (funciones puras, no requiere BD)   [x] completo
      ├── C-05a crear-turno-sin-solapamientos   [x] archivado (primer recorte de C-05)
      ├── C-05b calcular-slots-disponibles      [x] archivado (segundo recorte de C-05)
      ├── C-05c completar-dominio-agenda        [x] archivado (tercer recorte de C-05)
      └── C-05d puertos-repositorios-dominio    [x] archivado (cuarto y último recorte de C-05)

C-13 deploy-and-hardening  ← C-04, C-10, C-12
```

### Paralelismo por fase

```
GATE 0: C-01 ✓                                  ← FORK
  → C-02 db-schema-and-seed                [Agente A]
  → C-05 domain-scheduling-core            [Agente B]  (puro, sin BD)

GATE 1: C-02 ✓
  → C-03 auth-login-rbac                   [Agente A]
  → (C-05 continúa)                        [Agente B]

GATE 2: C-03 ✓ y C-05 ✓                         ← FORK
  → C-08 appointment-use-cases             [Agente A]
  → C-07 professional-schedules            [Agente B]
  → C-06 patients-crud                     [Agente C]

GATE 3: C-07 ✓ (C-08 ✓ archivado)              ← FORK
  → C-11 email-confirmation-infra          [Agente A — si C-08 ✓]
  → C-09 agenda-views                      [Agente B — si C-07 ✓ y C-08 ✓ (consume sus lecturas)]
  → C-04 user-management                   [Agente C — si C-03 ✓]

GATE 4: C-11 ✓, C-09 ✓, C-06 ✓
  → C-12 reminders-cron                    [Agente A]
  → C-10 appointment-management-ui         [Agente C — si C-08 ✓, C-09 ✓, C-06 ✓]

GATE 5: C-04 ✓, C-10 ✓, C-12 ✓
  → C-13 deploy-and-hardening              [Agente A]
```

### Camino crítico (7 changes — mínimo irreducible)

```
C-01 → C-02 → C-03 → C-08 → C-11 → C-12 → C-13*
C-01 → C-02 → C-03 → C-07 → C-09 → C-10 → C-13*   (cadena de igual longitud)
```

`*` C-13 es el último de ambas cadenas. Quedan fuera del camino crítico C-04 (gestión de usuarios: se puede sembrar por seed) y C-06 (ABM de pacientes se ejecuta en paralelo con C-07/C-08).

### Plan óptimo con 3 agentes

| Paso | Agente A (Backend Core) | Agente B (Backend Aux / Dominio) | Agente C (Frontend) |
|------|-------------------------|----------------------------------|---------------------|
| 1 | C-01 | — | — |
| 2 | C-02 | C-05 | — |
| 3 | C-03 | (cierra C-05 si falta) | — |
| 4 | C-08 | C-07 | C-06 |
| 5 | C-11 | C-09 | C-04 |
| 6 | C-12 | — | C-10 |
| 7 | C-13 | — | — |

---

## FASE 0 — Fundación

### [C-01] `foundation-setup`
- **Estado**: `[x]` implementado y archivado el 2026-11-03: 38/38 tasks (todas verificadas, incluidas las de Docker); 262 tests; mypy --strict y ruff limpios en `app` y `tests`; Docker Compose con los 7 servicios verificado; frontend con Vitest; tests del backend en Python 3.12 dentro del contenedor. Celery confirmado por el usuario (P-1 / DD-10). `GET /api/v1/health` público. TypeScript fijado en ~5.9 y ESLint en lugar de oxlint.
- **Scope**:
  - Estructura del repositorio: `backend/` (FastAPI con `app/{api,domain,application,infrastructure,core}`, `alembic/`, `scripts/`, `tests/`) y `frontend/` (React + TypeScript + Vite)
  - `docker-compose.yml` con los servicios `db` (PostgreSQL), `redis`, `api`, `worker`, `beat`, `frontend` y `mailpit`; Dockerfiles de backend y frontend; un comando levanta todo
  - pytest configurado (unit de dominio + carpeta de integración) y Vitest en el frontend; lint y format (ruff y eslint)
  - `.env.example` con todas las variables de la tabla de `08_arquitectura_propuesta.md` §Variables de entorno; configuración validada con Pydantic Settings; `.env` ignorado por git
  - `app/core/errors.py` (errores de dominio tipados) y endpoint de salud `GET /api/v1/health`
  - Riesgo a registrar: elegir el proveedor SMTP gratuito de demo y verificar su cupo (SU-02); confirmar Celery con la cátedra (DD-10). Celery ya quedó confirmado por el usuario; SU-02 sigue abierto para C-11
- **Dependencias**: ninguna
- **Governance**: BAJO
- **Artefactos**:
  - Change archivado: `openspec/changes/archive/2026-11-03-foundation-setup/` (proposal, design, tasks y specs)
  - Specs principales (capabilities nuevas): `openspec/specs/runtime-configuration/spec.md`, `openspec/specs/api-health/spec.md`, `openspec/specs/error-model/spec.md`, `openspec/specs/local-environment/spec.md`, `openspec/specs/quality-checks/spec.md` y `openspec/specs/frontend-shell/spec.md`
- **Nota**: `uvicorn --reload` en el compose de desarrollo mantiene vivo el contenedor `api` aunque falle la configuración. El error sale en el log y el servicio no llega a `healthy`.
- **Leer antes**:
  - `knowledge-base/02_descripcion_general.md` §Stack
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios, §Variables de entorno
  - `knowledge-base/09_decisiones_y_supuestos.md` (DD-01, DD-10 a DD-13)
  - `knowledge-base/01_vision_y_objetivos.md`
---

## FASE 1 — Datos y acceso

### [C-02] `db-schema-and-seed`
- **Estado**: `[x]` implementado, verificado y archivado el 2026-11-03 (`openspec/changes/archive/2026-11-03-db-schema-and-seed/`): 39/39 tasks; 315 tests por defecto y 151 de integración contra PostgreSQL en el contenedor; `alembic upgrade head` y el seed verificados en la base de desarrollo, seed idempotente. Specs principales nuevas: `database-schema` y `seed-data`; modificadas: `appointment-repository`, `schedule-repository`, `patient-repository` y `clinic-settings-repository`. 8 tablas, 4 enumerados y el constraint de exclusión en `alembic/versions/0001_initial_schema.py`; seed `backend/scripts/seed.py`; hash argon2 en `app/core/security.py`; repositorios PostgreSQL en `app/infrastructure/db/repositories/` y fábrica `postgres` en la batería de contrato (corre con `pytest -m integration`). Decisiones DD-37 a DD-44.
- **Cerrado en C-08**: test de concurrencia con dos sesiones simultáneas contra PostgreSQL y unidad de trabajo que agrupa turno y notificación (DD-36, cerrado con DD-62).
- **Scope**:
  - Modelos SQLAlchemy 2.0 y migraciones Alembic: extensión `btree_gist`; enums `user_role`, `appointment_status`, `notification_kind`, `notification_status`
  - Migración inicial escrita a mano: `CREATE EXTENSION IF NOT EXISTS btree_gist` antes de crear `appointments`; `downgrade` elimina constraint, tablas y tipos enum; revisar siempre el autogenerate (no genera bien `ExcludeConstraint` con `tstzrange` y `WHERE`)
  - Tablas `users`, `professionals`, `working_hours`, `time_off`, `patients`, `appointments`, `email_notifications`, `clinic_settings` con todos los CHECK/UNIQUE/FK del modelo
  - `appointments`: `ExcludeConstraint` equivalente a `EXCLUDE USING gist (professional_id WITH =, tstzrange(starts_at, ends_at) WITH &&) WHERE (status = 'scheduled')`; índices `(professional_id, starts_at)` y `(starts_at)`
  - `email_notifications`: `UNIQUE (appointment_id, kind, appointment_starts_at)`
  - `backend/scripts/seed.py` (idempotente): 1 admin, 1 recepción, 2 profesionales con `working_hours` L-V, `clinic_settings` (nombre, dirección y teléfono ficticios, 30 min, `America/Argentina/Buenos_Aires`, hora 9), 10 pacientes ficticios con emails `@example.com`; contraseñas de prueba ficticias
  - Tests de integración contra PostgreSQL real (contenedor): el constraint de exclusión rechaza solapamiento `scheduled`, permite solapar con `cancelled` y permite turnos pegados (rango `[)`); UNIQUE de notificaciones; CHECK de horarios
  - Fuera de C-05d (`puertos-repositorios-dominio`): repositorios SQLAlchemy de los puertos de turnos, horarios, licencias, pacientes y configuración del consultorio, con su fábrica en la batería de contrato de `backend/tests/contract/` (hoy solo corre con `in_memory`)
- **Dependencias**: `C-01`
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` (completo, §appointments y §email_notifications)
  - `knowledge-base/05_reglas_de_negocio.md` §RN-TU, §RN-NO-03, §RN-GL-01
  - `knowledge-base/10_preguntas_abiertas.md` (zona horaria SU-01, slot real)
  - `.claude/skills/supabase-postgres-best-practices/` (solo lo de PostgreSQL general; ignorar lo específico de Supabase y de RLS)
### [C-03] `auth-login-rbac`
- **Estado**: `[x]` implementado, verificado y archivado el 2026-11-03 (`openspec/changes/archive/2026-11-03-auth-login-rbac/`): 48/48 tasks; 424 tests por defecto, 161 de integración contra PostgreSQL en el contenedor y 40 de frontend; `mypy --strict`, `ruff`, `tsc` y `eslint` limpios; probado a mano con los cuatro usuarios del seed, contraseña incorrecta y cuenta desactivada. Specs principales nuevas: `user-authentication`, `access-control`, `user-account-repository` y `frontend-auth`; modificadas: `error-model` y `frontend-shell`. Decisiones DD-45 a DD-55; SU-06 y SU-07 resueltos. Sin variables de entorno nuevas; dependencias nuevas: `PyJWT` y `react-router`.
- **Nota para C-08 (cumplida en C-08)**: test de punta a punta obligatorio "un odontólogo no ve ni modifica turnos ajenos" (403) contra el endpoint real, usando `require_professional_access` o `can_access_professional` (DD-53); hoy solo está probado con una ruta que existe únicamente en los tests.
- **Nota para C-04 (hecha en C-04)**: rehash con `check_needs_rehash` al iniciar sesión (el repositorio de cuentas de C-03 es solo lectura); toda ruta nueva debe depender de `current_user` o `require_role(...)` (el test de inventario `tests/unit/api/test_route_inventory.py` falla si no).
- **Scope**:
  - `POST /api/v1/auth/login` (email + contraseña): verifica el hash, rechaza `users.active = false` y devuelve un JWT de acceso con el rol (US-001, RN-AU-03); error genérico en credenciales inválidas
  - `GET /api/v1/auth/me`; seguridad en `app/core/security.py` (hash argon2 o bcrypt, firma y verificación de JWT, expiración corta)
  - Dependencias de FastAPI `current_user()` y `require_role(...)`: todo endpoint salvo el login exige JWT válido (RN-AU-01); `current_user()` recarga el usuario desde la base en cada request y rechaza `active = false` y cambios de rol (el token no es la fuente de verdad del rol); matriz RBAC de `03_actores_y_roles.md`; odontólogo restringido a lo propio (RN-AU-04)
  - Librerías mantenidas: PyJWT y argon2-cffi (evitar python-jose y passlib, sin mantenimiento)
  - Frontend: pantalla `/login`, guardado del token en memoria o sessionStorage (riesgo de XSS aceptado y documentado), rutas protegidas y redirección a `/agenda` según rol
  - Sin RLS: la autorización vive solo en la aplicación (DD-02), por eso cada endpoint lleva su test de permisos
  - Tests: login válido/inválido/inactivo, token vencido, acceso por rol, dentist no lee turnos ajenos
- **Dependencias**: `C-02`
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §RBAC
  - `knowledge-base/05_reglas_de_negocio.md` §RN-AU, §RN-PR
  - `knowledge-base/07_flujos_principales.md` §Flujo 1
  - `knowledge-base/08_arquitectura_propuesta.md` §Seguridad
  - `knowledge-base/10_preguntas_abiertas.md` (quién edita horarios, SU-06; refresh token, SU-07)
### [C-04] `user-management`
- **Estado**: `[x]` implementado, verificado y archivado el 2026-11-03 (`openspec/changes/archive/2026-11-03-user-management/`): 45/45 tasks; 605 tests por defecto, 193 de integración contra PostgreSQL en el contenedor y 85 de frontend; `mypy --strict`, `ruff`, `tsc` y `eslint` limpios; probado contra el API real (alta de odontóloga, login, desactivar, reactivar, 422 sin eco de la contraseña). Specs principales nuevas: `user-management`, `professional-repository` y `frontend-user-management`; modificadas: `user-account-repository`, `error-model` y `user-authentication`. Decisiones DD-56 a DD-61 (P-1 a P-14 confirmadas con la opción recomendada). Sin migraciones, variables de entorno ni dependencias nuevas.
- **Nota para C-07 y C-08** (C-07 hecho): el repositorio de profesionales (`ProfessionalRepository`: `list(only_active=...)` y `get_by_id`) ya existe, en memoria y PostgreSQL, sin endpoints; C-08 debe listar solo fichas activas. Desactivar un odontólogo desactiva su ficha pero NO toca sus turnos (DD-59): C-08/C-10 deben contemplar turnos futuros de fichas inactivas. Editar la ficha (nombre a mostrar, matrícula) quedó en C-07 (hecho).
- **Scope**:
  - US-002: endpoints `/api/v1/users` (solo admin) y pantalla `/usuarios`: crear, editar rol, desactivar usuarios
  - Validación con Pydantic; contraseña inicial con hash, nunca expuesta en respuestas (RN-PR-03)
  - Al crear un usuario `dentist` se crea su fila `professionals` asociada en la misma operación
  - Caso de uso `gestionar_usuarios` con chequeo `require_role('admin')`
  - Tests: solo admin accede; alta de dentist crea professional; desactivar bloquea login
  - Fuera de C-05d: repositorio de usuarios (listado, alta, desactivación) y repositorio de profesionales (listado, activo), ambos definidos en C-04
- **Dependencias**: `C-03`
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §RBAC
  - `knowledge-base/06_funcionalidades.md` §US-002
  - `knowledge-base/05_reglas_de_negocio.md` §RN-AU-02, §RN-AU-03
  - `knowledge-base/04_modelo_de_datos.md` §users, §professionals
---

## FASE 2 — Dominio y catálogos

> C-05 no depende de la base de datos: corre en paralelo con C-02/C-03 (GATE 0).

### [C-05] `domain-scheduling-core`
- **Estado**: `[x]` completo: C-05a, C-05b, C-05c y C-05d están implementados y archivados (ver entradas propias más abajo). Los puertos de repositorio y los repos en memoria quedaron en C-05d; la persistencia SQLAlchemy y los casos de uso se reparten en C-02, C-04, C-06, C-07, C-08, C-11 y C-12.
- **Nota**: C-05 se ejecuta por recortes (sub-changes). Los archivados son C-05a, C-05b, C-05c y C-05d. C-01 extiende el esqueleto de C-05a sin rehacerlo.
- **Scope**:
  - `app/core/timezone.py`: conversión UTC <-> zona del consultorio (RN-GL-01), inicio/fin de día local
  - `app/domain/schedules`: validación de tramos (`start < end`, sin superposición, RN-HO-02); `is_date_in_time_off`
  - `app/domain/appointments`: `compute_slots(*, professional_id, day, working_hours, time_off, existing_appointments, slot_minutes=30, timezone="America/Argentina/Buenos_Aires") -> list[Slot]` (franjas del día local completo, con inicio y fin en UTC y estado libre / ocupado / fuera de horario; firma definida en C-05b); `validate_appointment` (RN-TU-01 a RN-TU-04 y RN-TU-12: grilla, dentro de tramo, fuera de licencia, anticipación mínima que incluye no pasado, sin solape); transiciones de estado (RN-TU-05, RN-TU-07)
  - `app/domain/patients`: regla de paciente inactivo (RN-PA-04)
  - Puertos (interfaces) de repositorios + repos en memoria para tests
  - Tests pytest exhaustivos (puros, sin base ni red): bordes de tramos, cambio de día por zona horaria, licencias, turnos pegados
- **Dependencias**: `C-01`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §RN-HO, §RN-TU, §RN-GL-01
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones aplicados
  - `knowledge-base/07_flujos_principales.md` §Flujo 2, §Flujo 5
  - `knowledge-base/10_preguntas_abiertas.md` (duración fija de slot, varios turnos por día SU-05, zona horaria SU-01)

### [C-05a] `crear-turno-sin-solapamientos` (recorte ya ejecutado de C-05)
- **Estado**: `[x]` implementado, verificado y archivado el 2026-09-30 (33 tests de pytest en verde)
- **Scope** (lo que cubrió):
  - `validate_appointment` en `backend/app/domain/appointments`: dado un profesional, su horario, sus licencias y sus turnos, responde si se puede crear un turno, con un solo motivo de rechazo en orden fijo: anticipación mínima de 6 horas (DD-14), grilla de 30 minutos, dentro del horario de trabajo, fuera de licencia y sin solapamiento (RN-TU-01 a RN-TU-04, RN-TU-12)
  - Los turnos pegados (uno empieza cuando termina otro) no se consideran solapados
  - Arranque mínimo del backend: `backend/pyproject.toml` y esqueleto `backend/app/domain/`
- **Dependencias**: ninguna
- **Governance**: MEDIO
- **Artefactos**:
  - Change archivado: `openspec/changes/archive/2026-09-30-crear-turno-sin-solapamientos/` (proposal, design, tasks y specs)
  - Spec principal: `openspec/specs/appointment-creation/spec.md`
  - Evidencia del flujo: `docs/opsx/explore-crear-turno-sin-solapamientos.md` y `docs/opsx/verify-crear-turno-sin-solapamientos.md`
- **Queda para C-05b en adelante**: `compute_slots`, zona horaria (`app/core/timezone.py`), validación de tramos y licencias, transiciones de estado, regla de paciente inactivo y puertos de repositorios (ver C-05)

### [C-05b] `calcular-slots-disponibles` (recorte de C-05, archivado)
- **Estado**: `[x]` implementado y archivado el 2026-11-03: 44/44 tasks, 71 tests pasando (33 de C-05a + 38 nuevos). Typecheck y lint resueltos en C-01: mypy y ruff están en `pyproject.toml` y limpios; la verificación en Python 3.12 se hizo en el contenedor.
- **Scope**:
  - `compute_slots`: clasifica cada franja del día local completo de un profesional como `FREE` / `BUSY` / `OUTSIDE_HOURS`, con inicio y fin en UTC. Solo ocupan los turnos `scheduled`; la licencia sale `OUTSIDE_HOURS`; no aplica anticipación mínima (la sigue rechazando `validate_appointment`)
  - `app/core/timezone.py`: conversión UTC <-> zona del consultorio, inicio y fin del día local (RN-GL-01); se asume una zona sin horario de verano (SU-01, sin confirmar)
  - Refactor de C-05a: extraer helpers compartidos de `validation.py`, con sus 33 tests en verde como red de seguridad
  - Entradas inválidas (`slot_minutes <= 0`, `day` inválido) lanzan `ValueError`
  - Sin base de datos, pantallas, login ni emails
- **Dependencias**: `C-05a` (reutiliza tipos, grilla y reglas de solapamiento)
- **Governance**: MEDIO
- **Artefactos**:
  - Change archivado: `openspec/changes/archive/2026-11-03-calcular-slots-disponibles/` (proposal, design, tasks y specs)
  - Specs principales: `openspec/specs/slot-availability/spec.md` y `openspec/specs/clinic-timezone/spec.md` (31 escenarios)
  - Explore: `docs/opsx/explore-calcular-slots-disponibles.md`
  - Evidencias de la skill y del MCP usados en la preparación: `docs/skills-mcp/evidencias/aplicacion/`
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §RN-HO, §RN-TU, §RN-GL-01
  - `knowledge-base/10_preguntas_abiertas.md` (zona horaria SU-01, slot real)
  - `openspec/changes/archive/2026-11-03-calcular-slots-disponibles/design.md`

### [C-05c] `completar-dominio-agenda` (recorte de C-05, archivado)
- **Estado**: `[x]` implementado y archivado el 2026-11-03: 26/26 tasks, 131 tests pasando en total. `openspec validate --strict` OK y `openspec validate --all` OK. Sin tope de horario (DD-26). Decisiones de dominio DD-21 a DD-30 confirmadas por el usuario. Typecheck: `mypy --strict` sobre `app/` está limpio; mypy y ruff quedaron en `pyproject.toml` en C-01 (resuelto).
- **Scope**:
  - `app/domain/schedules`: validación de tramos (`start < end`, sin superposición, RN-HO-02), día de la semana dentro de rango (RN-HO-01), horas en minutos exactos, validez de licencias e `is_date_in_time_off` con fecha local (RN-HO-03)
  - `app/domain/appointments`: transiciones de estado (RN-TU-05, RN-TU-06, RN-TU-07): matriz de transiciones permitidas, marcar atendido o ausente solo con el turno ya iniciado, cancelar solo antes del inicio, y turnos que admiten reprogramación
  - `app/domain/patients`: paciente inactivo no recibe turnos nuevos (RN-PA-04), como regla separada de la validación del horario
  - Sin base de datos, pantallas, login ni emails
- **Dependencias**: `C-05b` (reutiliza tipos, grilla y reglas de solapamiento)
- **Governance**: MEDIO
- **Artefactos**:
  - Change archivado: `openspec/changes/archive/2026-11-03-completar-dominio-agenda/` (proposal, design, tasks y specs)
  - Specs principales: `openspec/specs/schedule-validation/spec.md`, `openspec/specs/appointment-status-transitions/spec.md` y `openspec/specs/patient-booking-eligibility/spec.md` (capabilities nuevas)
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §RN-HO, §RN-TU, §RN-PA
  - `knowledge-base/09_decisiones_y_supuestos.md` (DD-21 a DD-30)
  - `openspec/changes/archive/2026-11-03-completar-dominio-agenda/design.md`

### [C-05d] `puertos-repositorios-dominio` (último recorte de C-05, archivado)
- **Estado**: `[x]` implementado y archivado el 2026-11-03: 31/31 tasks, 199 tests pasando en total (131 de C-05a a C-05c + 68 nuevos). `mypy --strict app/` limpio (30 archivos); sin imports de fastapi, sqlalchemy, celery ni redis en `domain/` ni `infrastructure/`. Decisiones DD-31 a DD-36 confirmadas por el usuario. mypy y ruff quedaron en `pyproject.toml` en C-01 (resuelto); la verificación en Python 3.12 se hizo en el contenedor de C-01.
- **Scope**:
  - Puertos (`typing.Protocol`, sin dependencias de infraestructura) para turnos, horarios y licencias, pacientes (solo `get(id)`) y configuración del consultorio (solo lectura: duración del slot, zona horaria y anticipación mínima)
  - Tipos con identidad (`Appointment`, `TimeOffEntry`, `Patient`, `ClinicSettings`) y errores de dominio `SlotTakenError` (`SLOT_TAKEN`) y `AppointmentNotFoundError` (`APPOINTMENT_NOT_FOUND`) en `app/domain/appointments/errors.py`
  - Repositorios en memoria en `app/infrastructure/in_memory/`: rechazan dos turnos `scheduled` superpuestos del mismo profesional al guardar y al reprogramar, con la regla única `overlaps_scheduled` de `rules.py` (RN-TU-01); listados por rango semiabierto, por profesional o por paciente, con todos los estados
  - Batería de contrato compartida en `backend/tests/contract/`, parametrizada por fábrica (hoy solo `id="in_memory"`)
  - Sin base de datos, modelos SQLAlchemy, migraciones, casos de uso ni pantallas
- **Dependencias**: `C-05c` (reutiliza tipos, reglas de solapamiento y bordes del día local)
- **Governance**: MEDIO
- **Artefactos**:
  - Change archivado: `openspec/changes/archive/2026-11-03-puertos-repositorios-dominio/` (proposal, design, tasks y specs)
  - Specs principales: `openspec/specs/appointment-repository/spec.md`, `openspec/specs/schedule-repository/spec.md`, `openspec/specs/patient-repository/spec.md` y `openspec/specs/clinic-settings-repository/spec.md`
- **Leer antes**:
  - `knowledge-base/09_decisiones_y_supuestos.md` (DD-31 a DD-36)
  - `knowledge-base/05_reglas_de_negocio.md` §RN-TU, §RN-PA-04
  - `openspec/changes/archive/2026-11-03-puertos-repositorios-dominio/design.md`
- **Fuera de C-05d**: repartido en C-02, C-04, C-06, C-07, C-08, C-11 y C-12 (ver cada entrada).

### [C-06] `patients-crud`
- **Estado**: `[x]` implementado, verificado y archivado el 2026-11-04 (`openspec/changes/archive/2026-11-04-patients-crud/`): 40/40 tasks; 1320 tests por defecto, 277 de integración contra PostgreSQL (1 omitido a propósito) y 160 de frontend; `mypy --strict app/`, `ruff`, `tsc` y `eslint` limpios; `openspec validate --strict` válido. Specs principales nuevas: `patient-data-rules`, `patient-management`, `patient-api` y `frontend-patient-management`; modificadas: `patient-repository` y `error-model`. Dominio `app/domain/patients/{errors,rules}.py`, casos de uso en `app/application/patients.py`, API en `app/api/patients.py` (siete endpoints), pantalla `/pacientes` y `PatientSearch`/`PatientForm` reutilizables. Decisiones DD-73 a DD-78. Sin migraciones, dependencias ni variables de entorno nuevas.
- **Scope**:
  - US-003: pantalla `/pacientes` en React (listado, búsqueda por apellido y documento, alta, edición, desactivación)
  - API `/api/v1/patients`, `PatientRepository` (SQLAlchemy) y casos de uso con validación Pydantic: nombre, apellido, documento y email obligatorios; documento único (RN-PA-01/02); desactivar en lugar de borrar (RN-PA-03)
  - Permisos: admin CRUD, recepción CRU, odontólogo solo lectura
  - Tests: duplicado de documento, búsqueda, desactivación, permisos por rol
  - Fuera de C-05d: alta, búsqueda por apellido o documento y unicidad del documento (RN-PA-01); extienden el `PatientRepository` de C-05d, que hoy solo tiene `get(id)` (DD-34)
- **Dependencias**: `C-03`
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §US-003
  - `knowledge-base/04_modelo_de_datos.md` §patients
  - `knowledge-base/05_reglas_de_negocio.md` §RN-PA
  - `knowledge-base/03_actores_y_roles.md` §RBAC

### [C-07] `professional-schedules`
- **Estado**: `[x]` implementado, verificado y archivado el 2026-11-04 (`openspec/changes/archive/2026-11-04-professional-schedules/`): 42/42 tasks; 1101 tests por defecto, 237 de integración contra PostgreSQL y 117 de frontend; `mypy --strict`, `ruff`, `tsc` y `eslint` limpios; `openspec validate --strict` válido; prueba manual con navegador (task 8.1) confirmada por la usuaria (aviso de conflicto al sacar el viernes a la Dra. A con un turno agendado, edición de fichas, permisos de recepción y de la Dra. A). Dominio `app/domain/schedules/conflicts.py` y `errors.py`, casos de uso en `app/application/professionals.py`, API en `app/api/professionals.py` (nueve endpoints), pantalla `/profesionales`. Specs principales nuevas: `schedule-conflicts`, `professional-schedule-use-cases`, `professional-schedule-api` y `frontend-professional-schedules`; modificadas: `professional-repository`, `schedule-repository` y `error-model`. Decisiones DD-68 a DD-72. Sin migraciones ni variables de entorno nuevas. **Nota para C-09 y C-10**: `GET /api/v1/professionals/{id}/conflicts` devuelve los turnos `scheduled` futuros fuera del horario o en licencia (calculados en el momento, DD-68); C-10 lo usa para su indicador de conflictos.
- **Scope**:
  - US-004 y US-005: `/profesionales` con listado, edición de `working_hours` (varios tramos por día) y carga de `time_off`
  - Repositorios `WorkingHoursRepository`, `TimeOffRepository`; validación con `domain/schedules` (C-05)
  - Detección de conflictos (RN-HO-04): al cambiar horarios o cargar licencia, listar turnos `scheduled` afectados sin cancelarlos
  - Permisos según matriz: solo admin edita (decisión abierta SU-06: dejar la política en un único punto para cambiarla fácil); recepción y dentist (propio) solo leen
  - Tests: tramos superpuestos rechazados, conflictos listados, licencia bloquea disponibilidad
  - Fuera de C-05d: borrar o editar licencias (sin respaldo en la KB; US-005 solo pide cargarlas). Los puertos de `schedule-repository` ya cubren leer y reemplazar tramos, y listar y agregar licencias, y sus adaptadores SQLAlchemy ya existen desde C-02; C-07 solo agrega borrar licencia y editar la ficha del profesional
- **Dependencias**: `C-03`, `C-05`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §US-004, §US-005
  - `knowledge-base/07_flujos_principales.md` §Flujo 5
  - `knowledge-base/05_reglas_de_negocio.md` §RN-HO
  - `knowledge-base/10_preguntas_abiertas.md` (quién edita horarios; aviso al paciente si hay conflicto)

---

## FASE 3 — Agenda de turnos (MVP)

### [C-08] `appointment-use-cases`
- **Estado**: `[x]` implementado, verificado y archivado el 2026-11-03 (`openspec/changes/archive/2026-11-03-appointment-use-cases/`): 46/46 tasks; 876 tests por defecto y 221 de integración contra PostgreSQL en el contenedor; `mypy --strict` y `ruff` limpios; `openspec validate --strict` válido. Casos de uso en `app/application/appointments.py`, API en `app/api/appointments.py` (siete endpoints), unidad de trabajo y registro de notificaciones en memoria y PostgreSQL. Specs principales nuevas: `appointment-use-cases`, `appointment-api`, `appointment-unit-of-work` y `notification-registration`; modificadas: `error-model` y `access-control`. Decisiones DD-62 a DD-67. Sin migraciones ni variables de entorno nuevas.
- **Scope**:
  - `AppointmentRepository` (SQLAlchemy) que traduce el error del constraint de exclusión a "el slot acaba de ocuparse"
  - Casos de uso en `app/application`: `agendar_turno`, `cancelar_turno` (con `cancel_reason`), `reprogramar_turno` (atómico: si falla no cambia el original, RN-TU-06), `marcar_atencion` (`completed`/`no_show`, solo propio, `scheduled` e iniciado)
  - Lectura mínima de paciente activo para RN-PA-04 (sin depender de la UI de C-06)
  - Puerto `NotificationPort` (no-op por defecto) invocado tras agendar/reprogramar/cancelar; C-11 lo implementa (RN-NO-04: nunca bloquea)
  - Endpoints `/api/v1/appointments` con esquemas Pydantic y chequeo de rol
  - Tests: happy path, slot ocupado, fuera de horario, pasado, concurrencia (dos inserciones simultáneas, una falla), reprogramación fallida no muta, permisos
  - Heredado de C-02: el repositorio de turnos con SQLAlchemy ya existe (`app/infrastructure/db/repositories/`, con la traducción de `23P01` a `SlotTakenError`). Hecho en C-08: test de concurrencia real con dos sesiones simultáneas contra PostgreSQL (una inserción falla) y unidad de trabajo que agrupe turno y notificación en una misma transacción (DD-36)
  - Listado de turnos de todos los profesionales por rango: pasa a C-12, que es quien lo usa (P-10 de C-08, DD-66)
  - Decisiones confirmadas el 2026-11-03 (DD-62 a DD-67): fila `confirmation` `pending` junto con el turno y despachador vacío (C-11 lo reemplaza y decide qué hacer con las `pending` viejas); consultas (ver, listar por profesional y rango) y franjas de un día incluidas en C-08, y C-09 las consume; un paciente no tiene dos turnos superpuestos (cierra H-2)
  - Pregunta abierta H-2 (paciente con dos turnos a la misma hora con profesionales distintos, SU-05 y `10_preguntas_abiertas.md`): la regla, si existe, se decide en este change
- **Dependencias**: `C-03`, `C-05`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` §Flujo 2, §Flujo 3
  - `knowledge-base/06_funcionalidades.md` §US-007 a §US-010
  - `knowledge-base/05_reglas_de_negocio.md` §RN-TU, §RN-NO-04, §RN-NO-05
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones aplicados

### [C-09] `agenda-views`
- **Estado**: `[x]` implementado, verificado y archivado el 2026-11-05 (`openspec/changes/archive/2026-11-05-agenda-views/`): 1349 tests por defecto, 279 de integración contra PostgreSQL (1 omitido) y 249 de frontend; `mypy --strict`, `ruff` y `eslint` limpios; `tsc` limpio; `openspec validate --strict` válido. Specs principales nuevas: `frontend-agenda`; modificadas: `appointment-api`, `appointment-use-cases` y `frontend-auth`. Backend: `GET /appointments` y `GET /appointments/{id}` devuelven además `patient_first_name` y `patient_last_name` (`AppointmentView` en `app/application/appointments.py`, `AppointmentViewOut` en `app/api/appointments.py`); las respuestas de agendar, cancelar, reprogramar y atención no cambian. Frontend: pantalla `/agenda` (`src/pages/AgendaPage.tsx`) con vistas Día y Semana, solo lectura; piezas reutilizables en `src/agenda/` (`grid.ts` puro, `dates.ts`, `DayColumn`, `WeekView`, `DateNavigator`, `ProfessionalPicker`, `AppNav`) y cliente `src/api/appointments.ts`. Decisiones DD-79 a DD-83 (P-1 a P-11 confirmadas, todas la opción A); DD-51 actualizada. Sin migraciones, dependencias ni variables de entorno nuevas. **Nota para C-10**: agregar las acciones sobre `DayColumn` (filas `free`, `busy` y `appointment` ya llevan el identificador del turno y de la franja), ampliar `api/appointments.ts` con las escrituras y mostrar `INSUFFICIENT_NOTICE`/`SLOT_TAKEN`.
- **Scope**:
  - US-006: `/agenda` con vista diaria y semanal por profesional
  - Slots libres, ocupados y fuera de horario diferenciados (usa `compute_slots` de C-05 y horarios/licencias de C-07)
  - Consume los endpoints de lectura de C-08 (turnos de un profesional por rango y franjas de un día; P-9 de C-08, DD-66); no define consultas propias. **Nota (C-08 hecho)**: `GET /api/v1/appointments?professional_id&from&to` (rango `[from, to)` con zona, hasta 31 días) y `GET /api/v1/professionals/{id}/slots?date=AAAA-MM-DD`; las franjas no aplican la anticipación mínima y un profesional inactivo devuelve las suyas igual
  - Selector de profesional para admin/recepción; odontólogo ve solo la propia (RN-AU-04)
  - Pantalla de inicio por rol tras el login
  - Componentes React reutilizables (grilla de slots, navegación de fechas); datos con un cliente de API; fechas mostradas en zona del consultorio
  - Tests con Vitest: componente de grilla, filtro por rol, cambio de semana
- **Dependencias**: `C-05`, `C-07`, `C-08`
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §US-006
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios
  - `knowledge-base/03_actores_y_roles.md` §RBAC
  - `knowledge-base/05_reglas_de_negocio.md` §RN-AU-04, §RN-GL-01

### [C-10] `appointment-management-ui`
- **Estado**: `[x]` implementado, verificado y archivado el 2026-11-06 (`openspec/changes/archive/2026-11-06-appointment-management-ui/`): 379 tests de frontend (C-09 dejó 249; ningún test previo se perdió), `eslint` y `tsc` limpios. P-1 a P-9 confirmadas con la opción A (DD-84 a DD-86). Specs principales nuevas: `frontend-appointment-management`; modificadas: `frontend-agenda`. Solo frontend: `src/appointments/` (`actions.ts` y `messages.ts` puros, `BookingPanel`, `AppointmentDetail`, `CancelDialog`, `RescheduleDialog`, `ConflictsPanel`), escrituras en `src/api/appointments.ts` y acciones opcionales en `DayColumn`/`WeekView`; sin migraciones, endpoints, dependencias ni variables de entorno nuevas. **Nota para C-11**: el aviso de éxito de agendar ("Turno agendado: …") no menciona emails; C-11 puede sumar "Se envió la confirmación por email" en `bookedNotice` de `src/appointments/messages.ts`.
- **Nota de C-06 (DD-78)**: reutilizar `PatientSearch` (solo pacientes activos, `onSelect` con id y nombre) y `PatientForm` (alta y edición, `onSaved`) de `frontend/src/patients/` para "buscar o crear paciente" al agendar. Avisar que buscar sin tilde no encuentra con tilde (DD-74).
- **Scope**:
  - UI para agendar desde un slot libre (buscar/crear paciente inline con C-06), cancelar con motivo, reprogramar y marcar atendido/ausente, conectada a los casos de uso de C-08
  - Mensajes de error claros (slot ocupado, fuera de horario, pasado, paciente inactivo)
  - Indicador de conflictos por cambio de horario/licencia (RN-HO-04) con acceso directo a reprogramar/cancelar (consume `GET /api/v1/professionals/{id}/conflicts` de C-07)
  - Tests de UI/flujo: agendar, choque de slot, cancelar libera slot, reprogramar
- **Dependencias**: `C-06`, `C-08`, `C-09`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §US-007 a §US-010
  - `knowledge-base/07_flujos_principales.md` §Flujo 2, §Flujo 3, §Flujo 5
  - `knowledge-base/01_vision_y_objetivos.md` (riesgo de adopción de recepción)
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios

---

## FASE 4 — Notificaciones por email

### [C-11] `email-confirmation-infra`
- **Estado**: `[x]` implementado, verificado y archivado el 2026-11-06 (`openspec/changes/archive/2026-11-06-email-confirmation-infra/`): 54/54 tasks; 1475 tests por defecto, 306 de integración contra PostgreSQL y 380 de frontend; `ruff`, `mypy`, `tsc` y `eslint` limpios. Decisiones DD-87 a DD-95. Specs principales nuevas: `email-sending`, `email-templates`, `notification-sending` y `notification-tasks`; modificadas: `clinic-settings-repository`, `database-schema`, `frontend-appointment-management`, `local-environment` y `notification-registration` (el requisito "Aviso posterior al commit sin efecto en C-08" se quitó de esta última y su contenido pasó a `notification-tasks`).
- **Scope**:
  - **SMTP**: Mailpit en desarrollo y en la demo; el adaptador es configurable por variables `SMTP_*`, sin elegir proveedor (DD-87). SU-02 queda abierto solo para producción y no bloquea nada
  - Aplicación Celery con Redis como broker (`app/infrastructure/tasks`); servicio `worker` en Docker Compose
  - `EmailSender` (puerto) + adaptador SMTP en `app/infrastructure/email`; plantillas de `confirmation` y `reminder` (paciente, profesional, fecha/hora, dirección del consultorio)
  - Encolado después del commit con `apply_async(retry=False)` y timeout corto; tarea de Beat `reencolar_pendientes` (cada 10 minutos) para las `pending` antiguas
  - `NotificationRepository` sobre `email_notifications`; implementación de `NotificationPort` (C-08): crear fila `pending`, encolar `enviar_email`, el worker envía y marca `sent`/`failed` con `error`
  - Confirmación al agendar y reprogramar; reprogramar reemplaza el recordatorio pendiente (RN-NO-05); cancelar no genera recordatorio
  - Fallos de envío y Redis caído nunca rompen la operación de turno (RN-NO-04)
  - Tests con `EmailSender` falso y Celery en modo inmediato: éxito, fallo registrado, idempotencia por UNIQUE
  - Fuera de C-05d: datos del consultorio para los emails (nombre, dirección, teléfono y hora del recordatorio) en `ClinicSettings`; el puerto de C-05d solo expone duración, zona y anticipación mínima
  - **Lo que C-12 recibe hecho (C-11, DD-87 a DD-95)**: plantilla `reminder` y `render_email` por tipo; `deliver_notification` genérico para cualquier `kind` (toma de la fila con `FOR UPDATE SKIP LOCKED`, `sent`/`failed`, `EXPIRED`, hasta 3 intentos ante fallos temporales); `ClinicSettings` con `clinic_name`, `address`, `phone` y `reminder_send_hour`; `NotificationRepository` con `claim_pending`, `mark_sent`, `mark_failed` y `list_pending_created_before`; migración `0002` (`created_at`); `CeleryNotificationDispatcher` y `publish_send_email`; `EMAIL_REDIRECT_TO` para la demo. Una `failed` no se reintenta: la segunda pasada de `failed` y el listado de turnos de todos los profesionales por rango son de C-12
  - **Nota (C-08 hecho, DD-62)**: C-08 ya guarda la fila `confirmation` `pending` junto con el turno (agendar y reprogramar; reprogramar y cancelar borran las `pending` del horario anterior) y llama a `AgendaDeps.dispatcher` (`NotificationDispatcher.dispatch`) después del commit; hoy es `NoOpNotificationDispatcher` (`app/infrastructure/notifications.py`). C-11 reemplaza ese despachador por el encolado, reusa `NotificationRepository` (ya existe, en memoria y PostgreSQL) y decide qué hacer con las filas `pending` acumuladas desde C-08 antes de activar `reencolar_pendientes`. Un despachador que falla no rompe la operación (se registra solo el id del turno)
- **Dependencias**: `C-08`
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/11_recordatorios_email.md` §Tipos de email, §Envío asincrónico, §Idempotencia y errores, §Límites y riesgos
  - `knowledge-base/05_reglas_de_negocio.md` §RN-NO
  - `knowledge-base/07_flujos_principales.md` §Flujo 2
  - `knowledge-base/10_preguntas_abiertas.md` (proveedor SMTP de producción SU-02, Celery DD-10; el contenido de la plantilla quedó resuelto en DD-90)
### [C-12] `reminders-cron` (Celery Beat)
- **Estado**: `[x]` implementado, verificado y archivado el 2026-11-06 (`openspec/changes/archive/2026-11-06-reminders-cron/`): 44/44 tasks; 1548 tests por defecto, 331 de integración contra PostgreSQL (más 1 omitido, igual que antes) y 380 de frontend sin cambios; `ruff`, `mypy` y `mypy --strict app/` limpios. Decisiones DD-96 a DD-103. Specs nuevas: `reminder-scheduling`; modificadas: `appointment-repository`, `notification-registration`, `notification-sending`, `notification-tasks` y `local-environment`. Sin migraciones, dependencias ni variables nuevas.
- **Cómo forzar la pasada (para el smoke test de C-13)**: desde la consola del contenedor, `docker compose exec worker celery -A app.infrastructure.tasks.celery_app call enviar_recordatorios --kwargs='{"forzar": true}'`; el recordatorio de los turnos `scheduled` de mañana aparece en Mailpit (http://localhost:8025) y repetirla no reenvía nada. Beat nunca fuerza y no hay ruta HTTP (DD-101).
- **Nota de C-06 (P-8, DD-76)**: los turnos `scheduled` futuros de un paciente **inactivo** SIGUEN recibiendo recordatorio mientras no se cancelen (desactivar no los toca, DD-25); C-12 no debe saltear a los pacientes inactivos. Si recepción no quiere que el paciente venga, cancela el turno y el recordatorio no sale (RN-NO-05).
- **Scope**:
  - Tarea Celery `enviar_recordatorios` y servicio `beat` (Celery Beat) que la dispara cada hora; la tarea solo actúa cuando la hora local del consultorio es `clinic_settings.reminder_send_hour`; app Celery con `timezone` del consultorio y `enable_utc = True`; no hay endpoint HTTP
  - Caso de uso `enviar_recordatorios`: turnos `scheduled` del día siguiente (zona de `clinic_settings`, DD-99) de todos los profesionales sin `reminder` para ese horario; envía cada uno en la pasada (DD-96); un fallo se registra y el lote continúa (US-011); registra `processed`, `sent`, `failed` y `pending` en el log, sin datos del paciente
  - Sin segunda pasada de `failed` (DD-97); una hora perdida no se recupera (DD-98); todos los `scheduled` de mañana reciben recordatorio, incluidos los de profesionales inactivos y los turnos en conflicto (DD-100); opción `forzar` solo desde la consola (DD-101)
  - Tests: doble ejecución no reenvía, cancelado excluido, fallo parcial no corta el lote, borde de zona horaria, la tarea solo actúa a la hora configurada
  - Listado de turnos de todos los profesionales por rango para `enviar_recordatorios` (**no está en C-08**: P-10, DD-66; el repositorio lista por profesional o por paciente y C-12 define su filtro); datos del consultorio para los recordatorios (ver C-11)
- **Dependencias**: `C-11`
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/11_recordatorios_email.md` §Programación del recordatorio, §Tareas
  - `knowledge-base/07_flujos_principales.md` §Flujo 4
  - `knowledge-base/10_preguntas_abiertas.md` (IN-01, zona horaria)
  - `knowledge-base/06_funcionalidades.md` §US-011
---

## FASE 5 — Salida a producción

### [C-13] `deploy-and-hardening`
- **Estado**: `[ ]` pendiente
- **Nota de C-06 (P-10, DD-77)**: la búsqueda de pacientes viaja como `GET /api/v1/patients?q=...`, así que el apellido o documento buscado puede quedar en el registro de accesos del servidor web (nginx/uvicorn). Revisar ese registro (no guardar `q`, o rotarlo) antes de usar datos reales. La aplicación misma no escribe datos de pacientes en errores ni logs.
- **Scope**:
  - Dockerfile del frontend multi-stage (build con `VITE_API_URL` como build-arg, servido con nginx); en desarrollo, servidor de Vite; Mailpit solo en desarrollo
  - Empaquetado final con Docker Compose: un comando levanta `db`, `redis`, `api`, `worker`, `beat`, `frontend` y `mailpit`; migraciones y seed ficticio aplicados al iniciar
  - Variables de entorno de producción o demo (secretos solo en el servidor y fuera del repositorio, RN-PR-03); CORS limitado al frontend
  - Revisión de permisos: matriz de tests por endpoint y rol; ninguna ruta sin JWT salvo el login; ningún secreto en el bundle del frontend
  - Smoke test end-to-end: login por rol -> agendar -> email de confirmación visible en Mailpit -> cancelar -> reprogramar -> ejecución de la tarea de recordatorios
  - README con setup, comandos, variables y decisiones abiertas pendientes
  - Checklist de adopción para recepción (riesgo de negocio)
- **Dependencias**: `C-04`, `C-10`, `C-12`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/08_arquitectura_propuesta.md` §Seguridad, §Variables de entorno
  - `knowledge-base/11_recordatorios_email.md` §Límites y riesgos
  - `knowledge-base/01_vision_y_objetivos.md`
  - `knowledge-base/10_preguntas_abiertas.md`
---

## Alineación con el informe de Discovery (sección D.3)

El informe `docs/discovery/informe-discovery.md` recomienda un MVP en tres niveles. Esta tabla muestra qué cubre este roadmap y qué queda afuera, con el motivo (decisiones DD-07, DD-08 y DD-09 de `knowledge-base/09_decisiones_y_supuestos.md`).

### Imprescindible según el informe

| Recomendación del informe (D.3, Imprescindible) | Cobertura | Change | Justificación si no se cubre |
|---|---|---|---|
| Agenda multi-profesional con prevención de solapamientos | Cubierta | C-02, C-05, C-07, C-08, C-09, C-10 | — |
| Agenda multi-sillón/box con duración por prestación y bloqueos | **Parcial**: solo bloqueos por día completo (licencias) y slot fijo; sin bloqueos horarios, sin sillón/box y sin duración por prestación | C-05, C-07 | DD-03 y DD-08 (RN-TU-09, RN-TU-10): cambia el esquema y el algoritmo; primera mejora posterior |
| Reserva online por enlace, con confirmación, cancelación y reprogramación por el paciente | **No cubierta** (la recepción sí cancela y reprograma: C-08, C-10) | — | DD-07; `01_vision_y_objetivos.md` §Fuera de alcance: turnos online y login para pacientes |
| Recordatorios y confirmaciones por WhatsApp | **Parcial, sustituida por email**: recordatorio y aviso informativo; el paciente no puede confirmar ni cancelar (DD-06) | C-11, C-12 | DD-09: la API de WhatsApp Business cobra; restricción de costo cero |
| Ficha del paciente con anamnesis, odontograma, evolución y adjuntos (radiografías) | **No cubierta**: C-06 solo da el ABM de datos de contacto, base para la ficha futura | C-06 (base) | DD-07: historia clínica fuera de v1 |
| Roles y permisos básicos | Cubierta (roles fijos) | C-03, C-04 | — |
| Registro de auditoría de accesos | **No cubierta** | — | DD-07: fuera de v1. El chequeo de rol restringe accesos pero no los registra; no hay log de accesos |
| Exportación de datos | **No cubierta** | — | DD-07: fuera de v1 por alcance. El informe la marca como vacío del mercado y oportunidad de diferenciación (C.4, C.5); candidata prioritaria tras v1 |

### Diferenciadores y etapas posteriores (D.3)

Ninguno de estos 14 ítems está en el roadmap. Es coherente con el alcance v1 (DD-07) y queda registrado en `06_funcionalidades.md`.

| Nivel | Ítem del informe | Cobertura | Motivo |
|---|---|---|---|
| Diferenciador | Lista de espera con oferta de huecos liberados | No cubierta | Fuera de v1 (DD-07) |
| Diferenciador | Sobreturnos controlados | No cubierta | RN-TU-11: no se permiten en v1 |
| Diferenciador | Seña con Mercado Pago atada al turno | No cubierta | Fuera de v1 y de costo cero (DD-07) |
| Diferenciador | Panel de ausentismo y ocupación de sillón | No cubierta | Reportes excluidos en `01_vision_y_objetivos.md` §Fuera de alcance; C-08 registra `no_show` como base |
| Etapa posterior | Presupuestos y planes de tratamiento | No cubierta | Fuera de alcance (cobros y presupuestos) |
| Etapa posterior | Periodontograma | No cubierta | Depende de la ficha clínica, fuera de v1 |
| Etapa posterior | Facturación electrónica ARCA | No cubierta | Fuera de v1 |
| Etapa posterior | Obras sociales y prepagas | No cubierta | Fuera de v1 |
| Etapa posterior | Receta electrónica | No cubierta | Fuera de v1 |
| Etapa posterior | Multi-sucursal | No cubierta | SU-04: un solo consultorio |
| Etapa posterior | Reportes avanzados | No cubierta | Reportes excluidos de v1 |
| Etapa posterior | Reactivación de pacientes y campañas | No cubierta | Fuera de v1 |
| Etapa posterior | Asistente conversacional con IA | No cubierta | Fuera de v1 |
| Etapa posterior | Consentimientos con firma digital | No cubierta | Fuera de v1 |

### Changes del roadmap que el informe no pide

Ninguno agrega funcionalidades que el informe desaconseje o que el MVP excluya (historia clínica, cobros, turnos online, WhatsApp, reportes). Los 13 changes salen de funciones del MVP recomendado o de trabajo técnico necesario (C-01 fundación, C-02 base de datos, C-13 despliegue). Se apartan del informe: C-11 y C-12 usan email en lugar de WhatsApp (DD-09), y C-08 registra `no_show`, lo que deja la base para un futuro panel de ausentismo.

---

## Riesgos del roadmap

| # | Riesgo | Change afectado | Mitigación |
|---|---|---|---|
| R-1 | Proveedor SMTP de producción sin elegir | C-11, C-12, C-13 | Desarrollo y demo con Mailpit; el adaptador se configura por variables (SU-02, DD-87) |
| R-2 | Redis o el worker de Celery caídos: no salen emails ni recordatorios | C-11, C-12 | La operación de turno nunca depende del envío (RN-NO-04); `reencolar_pendientes` recoge las notificaciones `pending` |
| R-3 | La cátedra puede preferir otra herramienta distinta de Celery sobre Redis | C-01, C-11, C-12 | Confirmar con el profesor en C-01 (DD-10) |
| R-4 | Errores de zona horaria en turnos y recordatorios | C-02, C-05, C-12 | Fechas en UTC y zona del consultorio en configuración (RN-GL-01); tests de borde |
| R-5 | Concurrencia: dos recepcionistas agendan el mismo slot | C-02, C-08 | Constraint de exclusión en la base (DD-04) |
| R-6 | Módulos de gobernanza CRÍTICA (auth, esquema) y autorización solo en la aplicación, sin RLS | C-02, C-03 | Análisis y aprobación humana antes de escribir código; test de permisos por cada endpoint |
| R-7 | Sin recordatorios por WhatsApp el producto queda por debajo del estándar del mercado | C-11, C-12 | DD-09; evaluar enlace `wa.me` manual tras v1 |
| R-8 | Adopción: la recepción puede seguir usando planilla y WhatsApp | C-13 | Checklist de adopción; probar con una recepcionista real |
| R-9 | El informe se basa solo en páginas comerciales y sin demos | Todo el roadmap | Validar prioridades con odontólogos reales antes de construir funciones grandes |
| R-10 | Tratamiento legal de datos personales sin revisar (Ley 25.326; Ley 27.706 si se agrega ficha clínica) | C-02, C-06, C-13 | v1 usa solo datos ficticios; no declarar cumplimiento; revisión legal antes de usar datos reales (`10_preguntas_abiertas.md`) |
| R-11 | Migrar luego a sillón o duración variable (DD-08) exige cambiar el constraint EXCLUDE y `compute_slots` | C-02, C-05 | Encapsular la duración en un único punto del dominio y documentar el punto de extensión |

---

## Tabla resumen

| ID | Change | Fase | Deps | Governance |
|----|--------|------|------|------------|
| C-01 | foundation-setup (archivado `[x]`) | 0 | — | BAJO |
| C-02 | db-schema-and-seed (archivado `[x]`) | 1 | C-01 | CRITICO |
| C-03 | auth-login-rbac (archivado `[x]`) | 1 | C-02 | CRITICO |
| C-04 | user-management (archivado `[x]`) | 1 | C-03 | ALTO |
| C-05 | domain-scheduling-core | 2 | C-01 | MEDIO |
| C-05a | crear-turno-sin-solapamientos (recorte de C-05, archivado `[x]`) | 2 | — | MEDIO |
| C-05b | calcular-slots-disponibles (recorte de C-05, archivado `[x]`) | 2 | C-05a | MEDIO |
| C-05c | completar-dominio-agenda (recorte de C-05, archivado `[x]`) | 2 | C-05b | MEDIO |
| C-05d | puertos-repositorios-dominio (recorte de C-05, archivado `[x]`) | 2 | C-05c | MEDIO |
| C-06 | patients-crud (archivado `[x]`) | 2 | C-03 | BAJO |
| C-07 | professional-schedules (archivado `[x]`) | 2 | C-03, C-05 | MEDIO |
| C-08 | appointment-use-cases (archivado `[x]`) | 3 | C-03, C-05 | MEDIO |
| C-09 | agenda-views (archivado `[x]`) | 3 | C-05, C-07, C-08 | BAJO |
| C-10 | appointment-management-ui (archivado `[x]`) | 3 | C-06, C-08, C-09 | MEDIO |
| C-11 | email-confirmation-infra (archivado `[x]`) | 4 | C-08 | ALTO |
| C-12 | reminders-cron | 4 | C-11 | ALTO |
| C-13 | deploy-and-hardening | 5 | C-04, C-10, C-12 | MEDIO |

**Siguientes changes habilitados**: C-01, C-02, C-03, C-04, C-05 (a-d), C-06, C-07, C-08, C-09, C-10 y C-11 ya están archivados. Queda habilitado `C-12` (reminders-cron, ALTO; depende de C-11). C-13 espera a C-12 (y a C-04 y C-10, ya archivados). Para arrancar: `/opsx:propose C-12-reminders-cron`. Gobernanza CRÍTICA de C-03 ya aprobada y ejecutada.
