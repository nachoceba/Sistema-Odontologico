# Spec Delta: online-booking-expiry

## Purpose

Vencimiento automático de las reservas online que no se confirmaron a tiempo: cancela el turno pendiente, libera la franja y registra un único aviso por email al paciente, sin carreras con la confirmación.

## ADDED Requirements

### Requirement: Vencimiento automático de reservas pendientes (DD-132, RN-TU-05, RN-TU-14)

Una tarea periódica SHALL cancelar cada turno `scheduled` pendiente de confirmación cuyo `pending_until` ya pasó:

- Le pone el motivo "Reserva online no confirmada", borra `pending_until` y el hash del token y libera la franja.
- MUST tomar cada fila con bloqueo y saltear las que otro proceso tiene tomadas.
- Repetirla no cambia nada.
- Cancela aunque el turno ya haya empezado, porque lo cancela el sistema y no la recepción.
- Registra solo la cantidad de turnos vencidos, sin datos de pacientes.
- Los turnos confirmados y los de la recepción nunca se tocan.

#### Scenario: Pendiente vencido (esperado)
- **WHEN** la tarea corre y una reserva venció hace 2 minutos sin confirmarse
- **THEN** el turno queda `cancelled` con el motivo "Reserva online no confirmada" y la franja vuelve a ser reservable para la página pública y para la recepción

#### Scenario: Pendiente todavía vigente (borde)
- **WHEN** la tarea corre y a una reserva le faltan 5 minutos para vencer
- **THEN** no la toca

#### Scenario: Vencimiento exacto (borde)
- **WHEN** la tarea corre en el mismo instante que `pending_until`
- **THEN** la cancela, porque la confirmación exige un instante anterior a `pending_until`

#### Scenario: Turnos confirmados y de recepción (error)
- **WHEN** la tarea corre
- **THEN** ningún turno confirmado ni agendado por la recepción cambia

#### Scenario: Confirmar y vencer a la vez, gana la confirmación (borde)
- **WHEN** la confirmación toma la fila primero y la tarea llega mientras tanto
- **THEN** el turno queda confirmado, hay una sola confirmación de C-11 y ningún aviso de vencimiento

#### Scenario: Confirmar y vencer a la vez, gana el vencimiento (borde)
- **WHEN** la tarea toma la fila primero y la confirmación llega mientras tanto
- **THEN** el turno queda cancelado, la confirmación recibe `CONFIRMATION_LINK_INVALID` y no se registra confirmación de C-11

#### Scenario: Dos pasadas a la vez (borde)
- **WHEN** dos pasadas de la tarea corren al mismo tiempo
- **THEN** cada reserva vencida se cancela una sola vez

### Requirement: Aviso de cancelación por falta de confirmación (DD-140, RN-NO-05, RN-NO-06)

Al cancelar una reserva por vencimiento, la tarea SHALL registrar en la misma transacción una notificación `booking_expired` en estado `pending`, con el inicio del turno, y despacharla después del commit con el mecanismo de C-11. Es la única notificación que genera un turno cancelado (excepción a RN-NO-05). Se envía al email de la ficha del paciente, que es la misma dirección que recibió el enlace de verificación. Ni una cancelación de la recepción ni una confirmación la registran nunca. El `UNIQUE (appointment_id, kind, appointment_starts_at)` MUST impedir un segundo aviso aunque la tarea corra dos veces.

#### Scenario: Aviso registrado con la cancelación (esperado)
- **WHEN** la tarea cancela una reserva vencida
- **THEN** en la misma transacción queda una notificación `booking_expired` `pending` y, después del commit, se encola su envío

#### Scenario: Cancelación de la recepción (borde)
- **WHEN** la recepción cancela un turno pendiente antes de que venza
- **THEN** no se registra ningún aviso `booking_expired`

#### Scenario: La tarea corre dos veces (borde)
- **WHEN** la tarea vuelve a correr sobre una reserva ya cancelada por vencimiento
- **THEN** no la vuelve a tocar y sigue habiendo un solo aviso

#### Scenario: Falla al encolar (borde, RN-NO-04)
- **WHEN** Redis no responde al despachar el aviso
- **THEN** la cancelación queda hecha, el aviso queda `pending` y lo toma `reencolar_pendientes`
