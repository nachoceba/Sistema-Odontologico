# Proposal: db-schema-and-seed (C-02)

> **Gobernanza CRÍTICA (esquema de base de datos).** El usuario confirmó las preguntas P-1 a P-7 de `design.md` aceptando las recomendaciones (DD-37 a DD-43).

## Why

El dominio de agenda (C-05a a C-05d) está terminado y probado, pero solo existe en memoria: no hay tablas, ni migraciones, ni datos para probar el sistema. Sin base de datos no pueden avanzar el login (C-03), los pacientes (C-06), los horarios (C-07) ni la creación de turnos (C-08). Además, la regla dura 3 y 6 exige que la no superposición de turnos de un profesional la garantice PostgreSQL con un constraint de exclusión, no solo el código: hoy esa segunda barrera no existe.

## What Changes

- **Modelos SQLAlchemy 2.0** en `backend/app/infrastructure/db/` para las 8 tablas de `04_modelo_de_datos.md`: `users`, `professionals`, `working_hours`, `time_off`, `patients`, `appointments`, `email_notifications`, `clinic_settings`, con los tipos enumerados `user_role`, `appointment_status`, `notification_kind` y `notification_status`.
- **Primera migración de Alembic escrita a mano**: habilita `btree_gist`, crea tipos, tablas, CHECK, UNIQUE, claves foráneas e índices; incluye el constraint de exclusión `EXCLUDE USING gist (professional_id WITH =, tstzrange(starts_at, ends_at) WITH &&) WHERE (status = 'scheduled')`. El `downgrade` deja la base vacía (sin tablas ni tipos propios).
- `alembic/env.py` pasa a usar la metadata de los modelos (`target_metadata`).
- **Seed idempotente** `backend/scripts/seed.py` con datos ficticios: administrador, recepción, 2 profesionales con horario de lunes a viernes, configuración del consultorio y 10 pacientes con emails `@example.com`. Sin contraseñas reales ni secretos en el código.
- **Repositorios PostgreSQL** (SQLAlchemy) de los puertos de C-05d (turnos, horarios, licencias, pacientes, configuración) y **fábrica `postgres`** en la batería de contrato de `backend/tests/contract/`, que pasa a correr contra memoria y contra PostgreSQL real (un solo change, P-7).
- **Tests de integración** contra el contenedor `db`: constraint de exclusión, CHECK, UNIQUE, migración que sube y baja en una base limpia y seed idempotente.
- Ajuste puntual de la batería de contrato: las referencias a profesionales, pacientes y usuarios (`"dra-a"`, `"pac-1"`, `"rec-1"`) pasan a pedirse a la fábrica, porque la base real exige que existan (claves foráneas) y usa identificadores UUID. El comportamiento verificado no cambia.

Fuera de alcance: login, verificación de contraseñas y JWT (C-03); ABM de usuarios y pacientes (C-04, C-06); casos de uso y endpoints (C-07, C-08); repositorio de notificaciones (C-11); test de concurrencia con dos sesiones simultáneas y unidad de trabajo (C-08).

## Capabilities

### New Capabilities
- `database-schema`: tablas, tipos, constraints e índices de PostgreSQL y la migración que los crea y los revierte; en particular la garantía en la base de que un profesional no tiene dos turnos `scheduled` superpuestos.
- `seed-data`: carga idempotente de datos ficticios de demostración y desarrollo.

### Modified Capabilities
- `appointment-repository`: la batería de contrato corre también contra PostgreSQL y obtiene de la fábrica las referencias a profesionales, pacientes y usuarios.
- `schedule-repository`: ídem para horarios y licencias.
- `patient-repository`: ídem para pacientes.
- `clinic-settings-repository`: la batería de configuración corre también contra PostgreSQL (con y sin fila cargada).

## Impact

- **Código nuevo**: `backend/app/infrastructure/db/` (base, modelos, sesión, repositorios), `backend/alembic/versions/0001_*.py`, `backend/scripts/seed.py`, `backend/tests/integration/db/`, fábrica `postgres` en `backend/tests/contract/conftest.py`.
- **Código modificado**: `backend/alembic/env.py`; los tests de contrato (referencias por fábrica); `backend/tests/integration/conftest.py` (base de pruebas); `.env.example` y README (comandos de migración y seed, variables nuevas del seed y de la base de pruebas).
- **Dependencias**: `argon2-cffi`.
- **Base de datos**: primera migración; la regla de no superposición queda reforzada en PostgreSQL (DD-02, DD-04).
- **Riesgos**: el autogenerate de Alembic no genera bien el `ExcludeConstraint` con `tstzrange` y `WHERE` (por eso la migración es manual y se prueba subiendo y bajando); diferencias entre lo que rechaza la base y lo que rechaza el repositorio en memoria (se mitiga con la misma batería de contrato para ambos).
- **Tamaño**: es un change grande; el usuario eligió mantenerlo en uno (P-7).
