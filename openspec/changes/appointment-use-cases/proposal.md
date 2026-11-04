# Proposal: appointment-use-cases (C-08)

> **Gobernanza MEDIA** (lógica de negocio de la agenda). Este change solo propone: no se escribe código hasta que la usuaria confirme las decisiones P-1 a P-12 de `design.md` (grupo 0 de `tasks.md`). Las specs ya están escritas con la opción recomendada de cada pregunta; si la usuaria elige otra, se ajustan con `/opsx:update` antes de implementar.

## Why

Todas las piezas de la agenda existen por separado y probadas (reglas puras de C-05a a C-05d, esquema con constraint de exclusión y repositorios PostgreSQL de C-02, login y permisos de C-03, repositorio de profesionales de C-04), pero **todavía no hay forma de agendar, cancelar, reprogramar ni marcar un turno**: no hay casos de uso ni endpoints que las unan. US-007 a US-010 son el corazón del MVP y bloquean C-10 (pantallas de turnos) y C-11 (emails). Además quedaron tres pendientes heredados que solo se pueden cerrar acá: el test de concurrencia real contra PostgreSQL (C-02), la unidad de trabajo que agrupa turno y notificación (DD-36) y el test de punta a punta "un odontólogo no ve ni modifica turnos ajenos" contra un endpoint real (DD-53).

## What Changes

- **Casos de uso de turnos** en `app/application/appointments.py` (sin FastAPI), con reloj inyectable:
  - `agendar_turno` (US-007): valida paciente existente y activo (RN-PA-04), profesional existente y activo (P-5), las reglas de `validate_appointment` (RN-TU-01 a RN-TU-04, RN-TU-12) con la configuración real del consultorio, y que el paciente no tenga otro turno a la misma hora (P-3); guarda y registra la confirmación (P-1).
  - `cancelar_turno` (US-008): motivo obligatorio (P-7), solo antes del inicio (DD-21), libera el slot (RN-TU-05) y descarta las notificaciones pendientes (RN-NO-05, P-2).
  - `reprogramar_turno` (US-009): solo cambia fecha y hora con el mismo profesional (P-6); elegibilidad (DD-24), paciente activo (DD-25) y las mismas validaciones de agendar sin chocar consigo mismo; atómico (RN-TU-06); rechaza el mismo horario (P-12); reemplaza la confirmación pendiente (RN-NO-05).
  - `marcar_atencion` (US-010): `completed` o `no_show` solo con el turno `scheduled` ya iniciado (RN-TU-07, DD-22, DD-23); el odontólogo solo los propios (RN-AU-04); quién más puede marcar según P-4.
  - Consultas: detalle de un turno, turnos de un profesional en un rango y franjas (slots) de un día (P-9).
- **Endpoints `/api/v1/appointments`** (y `/api/v1/professionals/{id}/slots`, P-9) con esquemas Pydantic, JWT, `require_role` y la regla de alcance del odontólogo (`can_access_professional`, DD-53); **test de permisos por rol en cada endpoint** (tres roles y sin token, regla dura 4) y el test de punta a punta de DD-53.
- **Unidad de trabajo** (puerto en `domain/`, implementación en memoria y PostgreSQL): turno y notificación en una sola transacción; si algo falla no queda nada escrito (cierra DD-36).
- **Registro de notificaciones** (P-1, P-2): fila `confirmation` `pending` en `email_notifications` al agendar y reprogramar, en la misma transacción; las `pending` de la fecha anterior se borran al reprogramar o cancelar. Después del commit se llama a un despachador que en C-08 **no hace nada**; C-11 lo reemplaza por el encolado en Celery y el envío real. Ningún email sale en C-08.
- **Concurrencia real**: test de integración con dos sesiones simultáneas contra PostgreSQL; el constraint de exclusión gana la carrera y la API responde 409 `SLOT_TAKEN` (regla dura 3 y 6, US-007 "dos recepcionistas…").
- **Errores nuevos** en el formato uniforme (tabla en `design.md` D-8): motivos de validación de agenda, transiciones, paciente y profesional.
- **Sin migraciones** (se usan `appointments` y `email_notifications` tal como las dejó C-02). **Sin variables de entorno nuevas. Sin dependencias nuevas. Sin frontend** (es C-10).

## Capabilities

### New Capabilities
- `appointment-use-cases`: casos de uso de agendar, cancelar, reprogramar, marcar atención y consultar turnos y franjas, con el orden de validación, los errores de negocio y las reglas de alcance por rol.
- `appointment-api`: contrato HTTP de `/api/v1/appointments` y de las franjas de un profesional, formato de fechas, códigos de respuesta y matriz de permisos por rol probada en cada endpoint.
- `appointment-unit-of-work`: transacción única que agrupa la escritura del turno y de sus notificaciones, y la garantía ante dos pedidos simultáneos contra PostgreSQL.
- `notification-registration`: qué deja registrado C-08 en `email_notifications` (confirmación pendiente, descarte de pendientes) y el despachador posterior al commit sin efecto, que es el borde con C-11.

### Modified Capabilities
- `error-model`: la tabla de códigos a estados HTTP suma los códigos de turnos (404 de paciente y profesional, 409 de conflictos de agenda y de estado, 400 de reglas de validación).
- `access-control`: la regla de alcance del odontólogo pasa a probarse contra los endpoints reales de turnos (antes solo con una ruta de prueba, DD-53).

## Impact

- **Backend**: `app/domain/appointments/` (errores de casos de uso, regla de doble turno del paciente, puerto de unidad de trabajo y de notificaciones), `app/application/appointments.py` (nuevo), `app/api/appointments.py` (router nuevo), `app/api/router.py`, `app/api/errors.py`, `app/api/dependencies.py` (fábricas de unidad de trabajo, reloj y despachador), `app/infrastructure/in_memory/` y `app/infrastructure/db/repositories/` (unidad de trabajo y notificaciones; los repositorios SQL de turnos, horarios, pacientes, profesionales y configuración pasan a poder usar la sesión de la unidad de trabajo sin cambiar su contrato).
- **Tests**: unitarios de dominio y de casos de uso (en memoria), de API con permisos por rol, batería de contrato de notificaciones (memoria + PostgreSQL), integración de concurrencia y de rollback contra PostgreSQL.
- **Base de datos**: sin migraciones.
- **KB y roadmap**: P-1 a P-12 confirmadas (2026-11-03) y registradas como DD-62 a DD-67 en `09_decisiones_y_supuestos.md`; se cierra la pregunta H-2 de `10_preguntas_abiertas.md` (P-3); si P-9 = A, CHANGES.md anota que C-09 consume los endpoints de lectura de C-08; si P-10 = A, el listado global por rango pasa a C-12.
- **Changes siguientes**: C-10 consume estos endpoints; C-11 implementa el despachador real y el envío; C-12 crea los recordatorios.
