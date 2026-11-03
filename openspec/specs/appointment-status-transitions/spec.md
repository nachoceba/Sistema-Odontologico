# appointment-status-transitions Specification

## Purpose
Decidir, sin base de datos ni reloj propio, si un turno puede pasar de su estado actual a otro (cancelar, marcar atendido, marcar ausente) o ser reprogramado, con un motivo único cuando no puede (RN-TU-05, RN-TU-06, RN-TU-07, US-010, DD-05).

## Requirements
> Datos comunes de los escenarios (salvo que el escenario diga otra cosa): zona del consultorio `America/Argentina/Buenos_Aires` (UTC-3, sin horario de verano, SU-01); el turno de la Dra. A empieza el lunes 5 de octubre de 2026 a las 10:00 locales (13:00 UTC) y termina a las 10:30; "ahora" (`now`) se recibe como dato, nunca se lee del reloj. Los estados son `scheduled`, `cancelled`, `completed` y `no_show`. Todos los datos son ficticios. Las decisiones de dominio P-1 a P-10 fueron confirmadas por el usuario (ver `design.md` y DD-21 a DD-30 en la KB).

### Requirement: Resultado de un cambio de estado

La decisión SHALL recibir el estado actual, el estado pedido, el inicio del turno (UTC) y `now` (UTC), y devolver un resultado aceptado o rechazado con exactamente un motivo cuando se rechaza, sin lanzar excepciones por motivos de negocio. La decisión MUST NOT modificar el turno: solo informa si el cambio es posible. Si el inicio del turno o `now` no tienen zona horaria, MUST lanzar `ValueError` (error de programación, misma convención que `appointment-creation`).

#### Scenario: Datetime sin zona horaria
- **DADO** un turno `scheduled` y un `now` sin zona horaria
- **CUANDO** se pide pasarlo a `cancelled`
- **ENTONCES** se lanza `ValueError`

### Requirement: Matriz de transiciones permitidas

Solo SHALL aceptarse estas transiciones: `scheduled` → `cancelled` (RN-TU-05), `scheduled` → `completed` y `scheduled` → `no_show` (RN-TU-07). Toda otra combinación MUST rechazarse con un único motivo, evaluado en este orden:

1. Estado actual `cancelled` → `CANCELLED_IS_FINAL` (RN-TU-07: un turno cancelado no cambia de estado).
2. Estado actual `completed` o `no_show` → `ATTENDANCE_ALREADY_RECORDED`.
3. Estado pedido `scheduled` (incluido `scheduled` → `scheduled`) → `INVALID_TARGET_STATUS` (sin respaldo en la KB: no hay reactivación ni cambio nulo).
4. Reglas de tiempo de los requisitos siguientes.

#### Scenario: Cancelar un turno agendado antes de su inicio (funcionamiento esperado)
- **DADO** el turno `scheduled` de la Dra. A y `now` el sábado 3 de octubre de 2026 a las 10:00 locales
- **CUANDO** se pide pasarlo a `cancelled`
- **ENTONCES** el resultado es aceptado (RN-TU-05)

#### Scenario: Un turno cancelado no cambia de estado (error de negocio)
- **DADO** un turno `cancelled` y `now` el lunes a las 11:00 locales
- **CUANDO** se pide pasarlo a `completed`, a `no_show`, a `scheduled` o otra vez a `cancelled`
- **ENTONCES** cada pedido se rechaza con el motivo `CANCELLED_IS_FINAL` (RN-TU-07)

#### Scenario: Asistencia ya registrada (error de negocio)
- **DADO** un turno `completed` y `now` el lunes a las 11:00 locales
- **CUANDO** se pide pasarlo a `no_show` o a `cancelled`
- **ENTONCES** cada pedido se rechaza con el motivo `ATTENDANCE_ALREADY_RECORDED`
- **Y** lo mismo ocurre para un turno `no_show` que se pide pasar a `completed`

#### Scenario: No se vuelve a `scheduled`
- **DADO** un turno `scheduled` y `now` el sábado 3 de octubre de 2026
- **CUANDO** se pide pasarlo a `scheduled`
- **ENTONCES** se rechaza con el motivo `INVALID_TARGET_STATUS`

### Requirement: Marcar atendido o ausente solo con el turno ya iniciado (RN-TU-07, US-010)

`scheduled` → `completed` y `scheduled` → `no_show` SHALL aceptarse solo si el turno ya inició, es decir, si `now >= inicio del turno` (el inicio exacto cuenta como iniciado). Si `now` es anterior al inicio, MUST rechazarse con el motivo `NOT_STARTED_YET`. No hay límite posterior: un turno de días atrás que quedó `scheduled` puede marcarse.

#### Scenario: Marcar atendido después del inicio (funcionamiento esperado)
- **DADO** el turno `scheduled` de la Dra. A y `now` el lunes a las 10:20 locales
- **CUANDO** se pide pasarlo a `completed`
- **ENTONCES** el resultado es aceptado

#### Scenario: Marcar ausente antes del inicio (error de negocio)
- **DADO** el turno `scheduled` de la Dra. A y `now` el lunes a las 09:59 locales
- **CUANDO** se pide pasarlo a `no_show`
- **ENTONCES** se rechaza con el motivo `NOT_STARTED_YET`

#### Scenario: Marcar en el instante exacto del inicio (borde)
- **DADO** el turno `scheduled` de la Dra. A y `now` el lunes a las 10:00:00 locales
- **CUANDO** se pide pasarlo a `completed`
- **ENTONCES** el resultado es aceptado

#### Scenario: Marcar un turno de días atrás (borde)
- **DADO** el turno `scheduled` de la Dra. A y `now` el jueves 8 de octubre de 2026
- **CUANDO** se pide pasarlo a `no_show`
- **ENTONCES** el resultado es aceptado

#### Scenario: El inicio se compara en instantes, no en hora local
- **DADO** el turno `scheduled` de la Dra. A (13:00 UTC) y `now` igual a 12:59 UTC expresado con desplazamiento UTC-3 (09:59 locales)
- **CUANDO** se pide pasarlo a `completed`
- **ENTONCES** se rechaza con el motivo `NOT_STARTED_YET`

### Requirement: Cancelar solo antes del inicio (RN-TU-05)

`scheduled` → `cancelled` SHALL aceptarse solo si `now` es anterior al inicio del turno. Si el turno ya inició (`now >= inicio`), MUST rechazarse con el motivo `ALREADY_STARTED`; para un turno al que el paciente no vino corresponde `no_show`. Cancelar no exige anticipación mínima (RN-TU-12 aplica solo a crear).

#### Scenario: Cancelar un minuto antes del inicio (borde)
- **DADO** el turno `scheduled` de la Dra. A y `now` el lunes a las 09:59 locales
- **CUANDO** se pide pasarlo a `cancelled`
- **ENTONCES** el resultado es aceptado

#### Scenario: Cancelar un turno ya iniciado (error de negocio)
- **DADO** el turno `scheduled` de la Dra. A y `now` el lunes a las 10:00 locales
- **CUANDO** se pide pasarlo a `cancelled`
- **ENTONCES** se rechaza con el motivo `ALREADY_STARTED`

### Requirement: Turnos que admiten reprogramación (RN-TU-06)

Reprogramar SHALL admitirse solo para un turno `scheduled` que todavía no inició (`now` anterior al inicio). La decisión MUST rechazar con un único motivo, en este orden: `CANCELLED_IS_FINAL` si está `cancelled`, `ATTENDANCE_ALREADY_RECORDED` si está `completed` o `no_show`, `ALREADY_STARTED` si ya inició. Esta decisión solo cubre el turno original: la validez del nuevo horario la decide `appointment-creation` (RN-TU-06) y la atomicidad la garantiza el caso de uso (fuera de este change).

#### Scenario: Reprogramar un turno futuro (funcionamiento esperado)
- **DADO** el turno `scheduled` de la Dra. A y `now` el sábado 3 de octubre de 2026
- **CUANDO** se pregunta si se puede reprogramar
- **ENTONCES** el resultado es aceptado

#### Scenario: Reprogramar un turno cancelado (error de negocio)
- **DADO** un turno `cancelled` y `now` el sábado 3 de octubre de 2026
- **CUANDO** se pregunta si se puede reprogramar
- **ENTONCES** se rechaza con el motivo `CANCELLED_IS_FINAL`

#### Scenario: Reprogramar un turno ya iniciado (borde)
- **DADO** el turno `scheduled` de la Dra. A y `now` el lunes a las 10:00 locales
- **CUANDO** se pregunta si se puede reprogramar
- **ENTONCES** se rechaza con el motivo `ALREADY_STARTED`
