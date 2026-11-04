# Spec Delta: appointment-unit-of-work

## Purpose

Garantizar que cada operación de agenda escriba el turno y sus notificaciones como un todo (o nada) y que, ante dos pedidos simultáneos por el mismo horario contra PostgreSQL, gane exactamente uno y el otro reciba un error claro (cierra DD-36 y el pendiente de concurrencia de C-02).

## ADDED Requirements

### Requirement: Turno y notificaciones en una sola transacción (DD-36)

Agendar, cancelar y reprogramar SHALL escribir el turno y los cambios en sus notificaciones dentro de una única transacción. Si cualquier escritura de la operación falla (el turno o la notificación), MUST NOT quedar ningún cambio guardado: el turno vuelve a como estaba y no queda ninguna notificación nueva ni borrada. La misma garantía MUST cumplirse en la implementación en memoria (usada por los tests de casos de uso) y en la de PostgreSQL.

#### Scenario: Todo se guarda junto (esperado)
- **WHEN** se agenda un turno válido
- **THEN** después de la operación existen el turno y su confirmación pendiente, y ambos son visibles desde otra conexión recién cuando la operación terminó

#### Scenario: Falla al registrar la notificación (error)
- **WHEN** la escritura de la confirmación falla después de haber escrito el turno, dentro de la misma operación de agendar
- **THEN** la operación termina con error y no queda ni el turno ni la notificación

#### Scenario: Falla al reprogramar después de borrar pendientes (borde)
- **WHEN** al reprogramar se borraron las pendientes de la fecha anterior y la escritura del nuevo horario es rechazada por la base por superposición
- **THEN** la operación se rechaza con `SLOT_TAKEN`, el turno conserva su horario anterior y sus notificaciones pendientes siguen existiendo

### Requirement: Dos pedidos simultáneos por el mismo horario (RN-TU-01, US-007, regla dura 3 y 6)

Cuando dos pedidos agendan, o uno agenda y otro reprograma, turnos del mismo profesional que se superponen al mismo tiempo, la base de datos SHALL aceptar exactamente uno; el otro MUST terminar con `SLOT_TAKEN` (409 en la API, "el horario acaba de ocuparse") aunque las validaciones del dominio de ambos hayan pasado. Esta garantía MUST probarse contra PostgreSQL real con dos sesiones abiertas a la vez, no con una simulación en memoria.

#### Scenario: Dos recepcionistas agendan el mismo slot (esperado)
- **WHEN** dos sesiones validan y escriben a la vez un turno de la Dra. A a las 10:00, la primera confirma su transacción y la segunda intenta confirmar después
- **THEN** la primera queda guardada, la segunda termina con `SLOT_TAKEN`
- **AND** en la base hay un solo turno `scheduled` de la Dra. A a las 10:00 y una sola confirmación pendiente

#### Scenario: Reprogramar compite con agendar (borde)
- **WHEN** una sesión reprograma un turno de la Dra. A a las 11:00 mientras otra agenda a otro paciente con la Dra. A a las 11:00
- **THEN** exactamente una de las dos operaciones se guarda y la otra termina con `SLOT_TAKEN`; si perdió la reprogramación, el turno conserva su horario anterior

#### Scenario: Pedidos simultáneos con profesionales distintos (borde)
- **WHEN** dos sesiones agendan a la vez a las 10:00, una con la Dra. A y otra con el Dr. B, para pacientes distintos
- **THEN** las dos se guardan
