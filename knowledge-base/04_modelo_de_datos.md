# Modelo de Datos

## Dominios

- **Identidad**: `profiles` (usuarios de la app y su rol).
- **Profesionales**: `professionals`, `working_hours`, `time_off`.
- **Pacientes**: `patients`.
- **Agenda**: `appointments`.
- **Notificaciones**: `email_notifications`.
- **Configuración**: `clinic_settings`.

## ERD

```
auth.users 1───1 profiles 1───0..1 professionals
                                      │ 1
                          ┌───────────┼───────────┐
                          │ N         │ N         │ N
                   working_hours   time_off   appointments N───1 patients
                                                   │ 1
                                                   │ N
                                          email_notifications
```

## Entidades

### profiles
- `id` uuid PK, FK a `auth.users.id`
- `full_name` text NOT NULL
- `role` enum (`admin`, `receptionist`, `dentist`) NOT NULL
- `active` boolean NOT NULL default true

### professionals
- `id` uuid PK
- `profile_id` uuid UNIQUE FK a `profiles.id` (un profesional es un usuario con rol `dentist`)
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
- `created_by` FK a `profiles.id`, `created_at`, `updated_at`
- Constraints:
  - `starts_at < ends_at`
  - Exclusión (requiere `btree_gist`): `EXCLUDE USING gist (professional_id WITH =, tstzrange(starts_at, ends_at) WITH &&) WHERE (status = 'scheduled')`
- Índices: `(professional_id, starts_at)`, `(starts_at)` para el job de recordatorios

### email_notifications
- `id` uuid PK
- `appointment_id` FK a `appointments.id`
- `kind` enum (`confirmation`, `reminder`) NOT NULL
- `status` enum (`pending`, `sent`, `failed`) NOT NULL default `pending`
- `sent_at` timestamptz NULL, `error` text NULL
- Constraint UNIQUE `(appointment_id, kind)`: garantiza idempotencia (RN-NO-03)

### clinic_settings
- Fila única. `slot_minutes` int NOT NULL default 30. `timezone` text NOT NULL default `America/Argentina/Buenos_Aires`. `reminder_send_hour` smallint default 9.

## Seed data inicial

- 1 usuario administrador.
- 1 usuario de recepción.
- 2 profesionales ficticios con `working_hours` de lunes a viernes.
- `clinic_settings` con slot de 30 min.
- 10 pacientes ficticios, con emails de prueba reales controlados por el equipo (ver SU-02).
