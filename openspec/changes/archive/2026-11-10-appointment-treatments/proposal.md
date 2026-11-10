# Proposal: C-17 `appointment-treatments` — el turno se guarda con el tratamiento a realizar

## Why

Hoy un turno dice quién, con quién y cuándo, pero no para qué: ni la recepción ni el odontólogo saben si el paciente viene a una limpieza, a una extracción o a una consulta de ortodoncia, y el paciente que reserva online no puede decirlo. Con la agenda, la reserva pública (C-15, C-16) y los emails ya funcionando, alcanza con sumar un catálogo chico de tratamientos y un dato más en el turno para que la recepción y el paciente elijan el tratamiento al sacar el turno y que se vea en la agenda y en los emails.

## What Changes

- **Catálogo de tratamientos** (tabla nueva `treatments`): nombre único y activo o inactivo. Lo administra el administrador: alta, cambio de nombre y desactivación. No se borra: se desactiva (DD-143, DD-145).
- **Qué ofrece cada profesional** (tabla nueva `professional_treatments`): el administrador marca qué tratamientos ofrece cada profesional desde la pantalla de profesionales (DD-141).
- **El turno guarda el tratamiento** (`appointments.treatment_id`, FK opcional en la base): es obligatorio para todo turno nuevo, de recepción o reservado online, y tiene que ser un tratamiento activo que el profesional ofrece (DD-142). Los turnos anteriores quedan sin tratamiento (DD-148). Reprogramar conserva el tratamiento sin volver a validarlo. Desactivar un tratamiento o quitárselo a un profesional no toca los turnos existentes. La recepción no cambia el tratamiento de un turno ya creado: lo cancela y agenda otro (DD-144).
- **Sin duración variable**: todos los turnos siguen durando `slot_minutes` (DD-03, RN-TU-10). El tratamiento es un dato del turno y no cambia la grilla, las franjas, la superposición ni el constraint `ex_appointments_no_overlap`. La duración por tratamiento queda explícitamente como mejora futura.
- **Recepción** (panel de agendar de C-10): después de la franja y el paciente, elige el tratamiento de una lista con los que ofrece el profesional. El tratamiento se ve en el detalle del turno y en la grilla del día y de la semana (DD-146).
- **Paciente** (`/turnos`, C-15): elige el profesional y a continuación el tratamiento, después el día y la franja. La pantalla de "Turno registrado" y la de "Turno confirmado" muestran el tratamiento. Solo se ofrecen online los profesionales que tienen al menos un tratamiento activo.
- **Endpoint público nuevo** `GET /api/v1/public/professionals/{professional_id}/treatments`: solo id y nombre de los tratamientos activos que ofrece un profesional ofrecido, con el límite de pedidos de lectura. Se suma a la excepción de la regla dura 4.
- **Endpoints internos nuevos**: listar, crear y editar tratamientos (`/api/v1/treatments`), y leer y reemplazar los tratamientos de un profesional (`/api/v1/professionals/{professional_id}/treatments`). Las escrituras son solo del administrador. Cada uno con su test de permisos por rol.
- **Emails**: la confirmación, el recordatorio, el email para confirmar la reserva online y el aviso de vencimiento suman la línea "Tratamiento: <nombre>" cuando el turno tiene uno (DD-147). Reemplaza en parte DD-90 de C-11 (DD-147).
- **Seed de demostración**: 5 tratamientos ficticios de ejemplo ("Consulta", "Limpieza dental", "Extracción", "Arreglo de caries" y "Blanqueamiento"); la Dra. Ana Alvarez ofrece los 5 y el Dr. Bruno Benitez todos menos "Blanqueamiento" (DD-151).
- **KB**: el tratamiento como dato del turno entra al alcance; la duración variable por tratamiento sigue afuera.

## Capabilities

### New Capabilities
- `treatment-management`: reglas y casos de uso del catálogo de tratamientos, de los tratamientos que ofrece cada profesional y de la validación del tratamiento de un turno nuevo.
- `treatment-api`: endpoints internos del catálogo y de la asignación por profesional, con su matriz de permisos y sus códigos de error.
- `frontend-treatment-management`: pantalla de catálogo para el administrador y la sección "Tratamientos que ofrece" en la ficha del profesional.

### Modified Capabilities
- `database-schema`: tablas `treatments` y `professional_treatments`, y columna `treatment_id` en `appointments`.
- `appointment-use-cases`: agendar exige un tratamiento válido; reprogramar lo conserva.
- `appointment-api`: `treatment_id` en el pedido de agendar y tratamiento en las respuestas.
- `public-booking`: solo se ofrecen profesionales con tratamientos; la reserva exige un tratamiento válido.
- `public-booking-api`: endpoint público nuevo de tratamientos y `treatment_id` en la reserva.
- `access-control`: la ruta pública nueva entra en la lista y en la matriz.
- `email-templates`: línea de tratamiento en los cuatro emails de turno.
- `seed-data`: tratamientos de demostración y su asignación.
- `frontend-appointment-management`: elegir el tratamiento al agendar y verlo en el detalle.
- `frontend-agenda`: el tratamiento en la grilla.
- `frontend-public-booking`: paso de tratamiento y tratamiento en las pantallas de resultado.

## Impact

- **Backend**:
  - Dominio nuevo `app/domain/treatments/` (tipos, reglas puras, puerto) y casos de uso en `app/application/treatments.py`.
  - `book_appointment` y `book_online` reciben `treatment_id`; `Appointment` y `NewAppointment` suman `treatment_id`.
  - Rutas en `app/api/treatments.py`, en `app/api/professionals.py` y en `app/api/public.py`.
  - Migración `0005_treatments`; repositorios SQLAlchemy y en memoria.
  - Plantillas y armado de los emails en `app/infrastructure/email/templates.py`, `app/application/notifications.py` y `app/application/verification.py`.
  - `scripts/seed.py`.
- **Frontend**: `api/treatments.ts`, selector en `BookingPanel` y en `PublicBookingPage`, tratamiento en `DayColumn` y `AppointmentDetail`, página nueva `/tratamientos` (solo administración) y sección en la ficha del profesional.
- **Docs**: `CLAUDE.md` y `AGENTS.md` (regla dura 4 y roadmap), `CHANGES.md` (entrada C-17) y la KB: 01, 03, 04, 05, 06, 07, 09 (DD-141 a DD-151), 10 y 11.
- **Dependencias**: ninguna nueva. Ninguna variable de entorno nueva.
- **Governance**: MEDIO (lógica de agenda y datos de turnos) con una parte ALTA: un endpoint público nuevo, aunque de solo lectura y sin datos de pacientes. Las decisiones están resueltas (DD-141 a DD-151).
