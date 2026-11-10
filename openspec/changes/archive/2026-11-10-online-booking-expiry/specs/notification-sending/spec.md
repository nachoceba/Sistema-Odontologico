# Spec Delta: notification-sending

## MODIFIED Requirements

### Requirement: Avisos de turnos que ya empezaron o no están vigentes (P-4)

Si al procesar una notificación `pending` de tipo `confirmation` o `reminder` su turno ya empezó (inicio anterior o igual al instante del procesamiento) o no está `scheduled`, el sistema SHALL NOT enviar el email y MUST marcarla `failed` con `error = EXPIRED` y sin `sent_at`, para que no se vuelva a encolar. Esto cubre las confirmaciones `pending` acumuladas desde C-08 (DD-62) de turnos ya pasados.

Una notificación `booking_expired` (C-16) se envía solo si su turno está `cancelled` con el motivo "Reserva online no confirmada", sigue con el mismo inicio y ese inicio no llegó. Si no se cumple alguna de esas condiciones, por ejemplo porque el turno se confirmó, MUST quedar `failed` con `error = EXPIRED` sin enviar nada.

#### Scenario: Pendiente acumulada de un turno pasado (esperado)
- **WHEN** al activar C-11 hay una confirmación `pending` registrada en C-08 de un turno que fue ayer
- **THEN** no se envía ningún email y queda `failed` con `error = EXPIRED`

#### Scenario: Pendiente acumulada de un turno futuro (esperado)
- **WHEN** al activar C-11 hay una confirmación `pending` registrada en C-08 de un turno `scheduled` de la semana próxima
- **THEN** la confirmación se envía y queda `sent`

#### Scenario: Turno que empieza justo ahora (borde)
- **WHEN** se procesa la confirmación a las 10:00:00 de un turno que empieza a las 10:00
- **THEN** no se envía y queda `failed` con `error = EXPIRED`

#### Scenario: Turno ya marcado atendido (borde)
- **WHEN** la confirmación sigue `pending` y el turno ya está `completed`
- **THEN** no se envía y queda `failed` con `error = EXPIRED`

#### Scenario: Aviso de vencimiento de un turno cancelado por la tarea (esperado)
- **WHEN** se procesa un `booking_expired` de un turno `cancelled` con el motivo "Reserva online no confirmada" que empezaba mañana
- **THEN** se envía y queda `sent`

#### Scenario: Aviso de vencimiento con otro motivo de cancelación (borde)
- **WHEN** se procesa un `booking_expired` y el turno figura cancelado con otro motivo
- **THEN** no se envía y queda `failed` con `error = EXPIRED`
