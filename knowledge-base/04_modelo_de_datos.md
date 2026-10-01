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
- `email` text NOT NULL UNIQUE (se usa para iniciar sesión)
- `password_hash` text NOT NULL (hash argon2 o bcrypt; nunca la contraseña en texto plano)
- `full_name` text NOT NULL
- `role` enum (`admin`, `receptionist`, `dentist`) NOT NULL
- `active` boolean NOT NULL default true

### professionals
- `id` uuid PK
- `user_id` uuid UNIQUE FK a `users.id` (un profesional es un usuario con rol `dentist`)
- `display_name` text NOT NULL
- `license_number` text NULL (matrícula, dato ficticio)
- `active` boolean NOT NULL default true

### working_hours
- `id` uuid PK
- `professional_id` FK a `professionals.id`
- `weekday` smallint (0-6) NOT NULL
- `start_time` time NOT NULL, `end_time` time NOT NULL
- Constraint: `start_time < end_time`. Los tramos del mismo día no se superponen.

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
- `created_by` FK a `users.id`, `created_at`, `updated_at`
- Constraints:
  - `starts_at < ends_at`
  - Exclusión (requiere `btree_gist`, creada en una migración de Alembic con `ExcludeConstraint`): `EXCLUDE USING gist (professional_id WITH =, tstzrange(starts_at, ends_at) WITH &&) WHERE (status = 'scheduled')`
- Índices: `(professional_id, starts_at)`, `(starts_at)` para el job de recordatorios

### email_notifications
- `id` uuid PK
- `appointment_id` FK a `appointments.id`
- `kind` enum (`confirmation`, `reminder`) NOT NULL
- `status` enum (`pending`, `sent`, `failed`) NOT NULL default `pending`
- `sent_at` timestamptz NULL, `error` text NULL
- `appointment_starts_at` timestamptz NOT NULL (copia de `appointments.starts_at` al crear la notificación; permite una notificación nueva si el turno se reprograma)
- Constraint UNIQUE `(appointment_id, kind, appointment_starts_at)`: garantiza idempotencia (RN-NO-03)

### clinic_settings
- Fila única. `clinic_name` text NOT NULL, `address` text NOT NULL, `phone` text NULL (datos ficticios; se usan en los emails). `slot_minutes` int NOT NULL default 30. `timezone` text NOT NULL default `America/Argentina/Buenos_Aires`. `reminder_send_hour` smallint default 9. `min_notice_hours` smallint NOT NULL default 6 (anticipación mínima para crear un turno, RN-TU-12). La fuente de verdad de la zona horaria en ejecución es esta tabla; `CLINIC_TIMEZONE` solo da el valor inicial.

## Seed data inicial

- Se carga con `backend/scripts/seed.py` (idempotente), no con un archivo SQL.
- 1 usuario administrador.
- 1 usuario de recepción (contraseñas de prueba ficticias definidas en el script, nunca reales).
- 2 profesionales ficticios con `working_hours` de lunes a viernes.
- `clinic_settings` con slot de 30 min.
- 10 pacientes ficticios, con emails `@example.com`; en una demo con SMTP real, emails de prueba controlados por el equipo (ver SU-02).
