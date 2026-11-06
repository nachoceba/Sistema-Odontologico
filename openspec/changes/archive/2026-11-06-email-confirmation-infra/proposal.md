# Proposal: email-confirmation-infra (C-11)

> **Gobernanza ALTA** (envío de emails a pacientes, configuración con credenciales SMTP, migración sobre `email_notifications` y servicios de Docker Compose). Las decisiones P-1 a P-9 de `design.md` fueron confirmadas por el usuario (opción A en todas) y se registran como DD-87 a DD-95.

## Why

Desde C-08 la agenda deja anotada una confirmación `pending` en `email_notifications` cada vez que se agenda o se reprograma, pero **ningún email sale**: el despachador posterior al commit es `NoOpNotificationDispatcher` y no existen el worker de Celery con tareas, el adaptador SMTP ni las plantillas. RN-NO-01 (confirmación al agendar) es parte del MVP (DD-06, IN-02) y C-12 (recordatorio diario) necesita toda esta infraestructura. Además quedan abiertos el proveedor SMTP gratuito de la demo (SU-02, pregunta de prioridad Alta), el contenido de la plantilla (`10_preguntas_abiertas.md`) y qué hacer con las filas `pending` acumuladas desde C-08 (DD-62).

## What Changes

- **Servidor SMTP (SU-02, P-1)**: Mailpit en desarrollo y en la demo; el adaptador es configurable por variables `SMTP_*`, sin elegir proveedor. El proveedor de producción queda abierto. La decisión se registra en `knowledge-base/09_decisiones_y_supuestos.md`.
- **Puerto `EmailSender`** (en `domain/`) y **adaptador SMTP** en `app/infrastructure/email/` con la librería estándar `smtplib`: STARTTLS y usuario opcionales, timeout corto, clasificación de errores en temporales y permanentes, y texto de error sin direcciones ni datos del paciente (RN-PR-01).
- **Plantillas `confirmation` y `reminder`** en texto plano (P-6): consultorio, paciente, profesional, fecha y hora en la zona del consultorio, dirección y teléfono; aviso de que el email es informativo (DD-06).
- **Caso de uso de envío** (`app/application/notifications.py`): bloquea la fila, envía solo si sigue `pending` y su `appointment_starts_at` coincide con el turno vigente (idempotencia), y la marca `sent` (con `sent_at`) o `failed` (con `error`). Un aviso de un turno que ya empezó no se envía (P-4). Errores temporales se reintentan unas pocas veces (P-5).
- **Aplicación Celery con tareas** en `app/infrastructure/tasks/`: `enviar_email` (worker) y `reencolar_pendientes` (Celery Beat cada 10 minutos, P-3). El despachador `NoOp` se reemplaza por uno que encola **después del commit** con `apply_async(retry=False)` y timeouts cortos de conexión a Redis: un Redis caído nunca rompe agendar ni reprogramar (RN-NO-04).
- **Registro de notificaciones ampliado**: leer y bloquear una pendiente, marcar `sent`/`failed`, listar `pending` antiguas; misma batería de contrato en memoria y PostgreSQL.
- **Migración `0002`** (P-3 = A): columna `created_at` en `email_notifications` para reconocer las pendientes antiguas.
- **Configuración del consultorio**: `ClinicSettings` suma `clinic_name`, `address`, `phone` y `reminder_send_hour` (ya están en la tabla y en el seed).
- **Protección de destinatarios en la demo** (P-2): variable opcional `EMAIL_REDIRECT_TO` que manda todos los emails a un buzón del equipo.
- **Docker Compose**: `worker` pasa a depender también de `db` y ejecuta las tareas; `beat` programa `reencolar_pendientes`.
- **Frontend** (P-8): los avisos "Turno agendado" y "Turno reprogramado" suman que se envía la confirmación por email al paciente.
- **Sin endpoints nuevos** (la matriz de permisos no cambia). **Sin dependencias nuevas** de Python ni de Node (Celery con Redis ya está; SMTP es librería estándar).
- **Fuera de alcance**: crear recordatorios y la tarea `enviar_recordatorios` (C-12; C-11 deja lista la plantilla `reminder` y el envío genérico), segunda pasada de `failed` (C-12), emails de cancelación (RN-NO-05 dice que cancelar no genera ninguno), ver el estado de los emails en pantalla.

## Capabilities

### New Capabilities
- `email-sending`: puerto `EmailSender`, adaptador SMTP (Mailpit en desarrollo y demo, configurable por variables), clasificación de errores, texto de error sin datos personales y redirección de destinatarios para la demo.
- `email-templates`: contenido de los emails `confirmation` y `reminder`, formato de fecha y hora en la zona del consultorio y datos del consultorio.
- `notification-sending`: caso de uso que envía una notificación pendiente con bloqueo e idempotencia, marca `sent`/`failed`, descarta avisos obsoletos o de turnos ya iniciados, reintenta errores temporales y reencola las pendientes antiguas.
- `notification-tasks`: tareas Celery `enviar_email` y `reencolar_pendientes`, programación en Celery Beat, publicación con timeout y sin reintentos, y garantía de que la API no depende de Redis.

### Modified Capabilities
- `notification-registration`: el despachador posterior al commit deja de no hacer nada y encola el envío; la batería de contrato del registro suma las operaciones de envío y de pendientes antiguas.
- `clinic-settings-repository`: la lectura de la configuración devuelve también nombre, dirección, teléfono y hora del recordatorio.
- `local-environment`: worker y beat ahora tienen tareas de negocio registradas y el worker necesita la base.
- `database-schema`: `email_notifications` registra cuándo se creó cada notificación (migración `0002`).
- `frontend-appointment-management`: los avisos de éxito de agendar y reprogramar mencionan el email de confirmación.

## Impact

- **Backend**: `app/domain/notifications/` (nuevo: decisión de envío, puerto `EmailSender`, errores), `app/domain/settings/types.py`, `app/domain/appointments/ports.py` (registro de notificaciones ampliado), `app/application/notifications.py` (nuevo), `app/infrastructure/email/` (adaptador SMTP y plantillas), `app/infrastructure/tasks/` (tareas, Beat, despachador), `app/infrastructure/notifications.py` (sale el `NoOp` de producción), repositorios de notificaciones y configuración (memoria y PostgreSQL), `app/api/dependencies.py` (despachador real), `app/core/config.py` (`EMAIL_REDIRECT_TO`).
- **Base de datos**: migración `0002_email_notifications_created_at` (P-3 = A), reversible.
- **Configuración**: `.env.example` suma `EMAIL_REDIRECT_TO` vacío (P-2 = A); si más adelante se usan credenciales SMTP, van solo en `.env` local, nunca en el repositorio ni en el frontend (regla dura 5).
- **Docker Compose**: `worker` con `depends_on: db`.
- **Frontend**: `src/appointments/messages.ts` y sus tests (P-8 = A).
- **Tests**: unitarios de dominio, plantillas y casos de uso con `EmailSender` falso; batería de contrato de notificaciones en memoria y PostgreSQL; Celery en modo inmediato; integración con PostgreSQL, Redis y Mailpit en el contenedor.
- **KB y roadmap**: SU-02 resuelto y decisiones P-1 a P-9 registradas como DD-87 en adelante; se cierra la pregunta del contenido de la plantilla en `10_preguntas_abiertas.md`; CHANGES.md marca lo que C-12 recibe hecho.
