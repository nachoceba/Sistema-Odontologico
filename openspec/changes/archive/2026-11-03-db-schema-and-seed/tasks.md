# Tasks: db-schema-and-seed (C-02)

> **Gobernanza CRÍTICA.** El grupo 0 bloquea todo lo demás. Modo TDD estricto: en cada task de código, primero el test que falla (RED), después el mínimo código (GREEN), triangulación y refactor. Los tests de integración corren en el contenedor contra la base de pruebas (`pytest -m integration`). Sin commits ni push sin pedido explícito del usuario.

## 0. Confirmaciones del usuario (BLOQUEANTE)

- [x] 0.1 Obtener respuesta del usuario a P-1 (UUID vs número) y registrar la decisión en `design.md`; verificar que la pregunta queda marcada CONFIRMADA con la opción elegida
- [x] 0.2 Obtener respuesta a P-2 (usuarios y profesionales; email sin mayúsculas) y registrarla en `design.md`
- [x] 0.3 Obtener respuesta a P-3 (borrado bloqueado vs en cadena) y registrarla en `design.md`
- [x] 0.4 Obtener respuesta a P-4 (contenido del seed y `SEED_DEMO_PASSWORD`) y registrarla en `design.md`
- [x] 0.5 Obtener respuesta a P-5 (hash en C-02 con `argon2-cffi`) y registrarla en `design.md`
- [x] 0.6 Obtener respuesta a P-6 (columna `time`, segundos, superposición de tramos) y registrarla en `design.md`
- [x] 0.7 Obtener respuesta a P-7 (un change o dos) y, si se parte, reorganizar este change con `/opsx:update`; verificar `openspec validate db-schema-and-seed --strict` en verde
- [x] 0.8 Si alguna respuesta difiere de la recomendación, ajustar specs, design y tasks; registrar las decisiones nuevas como DD en `knowledge-base/09_decisiones_y_supuestos.md`; verificar `openspec validate --strict` en verde

## 1. Infraestructura de pruebas contra PostgreSQL

- [x] 1.1 Safety net: correr en el contenedor la batería completa (`pytest`) y anotar el número de tests en verde como línea base; verificar que no hay fallas previas
- [x] 1.2 Agregar `TEST_DATABASE_URL` a `.env.example` (valor de ejemplo sin secretos reales) y al `.env` local; verificar que `tests/unit/test_env_example.py` sigue en verde (o se actualiza si exige la lista exacta). Los tests leen `TEST_DATABASE_URL` del entorno y `tests/unit/test_env_example.py` sigue en verde.
- [x] 1.3 Fixture de integración en `tests/integration/conftest.py`: crea la base `_test` si falta, se niega a correr si el nombre no termina en `_test`, falla con mensaje claro si falta `TEST_DATABASE_URL`; verificar con un test de humo `SELECT 1` en `pytest -m integration` (el fixture vive en `tests/conftest.py` para compartirlo con la batería de contrato; el humo está en `tests/integration/test_smoke.py`)
- [x] 1.4 `app/infrastructure/db/session.py`: engine y `sessionmaker` desde `get_settings()` (y uno para la URL de pruebas); verificar con test unitario que importar el dominio no carga la configuración

## 2. Modelos y migración inicial (database-schema)

- [x] 2.1 Consultar Context7 sobre `ExcludeConstraint` / `op.create_exclude_constraint` y `Enum(values_callable=...)` en SQLAlchemy 2.0 y Alembic (sin datos del proyecto); anotar lo consultado en el resumen del apply
- [x] 2.2 RED: test de integración de migración (base temporal: `upgrade head` crea 8 tablas, 4 enumerados, `btree_gist` y `ex_appointments_no_overlap`; `downgrade base` no deja tablas ni tipos propios; `upgrade head` otra vez; aplicar dos veces no cambia nada); verificar que falla
- [x] 2.3 `app/infrastructure/db/base.py` (convención de nombres) y `models.py` con las 8 tablas, enums con `values_callable` y constraints de D-5; `alembic/env.py` con `target_metadata`; verificar `mypy --strict` y `ruff` limpios
- [x] 2.4 GREEN: migración manual `alembic/versions/0001_initial_schema.py` (D-2) con `upgrade` y `downgrade`; verificar que el test 2.2 pasa (el `ExcludeConstraint` va dentro de `op.create_table`: `op.create_exclude_constraint` no admite la expresión de texto `tstzrange(...)`)
- [x] 2.5 Test "modelos = migración" con `compare_metadata` (D-8), documentando cualquier filtro de falso positivo; verificar que pasa

## 3. Constraints de la base (database-schema, SQL directo)

- [x] 3.1 Tests de exclusión de turnos: superposición, mismo horario, pegados, cancelado/atendido/ausente no bloquean, profesionales distintos, reactivar cancelado, mover encima de otro, medianoche; verificar en verde
- [x] 3.2 Tests de integridad de turnos: CHECK inicio < fin, instante entre zonas, estado por defecto, estado inválido, FK inexistentes; verificar en verde
- [x] 3.3 Tests de notificaciones: duplicado rechazado, reprogramado aceptado, otro tipo aceptado con `pending`; verificar en verde
- [x] 3.4 Tests de horarios y licencias: tramo válido, invertido/vacío, día fuera de rango, fin 23:59, segundos, licencia invertida y de un día; verificar en verde
- [x] 3.5 Tests de identidad: documento repetido, paciente sin email, email de usuario con mayúsculas, rol inválido, dos profesionales por usuario, activo por defecto; verificar en verde
- [x] 3.6 Tests de borrado y de `clinic_settings` (defaults, segunda fila, rangos); verificar en verde y que `pytest` por defecto no los corre

## 4. Hash de contraseñas y seed (seed-data)

- [x] 4.1 RED/GREEN: `app/core/security.py` `hash_password` con `argon2-cffi` (dependencia agregada a `pyproject.toml`); tests unitarios: el hash no es la contraseña, empieza con `$argon2`, dos hashes de la misma contraseña difieren; verificar en verde
- [x] 4.2 RED: tests de integración del seed: base vacía → 1 admin, 1 recepción, 2 profesionales con usuario `dentist`, tramos L–V válidos para `validate_working_hours`, 1 configuración con la zona de `CLINIC_TIMEZONE`, 10 pacientes, 0 turnos y 0 notificaciones; emails `@example.com`; verificar que fallan
- [x] 4.3 GREEN: `backend/scripts/seed.py` (D-10); verificar 4.2 en verde
- [x] 4.4 Tests de idempotencia y errores del seed: dos ejecuciones = mismas filas; cambios posteriores conservados; sin migración → error y nada creado; sin `SEED_DEMO_PASSWORD` → error que nombra la variable sin valores sensibles; verificar en verde
- [x] 4.5 Agregar `SEED_DEMO_PASSWORD` a `.env.example` con valor ficticio y documentar en el README los comandos `alembic upgrade head`, `python -m scripts.seed`, `alembic downgrade base` y `pytest -m integration`; verificar ejecutándolos en el contenedor tal como están escritos. README actualizado y los comandos se ejecutaron tal cual en el contenedor sobre una base temporal.

## 5. Repositorios PostgreSQL y batería de contrato

- [x] 5.1 Safety net: correr `tests/contract/` en memoria y anotar el número de tests en verde
- [x] 5.2 Refactor D-9: `RepositoryFactory` con referencias con nombre (`professional`, `user`, pacientes iniciales); reemplazar literales en los tests de contrato (salvo `"no-existe"`); verificar el mismo número de tests en verde en memoria que en 5.1
- [x] 5.3 Extraer la validación previa compartida (`_require_range`, `_require_query_range`, licencia invertida) para memoria y PostgreSQL (D-6); verificar contract + unit en verde
- [x] 5.4 Registrar la fábrica `postgres` (`marks=pytest.mark.integration`) con repositorios vacíos; verificar que `pytest -m integration tests/contract` falla (RED) y `pytest` por defecto solo corre `in_memory`
- [x] 5.5 GREEN: `SqlAlchemyClinicSettingsRepository` y `SqlAlchemyPatientRepository` (id mal formado → `None`; sin fila → defaults sin crearla); verificar sus baterías de contrato en verde en ambas fábricas
- [x] 5.6 GREEN: `SqlAlchemyWorkingHoursRepository` y `SqlAlchemyTimeOffRepository` (reemplazo atómico, orden); verificar la batería de horarios y licencias en verde en ambas fábricas, incluido el escenario de reemplazo sin tramos viejos
- [x] 5.7 GREEN: `SqlAlchemyAppointmentRepository` (traducción de `23P01` a `SlotTakenError`, `APPOINTMENT_NOT_FOUND` con id mal formado, rangos semiabiertos, instantes en UTC); verificar la batería de turnos en verde en ambas fábricas
- [x] 5.8 Verificar que `domain/` no importa SQLAlchemy ni `infrastructure/db` (test de imports existente o nuevo) y `mypy --strict` + `ruff` limpios en `app` y `tests`

## 6. Verificación integral

- [x] 6.1 En el contenedor: `pytest` (por defecto) con al menos la línea base de 1.1 en verde y `pytest -m integration` en verde; `mypy --strict` y `ruff` limpios
- [x] 6.2 En una base de desarrollo limpia: `alembic upgrade head` → seed → seed otra vez → `alembic downgrade base` → `upgrade head`, sin errores (se corrió con los comandos del README sobre una base temporal `*_cycle_test` que se borró; la base de desarrollo no se tocó)
- [x] 6.3 Actualizar la entrada C-02 de `CHANGES.md` (estado, artefactos, qué quedó para C-08: test de concurrencia con dos sesiones y unidad de trabajo); verificar `openspec validate db-schema-and-seed --strict` en verde
