# Design: db-schema-and-seed (C-02)

> **Gobernanza CRÍTICA.** Las preguntas P-1 a P-7 fueron **CONFIRMADAS** por el usuario: aceptó las 7 recomendaciones tal cual (registradas como DD-37 a DD-43 en `knowledge-base/09_decisiones_y_supuestos.md`) y aprobó las 3 reglas extra de `clinic_settings` (DD-44). No hubo cambios respecto de las specs y las tasks.

## Context

Ver `proposal.md` (Why). Estado actual observado en el código:

- `backend/alembic/env.py` lee la URL con `get_settings().DATABASE_URL` y tiene `target_metadata = None`; `alembic/versions/` está vacío. `app/infrastructure/db/` existe pero vacío.
- Dependencias ya presentes: `sqlalchemy>=2.0`, `alembic>=1.13`, `psycopg[binary]>=3.2`. No hay librería de hash de contraseñas.
- Docker Compose levanta `db` con `postgres:16-alpine` (`gen_random_uuid()` es nativo desde PostgreSQL 13; `btree_gist` viene en la imagen como extensión contrib).
- Los puertos de C-05d usan identificadores `str` y tipos de dominio inmutables (`Appointment`, `TimeOffEntry`, `Patient`, `ClinicSettings`, `WorkingHours`). El repositorio en memoria lanza `ValueError` ante instantes sin zona o `inicio >= fin`, `SlotTakenError` ante superposición y `AppointmentNotFoundError` al modificar un id inexistente.
- La batería de contrato (`backend/tests/contract/`) está parametrizada por fábrica (solo `in_memory`) y usa identificadores literales (`"dra-a"`, `"pac-1"`, `"rec-1"`, `"no-existe"`). **Esto no funciona tal cual contra PostgreSQL**: con claves foráneas y UUID, `"dra-a"` no existe ni tiene el formato de la columna (ver D-9).
- `tests/integration/conftest.py` marca como `integration` todo lo que vive ahí; `pytest` por defecto excluye `integration`.

## Goals / Non-Goals

**Goals:**
- Que PostgreSQL rechace por sí solo dos turnos `scheduled` superpuestos del mismo profesional (segunda barrera de RN-TU-01).
- Que los CHECK de la base y los `ValueError` de los repositorios digan lo mismo (inicio < fin; licencia `starts_on <= ends_on`).
- Que la misma batería de contrato pase contra memoria y contra PostgreSQL: ese es el criterio de "el esquema es correcto para el dominio".
- Migración reversible y probada en una base limpia; seed idempotente.

**Non-Goals:**
- La base **no** verifica grilla, duración igual a `slot_minutes`, tramo de trabajo, licencia ni anticipación mínima (RN-TU-02, RN-TU-03, RN-HO-03, RN-TU-12): son reglas del dominio (DD-02) que dependen de configuración y del reloj.
- La base **no** verifica las transiciones de estado (RN-TU-05, RN-TU-07, DD-21 a DD-24): un `UPDATE` directo de `cancelled` a `scheduled` sin superposición se acepta; las transiciones son del dominio y de C-08.
- La base **no** verifica la no superposición de tramos de horario (ver P-6).
- Login, verificación de contraseña, JWT (C-03); repositorio de usuarios (C-04) y de notificaciones (C-11); unidad de trabajo y test de concurrencia con dos sesiones (C-08).

## Decisiones confirmadas por el usuario (P-1 a P-7)

Escritas en lenguaje simple. Cada una trae una recomendación; basta con responder "sí a la recomendación" o elegir otra opción.

### P-1 — ¿Cómo se identifica cada fila: código largo aleatorio (UUID) o número correlativo? — CONFIRMADA (se aceptó la recomendación)
Cada paciente, turno o usuario necesita un identificador único. Opciones:
- **(a) UUID** (un código como `3f2c…`, generado por la base). Es lo que ya dice `04_modelo_de_datos.md`; no deja adivinar cuántos pacientes hay ni el id del siguiente, y encaja con el dominio, que ya trata los ids como texto.
- (b) Número correlativo (1, 2, 3…). Más corto y algo más rápido, pero expone cantidades y es fácil de adivinar en una URL.

**Recomendación: (a) UUID generado por la base** (`gen_random_uuid()`). Para el tamaño de un consultorio, la diferencia de rendimiento no se nota. Consecuencia: la batería de contrato deja de usar ids inventados como `"dra-a"` (D-9).

### P-2 — ¿Los odontólogos son usuarios con una ficha de profesional aparte? — CONFIRMADA (se aceptó la recomendación)
Hay dos "cosas": la **cuenta para entrar al sistema** (usuario) y la **ficha del profesional** que tiene horarios y turnos.
- **(a) Dos tablas unidas** (`users` y `professionals`), como dice la KB: cada profesional tiene exactamente una cuenta con rol odontólogo, y una cuenta tiene como mucho una ficha. **Todo profesional debe tener cuenta** (no hay profesionales sin usuario).
- (b) Dos tablas, pero permitiendo profesionales sin cuenta (por ejemplo, un odontólogo que no usa el sistema).
- (c) Una sola tabla con todo.

Además: ¿el email de una cuenta se considera el mismo aunque cambien mayúsculas (`Ana@Example.com` = `ana@example.com`)? Esto no está en la KB.

**Recomendación: (a), y emails de cuentas únicos sin importar mayúsculas** (evita dos cuentas para la misma persona y errores al iniciar sesión).

### P-3 — ¿Qué pasa si se intenta borrar algo que tiene turnos? — CONFIRMADA (se aceptó la recomendación)
La KB ya dice que a un paciente con turnos no se lo borra, se lo desactiva (RN-PA-03), y que cancelar un turno no lo borra (DD-05).
- **(a) La base impide borrar** pacientes, profesionales y usuarios que tengan turnos (y turnos con emails registrados); nunca se borra nada "en cadena". Un paciente cargado por error y sin turnos sí se puede borrar.
- (b) Borrado en cadena: borrar un paciente borra sus turnos. Se pierde el historial.

**Recomendación: (a).** Conserva la historia y es coherente con RN-PA-03 y DD-05. (Los tramos de horario sí se reemplazan borrando los viejos, porque nadie los referencia.)

### P-4 — ¿Qué datos de prueba carga el seed y con qué contraseña? — CONFIRMADA (se aceptó la recomendación)
Propuesta de contenido (todo ficticio):
- Usuarios: `admin@example.com` (administrador), `recepcion@example.com` (recepción) y una cuenta odontólogo por cada profesional (`dra.a@example.com`, `dr.b@example.com`), porque la KB pide 2 profesionales y P-2 recomienda que todo profesional tenga cuenta.
- Profesionales: "Dra. Ana Alvarez" de lunes a viernes 09:00–13:00 y 14:00–18:00; "Dr. Bruno Benítez" de lunes a viernes 13:00–20:00. Matrículas ficticias.
- Consultorio: "Consultorio Odontológico Demo", dirección y teléfono ficticios, turnos de 30 minutos, zona tomada de `CLINIC_TIMEZONE`, recordatorio a las 9, anticipación de 6 horas.
- 10 pacientes ficticios con DNI inventados y emails `@example.com`.
- **Contraseña**: no se escribe en el código. Se lee de una variable de entorno `SEED_DEMO_PASSWORD` (misma para todas las cuentas de demo), con un valor de ejemplo ficticio en `.env.example`. Si falta, el seed se niega a crear usuarios.
- Si se vuelve a correr, el seed **solo agrega lo que falta**: no pisa cambios hechos después ni cambia contraseñas.

**Recomendación: aceptar esta propuesta.** Alternativa: contraseña fija de demo escrita en el script (más simple, pero queda en el repositorio y sería peligrosa si alguien usa el seed en la demo pública de C-13).

### P-5 — La autenticación completa es C-03, pero el seed necesita guardar contraseñas "cifradas" (hash). ¿Quién lo hace? — CONFIRMADA (se aceptó la recomendación)
- **(a) C-02 agrega solo la función que convierte una contraseña en hash** (argon2, la librería `argon2-cffi` que C-03 ya prevé usar), en `app/core/security.py`. C-03 le suma la verificación y el JWT.
- (b) C-02 crea los usuarios con un hash "imposible" (nadie puede entrar) y C-03 los actualiza.
- (c) Los usuarios del seed se mueven a C-03; C-02 solo carga profesionales, consultorio y pacientes (pero los profesionales necesitan su usuario, ver P-2).

**Recomendación: (a).** Es una función pequeña y probada, y deja el seed completo desde ahora. El resto de la seguridad sigue en C-03 con su propia revisión.

### P-6 — ¿Cómo se guardan los horarios de atención y cuánto los controla la base? — CONFIRMADA (se aceptó la recomendación)
Los horarios son "hora de reloj local" (09:00, 13:00), no un instante. Opciones de columna:
- **(a) Tipo "hora sin fecha ni zona"** (`time`), como dice la KB y como ya los maneja el dominio.
- (b) Minutos desde la medianoche (540 = 09:00). Más fácil de comparar, menos legible.

Y qué controla la base además de "inicio antes que fin" y "día de 0 a 6":
- **Rechazar horas con segundos** (09:00:30), igual que el dominio (DD-29). Recomendado.
- **No** controlar en la base que dos tramos del mismo día no se pisen: lo valida el dominio antes de guardar (`schedule-validation`, D-8 de C-05d). Hacerlo en la base requiere un tipo especial de rango de horas y haría que la base y el repositorio en memoria se comporten distinto ante un error del llamador.

**Recomendación: (a) `time`, rechazar segundos en la base y dejar la no superposición de tramos solo en el dominio.**

### P-7 — ¿Qué entra en C-02 y conviene partirlo? — CONFIRMADA (se aceptó la recomendación)
El change incluye: tablas y migración, tests de la base, seed, **repositorios PostgreSQL** de los 5 puertos y la **fábrica PostgreSQL de la batería de contrato** (que además obliga a ajustar los tests de contrato, D-9). El test de "dos recepcionistas agendan a la vez" con dos conexiones reales queda para C-08, que es donde se agenda de verdad.
- **(a) Un solo change** con todo lo anterior (≈ 45 tasks). La batería de contrato contra PostgreSQL es la mejor prueba de que el esquema sirve al dominio.
- (b) **Partirlo en dos**: C-02a `db-schema-and-seed` (tablas, migración, tests de la base, seed, hash) y C-02b `repositorios-postgres` (repositorios, fábrica y ajuste de la batería). C-03 solo necesita C-02a.
- (c) Dejar los repositorios para C-08.

**Recomendación: (a) un solo change**, ejecutado en el orden de los grupos de `tasks.md` (los grupos 1–4 son, de hecho, C-02a). Si el usuario prefiere revisiones más chicas, (b) es una buena alternativa sin cambiar el contenido. (c) se desaconseja: el esquema quedaría sin su verificación principal.

## Decisions

Decisiones técnicas que no cambian el comportamiento visible y se toman en este design (respaldo en la KB o en la skill `supabase-postgres-best-practices`):

### D-1 — Modelos SQLAlchemy 2.0 declarativos en `app/infrastructure/db/`
`base.py` (DeclarativeBase con convención de nombres de constraints), `models.py`, `session.py` (`create_engine` + `sessionmaker` desde `get_settings()`), `repositories/`. Los modelos nunca se importan desde `domain/` (regla dura 2); los repositorios convierten fila ↔ tipo de dominio. Convención de nombres explícita (`pk_`, `fk_`, `uq_`, `ck_`, `ix_`, `ex_`) para que la migración y el `downgrade` nombren cada constraint. Identificadores en minúscula y `snake_case`. Alternativa descartada: mapear las dataclasses del dominio directo (acoplaría el dominio al ORM).

### D-2 — Migración `0001_initial_schema` escrita a mano
Orden: `CREATE EXTENSION IF NOT EXISTS btree_gist` → tipos enumerados → tablas sin dependencias → tablas con FK → `appointments` con `op.create_exclude_constraint` (o `ExcludeConstraint` en `create_table`): `(professional_id, '='), (tstzrange(starts_at, ends_at, '[)'), '&&')`, `using='gist'`, `where="status = 'scheduled'"` → índices. `downgrade` en orden inverso, con `DROP TYPE` explícito de los 4 enumerados. **No** se borra `btree_gist` en el `downgrade` (puede usarla otra cosa y es inocua); el escenario "revertir" verifica tablas y tipos propios. El autogenerate solo se usa como control (D-8), nunca como fuente. Antes de escribirla, consultar Context7 (SQLAlchemy 2.0 / Alembic: `ExcludeConstraint` y `create_exclude_constraint`) sin enviar código del proyecto, y registrar lo consultado en la task.

### D-3 — Tipos de columna
`uuid` con `DEFAULT gen_random_uuid()`; `text` en lugar de `varchar(n)`; `timestamptz` para instantes (RN-GL-01); `time` para horas de tramo; `date` para licencias; `smallint` para `weekday`, `reminder_send_hour`, `min_notice_hours`; `integer` para `slot_minutes`; `boolean NOT NULL DEFAULT true` para `active`; `created_at`/`updated_at timestamptz NOT NULL DEFAULT now()` en `appointments` (`updated_at` lo actualiza SQLAlchemy con `onupdate`, sin triggers).

### D-4 — Enumerados nativos de PostgreSQL con los **valores** del dominio
Como pide `CHANGES.md`. En SQLAlchemy, `Enum(AppointmentStatus, name="appointment_status", values_callable=lambda e: [m.value for m in e])`: sin `values_callable`, SQLAlchemy guarda el **nombre** (`SCHEDULED`) y no el valor (`scheduled`), y el `WHERE status = 'scheduled'` del constraint dejaría de coincidir. `create_type=False` en los modelos porque la migración crea los tipos. Para `user_role`, `notification_kind` y `notification_status` se definen enums Python en infraestructura (no hay tipo de dominio todavía). Alternativa descartada: `text` + `CHECK` (más fácil de extender, pero se aparta del alcance de `CHANGES.md`).

### D-5 — Constraints e índices
- `appointments`: `ck_appointments_starts_before_ends`, exclusión `ex_appointments_no_overlap`, índices `(professional_id, starts_at)`, `(starts_at)` (job de recordatorios), `(patient_id, starts_at)` (listado por paciente, FK indexada) y `(created_by)` (FK indexada).
- `working_hours`: `ck` `weekday BETWEEN 0 AND 6`, `start_time < end_time`, y sin segundos `date_trunc('minute', start_time) = start_time` (y lo mismo para `end_time`); índice `(professional_id, weekday, start_time)`.
- `time_off`: `ck` `starts_on <= ends_on`; índice `(professional_id, starts_on)`.
- `patients`: `uq(document_number)`, índice `(last_name)`; `email NOT NULL`.
- `users`: índice único sobre `lower(email)`; `role user_role NOT NULL`.
- `professionals`: `uq(user_id)`, `user_id NOT NULL`.
- `email_notifications`: `uq(appointment_id, kind, appointment_starts_at)` (su primera columna cubre la FK).
- `clinic_settings`: fila única con `id smallint PRIMARY KEY DEFAULT 1 CHECK (id = 1)`; `ck` `slot_minutes > 0` (coherente con DD-18), `min_notice_hours >= 0`, `reminder_send_hour BETWEEN 0 AND 23`. La zona horaria no se valida en la base (un CHECK no puede consultar la lista IANA de forma estable); la valida `Settings` al leer `CLINIC_TIMEZONE` y el repositorio la usa con `ZoneInfo`.
- Todas las FK `ON DELETE RESTRICT`.

### D-6 — Repositorios PostgreSQL: misma frontera de errores que en memoria
- Cada método valida en Python **antes** de tocar la base lo mismo que el repositorio en memoria (`_require_range`, `_require_query_range`, `ends_on < starts_on` → `ValueError`), reutilizando las mismas funciones (se mueven a un módulo compartido sin dependencias, p. ej. `app/domain/appointments/rules.py` o un helper de infraestructura), para que el mensaje y el tipo de error no dependan de la implementación.
- La violación del constraint de exclusión (SQLSTATE `23P01`, `psycopg.errors.ExclusionViolation` dentro de `IntegrityError`) se traduce a `SlotTakenError(professional_id, starts_at)` tras `rollback`. Cualquier otra `IntegrityError` se propaga (es un error de programación o de datos).
- Id con formato no UUID: `get` devuelve `None`; `change_status`/`reschedule` lanzan `AppointmentNotFoundError` (contrato vigente, escenario `no-existe`).
- `list_for_*`: `WHERE professional_id = :p AND ends_at > :start [AND starts_at < :end] ORDER BY starts_at` (mismo rango semiabierto que memoria; DD-31, DD-35).
- Instantes leídos de la base se devuelven con zona UTC; la igualdad de `Appointment` con el guardado se cumple porque `datetime` con zona compara por instante.
- `ClinicSettingsRepository.get()`: lee la fila `id = 1`; si no existe devuelve `ClinicSettings()` sin crearla.
- `WorkingHoursRepository.replace_for_professional`: `DELETE` + `INSERT` en la misma transacción.

### D-7 — Transacción por operación (DD-36)
Cada repositorio recibe un `sessionmaker` y cada método corre en su propia transacción (`with factory.begin() as session`), "todo o nada" por sí solo, como pide DD-36. C-08 decide si introduce una unidad de trabajo compartida; el cambio quedaría dentro de la infraestructura. Alternativa descartada: recibir una `Session` abierta y dejar el commit al llamador (no hay todavía un llamador que lo haga).

### D-8 — Tests de integración contra una base de pruebas separada
- Variable `TEST_DATABASE_URL` (en `.env.example`, sin secretos reales) apuntando a una base `<POSTGRES_DB>_test` del mismo contenedor `db`; los tests nunca tocan la base de desarrollo. Si la variable falta, los tests de integración fallan con un mensaje claro (no se saltan en silencio).
- Fixture de sesión: crea la base de pruebas si no existe, corre `alembic downgrade base` + `upgrade head` una vez por sesión; entre tests, `TRUNCATE ... RESTART IDENTITY CASCADE` de las 8 tablas (solo en la base de pruebas).
- Test de migración: base temporal propia → `upgrade head` → inspección (tablas, tipos, constraint de exclusión) → `downgrade base` → sin tablas ni tipos → `upgrade head`.
- Test "modelos = migración": `alembic.autogenerate.compare_metadata` contra la base migrada debe dar lista vacía; si el `ExcludeConstraint` produce un falso positivo conocido, se filtra con `include_object` documentando el motivo.
- Los tests de constraints usan SQL directo (sin repositorios) para probar que la base protege sola.

### D-9 — La batería de contrato pide referencias a la fábrica
`RepositoryFactory` gana métodos para obtener referencias con nombre: `professional("dra-a")`, `patient(Patient(...))` / `patients(initial)`, `user("rec-1")`. En memoria devuelven el mismo texto (`"dra-a"`), así el comportamiento en memoria no cambia; en PostgreSQL insertan la fila mínima (usuario + profesional, paciente con documento ficticio único) y devuelven su UUID. Los tests reemplazan los literales por esas referencias; las aserciones comparan contra la referencia, no contra el literal. `"no-existe"` se mantiene literal (prueba el id mal formado). La fábrica `postgres` se registra como `pytest.param(PostgresFactory, id="postgres", marks=pytest.mark.integration)`. Red de seguridad: antes de tocar la batería, correrla en memoria y anotar cuántos pasan; después del ajuste, el mismo número en memoria.

### D-10 — Seed
`backend/scripts/seed.py`, ejecutable como `python -m scripts.seed` dentro del contenedor `api`, después de `alembic upgrade head` (comando documentado en el README; el contenedor no migra solo al arrancar). Usa la sesión de D-1 y `INSERT ... ON CONFLICT DO NOTHING` por clave natural (`lower(email)`, `document_number`, `professionals.user_id`, `clinic_settings.id`); los tramos de un profesional se cargan solo si no tiene ninguno. Antes de escribir, verifica que la migración esté aplicada (tabla `alembic_version` en la última revisión) y si no, termina con error. Valida sus propios tramos con `validate_working_hours` del dominio. Lee `SEED_DEMO_PASSWORD` y `CLINIC_TIMEZONE` del entorno. Los datos viven como constantes en el script.

### D-11 — Hash de contraseñas
`app/core/security.py` con `hash_password(plain: str) -> str` usando `argon2-cffi` (`PasswordHasher` con parámetros por defecto). Sin verificación ni JWT (C-03).

## Revisión de escenarios (skill `revisor-escenarios-turnos`)

Se revisaron 41 escenarios de `database-schema` y `seed-data`. Hallazgos:

| # | Tipo | Escenario | Qué pasa | Respaldo en la KB | Resolución |
|---|------|-----------|----------|-------------------|------------|
| 1 | Sin respaldo | Email de usuario repetido con otras mayúsculas | La KB pide `UNIQUE`, no dice nada de mayúsculas | sin respaldo en la KB | P-2 |
| 2 | Sin respaldo | Hora con segundos | DD-29 es una regla del dominio; reforzarla en la base es nuevo | DD-29 (dominio) | P-6 |
| 3 | Ambigüedad | Tramos del mismo día superpuestos | `04_modelo_de_datos.md` dice "no se superponen" sin decir quién lo garantiza; D-8 de C-05d dice que el repositorio no valida | RN-HO-02, `04_modelo_de_datos.md` | P-6 |
| 4 | Sin respaldo | Borrar paciente/usuario/profesional con turnos | RN-PA-03 cubre pacientes; profesionales y usuarios no | RN-PA-03, DD-05; resto sin respaldo en la KB | P-3 |
| 5 | Borde aclarado | "Volver a agendar un cancelado" | La base no impide `cancelled` → `scheduled` sin superposición, aunque RN-TU-07 lo prohíbe | RN-TU-07 | Non-goal explícito: transiciones solo en dominio/C-08 |
| 6 | Borde aclarado | Turnos fuera de grilla, de horario o en licencia | La base los acepta; las reglas son del dominio | RN-TU-02, RN-TU-03, RN-HO-03, DD-02 | Non-goal explícito |
| 7 | Sin respaldo | Rangos de `clinic_settings` | `slot_minutes > 0` coincide con DD-18; `0 ≤ reminder_send_hour ≤ 23` y `min_notice_hours ≥ 0` no figuran | DD-18; resto sin respaldo en la KB | D-5 (técnico, valores triviales); se menciona al usuario en el reporte |
| 8 | Pregunta abierta | Zona del seed | Depende de SU-01; el seed la toma de `CLINIC_TIMEZONE`, sin fijarla | SU-01 | No bloquea: `timestamptz` no depende de la zona |

Escenarios sin hallazgos: superposición directa, mismo horario, pegados (rango `[)`), cancelado/atendido/ausente no bloquean, profesionales distintos, mover encima de otro, medianoche (DD-19), CHECK inicio < fin, instante entre zonas (RN-GL-01), notificaciones (RN-NO-03), licencias (DD-28), documento repetido (RN-PA-01), email obligatorio (RN-PA-02), configuración única, seed e idempotencia. Hay escenarios esperados, de error de negocio y de borde en ambas capabilities.

## Risks / Trade-offs

- [El autogenerate no reproduce `ExcludeConstraint` con `tstzrange` y `WHERE`] → migración manual (D-2) y test que compara modelos y base (D-8).
- [Enum guardado por nombre en vez de valor] → `values_callable` (D-4) y escenario "estado por defecto / inválido" con SQL directo.
- [El repositorio PostgreSQL y el de memoria divergen en errores] → validación previa compartida (D-6) y misma batería de contrato.
- [Los tests de integración borran datos] → base de pruebas separada por `TEST_DATABASE_URL` (D-8); el `TRUNCATE` se niega a correr si el nombre de la base no termina en `_test`.
- [Contraseña de demo conocida usada en la demo pública (C-13)] → viene del entorno (P-4); C-13 debe cambiarla.
- [Ajustar la batería de contrato toca tests archivados] → cambio mecánico con red de seguridad (mismo número de tests en verde en memoria antes y después, D-9).
- [Concurrencia real (dos sesiones simultáneas)] → el constraint la cubre por construcción; la prueba con dos conexiones queda en C-08 (R-5).
- [Cambiar a sillones o duración variable (DD-08, R-11)] → el constraint queda en un único lugar de la migración; extenderlo será una migración nueva.
- [Intérprete local Python 3.11 frente a `requires-python >=3.12`] → los tests se corren en el contenedor (spec `local-environment`).

## Migration Plan

1. `docker compose up -d db` → `docker compose exec api alembic upgrade head` → `docker compose exec api python -m scripts.seed`.
2. Rollback: `alembic downgrade base` (deja la base sin tablas ni tipos del sistema; no hay datos reales que perder, R-10).
3. Producción (C-13) aplica la misma migración; el seed allí es opcional y con contraseña propia.

## Open Questions

Ninguna diferible: las preguntas que cambian specs o tasks están arriba como P-1 a P-7.
