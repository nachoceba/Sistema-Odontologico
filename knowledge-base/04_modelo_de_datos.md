# Modelo de Datos

## Dominios

- **Identidad**: `users` (usuarios de la app, su contraseña con hash y su rol).
- **Profesionales**: `professionals`, `working_hours`, `time_off`.
- **Pacientes**: `patients`.
- **Agenda**: `appointments`.
- **Notificaciones**: `email_notifications`.
- **Configuración**: `clinic_settings`.

## ERD

```
users 1───0..1 professionals
                                      │ 1
                          ┌───────────┼───────────┐
                          │ N         │ N         │ N
                   working_hours   time_off   appointments N───1 patients
                                                   │ 1
                                                   │ N
                                          email_notifications
```

## Entidades

### users
- `id` uuid PK
- `email` text NOT NULL, único sin distinguir mayúsculas (índice único sobre `lower(email)`, DD-38; se usa para iniciar sesión)
- `password_hash` text NOT NULL (hash argon2 o bcrypt; nunca la contraseña en texto plano)
- `full_name` text NOT NULL
- `role` enum (`admin`, `receptionist`, `dentist`) NOT NULL
- `active` boolean NOT NULL default true

### professionals
- `id` uuid PK
- `user_id` uuid NOT NULL UNIQUE FK a `users.id` (todo profesional tiene su cuenta con rol `dentist`, DD-38)
- `display_name` text NOT NULL
- `license_number` text NULL (matrícula, dato ficticio)
- `active` boolean NOT NULL default true

### working_hours
- `id` uuid PK
- `professional_id` FK a `professionals.id`
- `weekday` smallint (0-6) NOT NULL
- `start_time` time NOT NULL, `end_time` time NOT NULL
- Constraints: `weekday BETWEEN 0 AND 6`, `start_time < end_time` y horas sin segundos (DD-29, DD-42). Los tramos del mismo día no se superponen: lo valida el dominio (`validate_working_hours`), no la base (DD-42).

### time_off
- `id` uuid PK
- `professional_id` FK a `professionals.id`
- `starts_on` date NOT NULL, `ends_on` date NOT NULL, `reason` text NULL
- Constraint: `starts_on <= ends_on`

### patients
- `id` uuid PK
- `first_name`, `last_name` text NOT NULL
- `document_number` text NOT NULL UNIQUE (DNI ficticio)
- `email` text NOT NULL (necesario para recordatorios)
- `phone` text NULL
- `birth_date` date NULL
- `active` boolean NOT NULL default true
- Índices: `document_number` (único), `last_name`

### appointments
- `id` uuid PK
- `patient_id` FK a `patients.id`, `professional_id` FK a `professionals.id`
- `starts_at` timestamptz NOT NULL, `ends_at` timestamptz NOT NULL
- `status` enum (`scheduled`, `cancelled`, `completed`, `no_show`) NOT NULL default `scheduled`
- `cancel_reason` text NULL
- `created_by` FK a `users.id` NULL: un valor nulo significa que el turno lo reservó el paciente online (migración `0003`, C-15)
- `pending_until` timestamptz NULL: si tiene valor, el turno es una reserva online pendiente de confirmación (`status = 'scheduled'`); se calcula como el menor entre la reserva más `ONLINE_BOOKING_HOLD_MINUTES` y `starts_at`
- `confirmation_token_hash` text NULL: SHA-256 en hexadecimal del token del enlace de confirmación; el token en claro nunca se guarda
- `created_at`, `updated_at`
- Constraints:
  - `starts_at < ends_at`
  - `ck_appointments_pending_columns_together`: `(pending_until IS NULL) = (confirmation_token_hash IS NULL)`
  - `ck_appointments_pending_only_online`: `pending_until IS NULL OR created_by IS NULL`
  - Exclusión `ex_appointments_no_overlap` (requiere `btree_gist`, creada en la migración de Alembic con `ExcludeConstraint`): `EXCLUDE USING gist (professional_id WITH =, tstzrange(starts_at, ends_at, '[)') WITH &&) WHERE (status = 'scheduled')`
- Índices: `(professional_id, starts_at)`, `(starts_at)` para el job de recordatorios (lo usa el listado de turnos `scheduled` que empiezan en un rango, C-12), `(patient_id, starts_at)` y `(created_by)` (claves foráneas indexadas), `uq_appointments_confirmation_token_hash` (único parcial sobre `confirmation_token_hash`) e `ix_appointments_pending_until` (parcial sobre `pending_until`). La reversión de `0003` falla si hay turnos online

### email_notifications
- `id` uuid PK
- `appointment_id` FK a `appointments.id`
- `kind` enum (`confirmation`, `reminder`, `booking_expired`) NOT NULL (`booking_expired` lo agrega la migración `0004`; su reversión falla si hay avisos de ese tipo, C-16)
- `status` enum (`pending`, `sent`, `failed`) NOT NULL default `pending`
- `sent_at` timestamptz NULL, `error` text NULL
- `appointment_starts_at` timestamptz NOT NULL (copia de `appointments.starts_at` al crear la notificación; permite una notificación nueva si el turno se reprograma)
- `created_at` timestamptz NOT NULL default `now()` (migración `0002`, DD-88): permite reencolar solo las `pending` con más de 5 minutos. Índice parcial `ix_email_notifications_pending_created_at (created_at) WHERE status = 'pending'`
- Un aviso de un turno que ya empezó no se envía y queda `failed` con `error = EXPIRED` (no hay estado nuevo)
- Constraint UNIQUE `(appointment_id, kind, appointment_starts_at)`: garantiza idempotencia (RN-NO-03)

### clinic_settings
- Fila única. `clinic_name` text NOT NULL, `address` text NOT NULL, `phone` text NULL (datos ficticios; se usan en los emails). `slot_minutes` int NOT NULL default 30 (> 0). `timezone` text NOT NULL default `America/Argentina/Buenos_Aires`. `reminder_send_hour` smallint NOT NULL default 9 (0-23). `min_notice_hours` smallint NOT NULL default 6 (anticipación mínima para crear un turno, RN-TU-12; >= 0). La fila única la garantiza `id smallint PRIMARY KEY DEFAULT 1 CHECK (id = 1)` (DD-44). La fuente de verdad de la zona horaria en ejecución es esta tabla; `CLINIC_TIMEZONE` solo da el valor inicial.

## Seed data inicial

- Se carga con `backend/scripts/seed.py` (idempotente), no con un archivo SQL.
- 1 usuario administrador.
- 1 usuario de recepción. Los usuarios del seed (administrador, recepción y una cuenta `dentist` por profesional) comparten una contraseña de demo ficticia que NO está en el script: sale de la variable de entorno `SEED_DEMO_PASSWORD` y solo se guarda su hash argon2 (DD-40, regla dura 5).
- 2 profesionales ficticios con `working_hours` de lunes a viernes.
- `clinic_settings` con slot de 30 min.
- 10 pacientes ficticios, con emails `@example.com`; en una demo con SMTP real, emails de prueba controlados por el equipo (ver SU-02).

## Integridad referencial

- Todas las claves foráneas son `ON DELETE RESTRICT`: la base impide borrar pacientes, profesionales y usuarios con turnos, y turnos con notificaciones; nada se borra en cadena (DD-39). La baja es marcar `active = false`.
- Los identificadores son `uuid` con `DEFAULT gen_random_uuid()` (DD-37).
