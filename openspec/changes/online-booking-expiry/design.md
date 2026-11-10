# Design: C-16 `online-booking-expiry`

La motivación está en `proposal.md` y el comportamiento en las specs del change. Depende de C-15 `public-patient-booking`, de donde salen `pending_until`, `confirmation_token_hash`, `confirm_online_booking` con `FOR UPDATE`, `ONLINE_BOOKING_HOLD_MINUTES` y las etiquetas de la recepción.

## Context

- **De C-15**: un pendiente es `scheduled` con `pending_until` no nulo. La confirmación exige `now < pending_until` y toma la fila con `FOR UPDATE`. Hasta este change, nada cancela solo.
- **De C-11 y C-12**: `email_notifications` con `UNIQUE (appointment_id, kind, appointment_starts_at)`, `deliver_notification` (reclamo con `FOR UPDATE SKIP LOCKED` y regla `EXPIRED`), reintentos (DD-89), `reencolar_pendientes` cada 10 minutos y la programación de Beat en `app/infrastructure/tasks/`. `deliver_notification` toma el destinatario de la ficha.

## Goals / Non-Goals

**Goals:**
- Liberar sola la franja de un pendiente vencido.
- Avisar una sola vez al paciente.
- Sin carreras con la confirmación.

**Non-Goals:**
- Cambiar el plazo, que sigue en `ONLINE_BOOKING_HOLD_MINUTES`.
- Endpoints nuevos.
- Cambios en el frontend: las etiquetas de C-15 ya muestran "Cancelado".
- Borrar fichas creadas por reservas vencidas (Q-5 A: la ficha queda).

## Decisions

### D-1 (DD-132): tarea cada 5 minutos con bloqueo de fila

- **Caso de uso**: `expire_pending_bookings(deps, now)` en `app/application/public_booking.py`.
- **Repositorio**: `AppointmentRepository.expire_pending(now, limit=200)` corre `SELECT … WHERE status = 'scheduled' AND pending_until <= now ORDER BY pending_until FOR UPDATE SKIP LOCKED LIMIT 200`.
- **Por cada fila**: `status = cancelled`, `cancel_reason = 'Reserva online no confirmada'` (constante compartida `EXPIRED_BOOKING_REASON`), y `pending_until` y el hash en NULL.
- **Transacción**: todo va en la misma unidad de trabajo que el registro del aviso.
- **Tarea**: `vencer_reservas_pendientes` en Beat cada 5 minutos, como C-12. El log lleva solo `expired=N`.
- **Carrera**: la confirmación de C-15 bloquea la misma fila. Si llega primero, `SKIP LOCKED` la saltea, o al releer la tarea la ve con `pending_until` en NULL. Si la tarea llega primero, la confirmación ve `cancelled` y responde 410.
- **Límite exacto**: lo resuelve la desigualdad estricta de la confirmación (`now < pending_until`) contra `pending_until <= now` de la tarea.
- **Alternativa descartada**: vencer "de forma perezosa" al calcular franjas. Mezcla escrituras con lecturas públicas y no manda el aviso si nadie mira la agenda.

### D-2 (DD-140): aviso `booking_expired` con el mecanismo de C-11

- **Migración `0004`**: `ALTER TYPE notification_kind ADD VALUE 'booking_expired'`, en su propia migración y sin usar el valor en la misma transacción. La reversión, si no hay filas, recrea el tipo con los dos valores originales. Si las hay, falla.
- **Registro**: `NotificationRepository.add_pending_booking_expired(appointment_id, starts_at)` con `INSERT … ON CONFLICT DO NOTHING`, dentro de la misma transacción que la cancelación. Después del commit se despacha con el despachador existente.
- **Reintentos y reencolado**: son los de C-11, porque es una fila `pending` más. Así, un fallo temporal la deja `pending` y la levanta `reencolar_pendientes`.
- **Regla de envío** (`deliver_notification`): para `booking_expired`, envía solo si el turno está `cancelled` con `EXPIRED_BOOKING_REASON`, mantiene el mismo inicio y `now < starts_at`. Si no, queda `failed` con `EXPIRED`. `confirmation` y `reminder` siguen igual.
- **Destinatario**: el email de la ficha, que es la dirección que recibió el enlace. Si el DNI era nuevo, la ficha se creó con el email escrito; si existía, el enlace también fue a la ficha.
- **Plantilla**: `render_email` suma el tipo `booking_expired`, en texto plano, con la fecha local que ya usan las plantillas de C-11 y con `PUBLIC_APP_URL/turnos`.
- **Alternativa descartada**: mandarlo directo desde la tarea, sin una fila en `email_notifications`. Pierde la idempotencia, los reintentos y el reencolado.

### D-3: KB

- **`05_reglas_de_negocio.md`**:
  - RN-TU-14 (vencimiento automático; ya redactada en C-15).
  - RN-NO-05 suma: "salvo el aviso único de cancelación por falta de confirmación de una reserva online".
  - RN-NO-06 suma el aviso de vencimiento.
- **`04_modelo_de_datos.md`**: el `kind` suma `booking_expired`.
- **`07_flujos_principales.md`**: el Flujo 6 suma la rama "vence".
- **`11_recordatorios_email.md`**: los tipos de email suman `booking_expired`, y las tareas suman `vencer_reservas_pendientes`.
- **`09_decisiones_y_supuestos.md`**: DD-140.

## Risks / Trade-offs

- [La franja queda retenida hasta 5 minutos de más] → se acepta. Es la frecuencia de Beat, configurable en el código.
- [Un aviso de vencimiento para una ficha que alguien creó con un DNI ajeno y su propio email] → el aviso va al email de esa ficha, igual que el enlace: no llega a terceros nuevos. La recepción corrige la ficha (Q-5 A).
- [`ALTER TYPE … ADD VALUE` no se puede revertir con facilidad] → la reversión recrea el tipo y falla si hay filas, sin tocar datos.
- [Turno que vence ya empezado] → se cancela igual y no se manda aviso (`now >= starts_at` → `EXPIRED`). Con la anticipación de 6 h y el plazo de 60 minutos no pasa en la práctica.

## Migration Plan

1. Migración `0004` con el servicio `migrate`. Rollback: `alembic downgrade 0003` si no hay avisos `booking_expired`.
2. Reiniciar `beat` y `worker` para que tomen la tarea nueva.
