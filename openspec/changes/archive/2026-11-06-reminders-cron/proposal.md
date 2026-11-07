# Proposal: reminders-cron (C-12)

> **Gobernanza ALTA** (emails automáticos a pacientes sin intervención de recepción, programación periódica en Celery Beat y zona horaria del consultorio). Las decisiones P-1 a P-7 de `design.md` están **CONFIRMADAS por el usuario** (opción A) y se registran como DD-96 a DD-102.

## Why

C-11 dejó funcionando el envío de la confirmación (worker, Mailpit, plantilla `reminder`, envío genérico por tipo y `reminder_send_hour` en `ClinicSettings`), pero **nadie crea recordatorios**: RN-NO-02 y US-011 piden que el paciente reciba un email el día anterior a su turno y hoy no sale ninguno. Falta la tarea periódica `enviar_recordatorios`, el caso de uso que elige los turnos del día siguiente en la zona del consultorio y el listado de turnos de todos los profesionales por rango, que C-08 dejó para este change (P-10, DD-66). También quedó para C-12 decidir si las notificaciones `failed` tienen una segunda pasada (DD-89).

## What Changes

- **Tarea `enviar_recordatorios`** en `app/infrastructure/tasks/`, programada por Celery Beat **cada hora en punto**; solo actúa cuando la hora local del consultorio es igual a `clinic_settings.reminder_send_hour` (el valor se lee en cada pasada, sin reiniciar `beat`). La aplicación Celery mantiene `timezone` del consultorio y `enable_utc = True`. **No hay endpoint HTTP** (por eso no hay chequeo de rol nuevo).
- **Caso de uso `enviar_recordatorios`** (`app/application/`): calcula el día siguiente en la zona del consultorio (P-4), toma los turnos `scheduled` que **empiezan** ese día, de todos los profesionales (P-5), registra un `reminder` `pending` por turno sin recordatorio para ese horario y lo envía (P-1). Un fallo se registra y el lote sigue (US-011). Registra en el log solo cantidades (`processed`, `sent`, `failed` y `pending`, P-1), nunca datos del paciente.
- **Regla pura** en `app/domain/notifications/`: a partir del instante actual, la zona y la hora configurada decide si la pasada actúa y qué día local apunta.
- **Pacientes inactivos**: sus turnos `scheduled` futuros **siguen recibiendo recordatorio** (DD-76, RN-NO-05); no se saltean.
- **Repositorio de turnos**: nuevo listado de los turnos `scheduled` de **todos** los profesionales cuyo inicio cae en un rango `[desde, hasta)`, en memoria y PostgreSQL, con su batería de contrato.
- **Registro de notificaciones**: registrar un `reminder` `pending` solo si el turno sigue `scheduled` con ese mismo horario, sin duplicar (RN-NO-03), en memoria y PostgreSQL.
- **Segunda pasada de `failed`** (P-2): se recomienda **no** hacerla; la decisión queda registrada.
- **Disparo manual** (P-6): la tarea acepta una opción para forzar la pasada fuera de la hora configurada, solo desde la consola del contenedor, para la demo con Mailpit y el smoke test de C-13.
- **Sin migraciones, sin dependencias nuevas, sin variables de entorno nuevas y sin cambios en el frontend.** Docker Compose ya tiene `worker` y `beat`; no cambia.
- **Fuera de alcance**: ventana de 24 h exactas (IN-01, mejora posterior), recuperar una pasada perdida en otra hora (P-3), avisos por cancelación, pantallas de estado de emails, elegir proveedor SMTP de producción (SU-02).

## Capabilities

### New Capabilities
- `reminder-scheduling`: cuándo actúa la pasada horaria, qué turnos reciben recordatorio (día siguiente en la zona del consultorio, solo `scheduled`, todos los profesionales, pacientes inactivos incluidos), idempotencia ante ejecuciones dobles, fallo parcial que no corta el lote, registro de cantidades sin datos personales y disparo manual.

### Modified Capabilities
- `appointment-repository`: suma el listado de turnos `scheduled` de todos los profesionales que empiezan en un rango (DD-66).
- `notification-registration`: la batería de contrato suma registrar un `reminder` `pending` condicionado a que el turno siga vigente con ese horario.
- `notification-sending`: la regla de `failed` deja de remitir a C-12 y fija que no hay segunda pasada (P-2); un recordatorio que falla de forma temporal en la pasada sigue el camino del reencolado (P-1).
- `notification-tasks`: tercera tarea propia `enviar_recordatorios`, segunda entrada de Beat (cada hora) y el inventario de rutas sigue sin endpoints de notificaciones.
- `local-environment`: el `worker` lista también `enviar_recordatorios` y `beat` la programa.

## Impact

- **Código**: `app/domain/notifications/` (regla de la pasada), `app/domain/appointments/ports.py` (listado global y alta de `reminder`), `app/application/` (caso de uso de recordatorios), `app/infrastructure/in_memory/` y `app/infrastructure/db/repositories/` (implementaciones), `app/infrastructure/tasks/` (tarea, Beat y armado de dependencias).
- **Tests**: unitarios de la regla pura (bordes de hora y de día local), del caso de uso con repositorios en memoria, reloj fijo y remitente falso; contrato en memoria y PostgreSQL; tareas en modo inmediato; integración con Mailpit en el contenedor.
- **API**: ninguna ruta nueva; el inventario de rutas y la matriz de permisos no cambian (regla dura 4).
- **Datos**: sin migraciones; usa `email_notifications` (`kind = reminder`) y el índice `(starts_at)` de `appointments` que ya existe.
- **Reglas duras**: la no superposición no se toca (el change no escribe turnos); `domain/` sigue sin FastAPI, SQLAlchemy, Celery ni Redis; secretos solo en `.env` local.
- **Documentación** (al archivar): `knowledge-base/09` (DD-96 en adelante), `11_recordatorios_email.md`, `07_flujos_principales.md` Flujo 4, `10_preguntas_abiertas.md`, `CHANGES.md`, `CLAUDE.md`/`AGENTS.md` y `README.md`.
