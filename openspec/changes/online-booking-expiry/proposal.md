# Proposal: C-16 `online-booking-expiry`: vencimiento automático de reservas online

## Why

C-15 (`public-patient-booking`) deja las reservas online pendientes hasta que el paciente las confirma desde el email. Un pendiente vencido ya no se puede confirmar, pero sigue ocupando la franja hasta que la recepción lo cancela a mano. Este change lo cancela solo, libera la franja y le avisa al paciente por email. Se separó de C-15 por tamaño (Q-6 A, DD-139).

## What Changes

- **Tarea `vencer_reservas_pendientes`**: Celery Beat la corre cada 5 minutos. Cancela los turnos pendientes cuyo `pending_until` ya pasó, con el motivo "Reserva online no confirmada", borra el token y libera la franja.
- **Bloqueo de fila**: la tarea usa `FOR UPDATE SKIP LOCKED`. Hay tests de las carreras entre confirmar y vencer (en los dos órdenes) y entre dos pasadas simultáneas.
- **Email de cancelación por falta de confirmación (DD-140)**: tipo de notificación nuevo `booking_expired`, registrado en la misma transacción que la cancelación.
  - Usa los mismos reintentos, reencolado y registro de C-11 y C-12.
  - No se duplica, gracias al `UNIQUE (appointment_id, kind, appointment_starts_at)`.
  - No se envía si el turno se confirmó o se canceló por otra vía.
  - Va al email de la ficha, el mismo que recibió el enlace.
  - Lleva profesional, fecha y hora local y la indicación de que puede volver a reservar.
- **Migración `0004`**: agrega el valor `booking_expired` al tipo `notification_kind`.
- **KB**: RN-TU-14 (vencimiento automático) y una excepción a RN-NO-05 (un turno cancelado por vencimiento genera un único aviso).

## Capabilities

### New Capabilities
- `online-booking-expiry`: regla y caso de uso del vencimiento automático de reservas pendientes, y registro de su aviso.

### Modified Capabilities
- `notification-tasks`: programación cada 5 minutos de la tarea de vencimiento.
- `notification-sending`: un aviso `booking_expired` se envía para un turno cancelado por vencimiento.
- `email-templates`: plantilla del email de cancelación por falta de confirmación.
- `database-schema`: valor nuevo del tipo de notificación.

## Impact

- **Backend**: `app/application/public_booking.py` (`expire_pending_bookings`), el repositorio de turnos (`expire_pending`), el de notificaciones (`add_pending_booking_expired`), la regla de envío en `app/application/notifications.py`, la plantilla, la tarea y la programación de Beat, y la migración `0004`.
- **Sin cambios** en los endpoints, el frontend ni las variables de entorno (`ONLINE_BOOKING_HOLD_MINUTES` ya existe desde C-15).
- **Docs**: KB 04, 05, 07, 09 (DD-140 en adelante) y 11; `CHANGES.md` (entrada C-16).
- **Dependencia**: C-15 implementado y archivado.
- **Governance**: MEDIO. Es lógica de agenda y notificaciones, sin endpoints nuevos.
