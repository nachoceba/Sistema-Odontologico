# appointment-creation Specification

## Purpose
Decidir, sin pantalla ni base de datos, si se puede crear un turno para un profesional del consultorio, respetando anticipación mínima, grilla de slots, horario de trabajo, licencias y no solapamiento con otros turnos del mismo profesional, y explicar el motivo cuando no se puede.

## Requirements

### Requirement: Resultado de la validación de un turno nuevo

El sistema SHALL responder a cada pedido de crear un turno para un profesional con un resultado explícito, sin lanzar errores por motivos de negocio: **aceptado**, con la hora de fin igual a la hora de inicio más `slot_minutes`, o **rechazado**, con exactamente un motivo de esta lista cerrada: `INSUFFICIENT_NOTICE`, `OFF_GRID`, `OUTSIDE_WORKING_HOURS`, `PROFESSIONAL_TIME_OFF`, `OVERLAPS_EXISTING`. La validación MUST ser determinista: con los mismos datos de entrada (incluido el momento actual) devuelve siempre el mismo resultado.

#### Scenario: Turno libre dentro del horario (feliz)
- **DADO** que la Dra. A no tiene turnos el lunes
- **CUANDO** se pide crear un turno para la Dra. A el lunes a las 10:00
- **ENTONCES** el resultado es aceptado y el turno termina el lunes a las 10:30

#### Scenario: El instante en UTC se interpreta en la hora local del consultorio
- **DADO** que la Dra. A no tiene turnos el lunes
- **CUANDO** se pide crear un turno con inicio el lunes 5 de octubre de 2026 a las 13:00 UTC (10:00 local)
- **ENTONCES** el resultado es aceptado y el turno termina a las 13:30 UTC (10:30 local)

### Requirement: Anticipación mínima (RN-TU-12)

El sistema MUST rechazar con `INSUFFICIENT_NOTICE` todo turno cuyo inicio sea anterior a `now + min_notice_hours`. Un inicio exactamente igual a `now + min_notice_hours` SHALL aceptarse (límite inclusivo). La anticipación mínima es configurable y vale 6 horas por defecto. Un turno con inicio en el pasado queda rechazado por esta misma regla (RN-TU-04).

#### Scenario: Anticipación insuficiente
- **DADO** que el momento actual es el lunes a las 05:00
- **CUANDO** se pide crear un turno para la Dra. A el lunes a las 10:00 (faltan 5 horas)
- **ENTONCES** el resultado es rechazado con motivo `INSUFFICIENT_NOTICE`

#### Scenario: Anticipación exacta de 6 horas (borde inclusivo)
- **DADO** que el momento actual es el lunes a las 04:00
- **CUANDO** se pide crear un turno para la Dra. A el lunes a las 10:00 (faltan exactamente 6 horas)
- **ENTONCES** el resultado es aceptado y el turno termina a las 10:30

#### Scenario: Turno en el pasado
- **DADO** que el momento actual es el lunes a las 11:00
- **CUANDO** se pide crear un turno para la Dra. A el lunes a las 10:00
- **ENTONCES** el resultado es rechazado con motivo `INSUFFICIENT_NOTICE`

#### Scenario: Anticipación configurada en 12 horas
- **DADO** que el momento actual es el domingo 4 de octubre a las 23:00 y la anticipación mínima es 12 horas
- **CUANDO** se pide crear un turno para la Dra. A el lunes a las 10:00 (faltan 11 horas)
- **ENTONCES** el resultado es rechazado con motivo `INSUFFICIENT_NOTICE`

### Requirement: Inicio dentro de la grilla de slots (RN-TU-02)

El sistema MUST rechazar con `OFF_GRID` todo turno cuyo inicio no caiga en la grilla de slots del profesional. La grilla SHALL contarse desde el inicio de cada tramo de horario del profesional, en pasos de `slot_minutes`. Un inicio que no coincide con ningún tramo del día no es un problema de grilla: se resuelve por la regla de horario de trabajo.

#### Scenario: Inicio fuera de la grilla
- **DADO** que la Dra. A atiende el lunes de 09:00 a 13:00
- **CUANDO** se pide crear un turno para la Dra. A el lunes a las 10:10
- **ENTONCES** el resultado es rechazado con motivo `OFF_GRID`

#### Scenario: La grilla se cuenta desde el inicio del tramo
- **DADO** que el Dr. B atiende el lunes de 09:15 a 13:15
- **CUANDO** se pide crear un turno para el Dr. B el lunes a las 09:45
- **ENTONCES** el resultado es aceptado y el turno termina a las 10:15

### Requirement: Turno completo dentro del horario de trabajo (RN-TU-03)

El sistema MUST rechazar con `OUTSIDE_WORKING_HOURS` todo turno que no quede completo (inicio y fin) dentro de un tramo de horario de trabajo del profesional para ese día de la semana local. Los días de la semana se numeran de 0 (lunes) a 6 (domingo). Un turno que termina exactamente cuando termina el tramo SHALL aceptarse.

#### Scenario: Antes del inicio del horario
- **DADO** que la Dra. A atiende el lunes desde las 09:00
- **CUANDO** se pide crear un turno para la Dra. A el lunes a las 08:30
- **ENTONCES** el resultado es rechazado con motivo `OUTSIDE_WORKING_HOURS`

#### Scenario: En el hueco entre dos tramos
- **DADO** que la Dra. A atiende el lunes de 09:00 a 13:00 y de 14:00 a 18:00
- **CUANDO** se pide crear un turno para la Dra. A el lunes a las 13:00
- **ENTONCES** el resultado es rechazado con motivo `OUTSIDE_WORKING_HOURS`

#### Scenario: Último slot del tramo (borde)
- **DADO** que la Dra. A atiende el lunes de 09:00 a 13:00
- **CUANDO** se pide crear un turno para la Dra. A el lunes a las 12:30
- **ENTONCES** el resultado es aceptado y el turno termina a las 13:00

#### Scenario: Día sin horario de trabajo
- **DADO** que la Dra. A no tiene horario los martes (día 1)
- **CUANDO** se pide crear un turno para la Dra. A el martes 6 de octubre de 2026 a las 10:00
- **ENTONCES** el resultado es rechazado con motivo `OUTSIDE_WORKING_HOURS`

### Requirement: Fuera de las licencias del profesional (RN-TU-03, RN-HO-03)

El sistema MUST rechazar con `PROFESSIONAL_TIME_OFF` todo turno cuyo día local caiga dentro de una licencia del profesional. Las licencias son por días completos y SHALL incluir tanto el día de inicio como el día de fin. Las licencias de otros profesionales no afectan la validación.

#### Scenario: Turno en el último día de una licencia
- **DADO** que la Dra. A tiene licencia del jueves 1 al lunes 5 de octubre de 2026, ambos inclusive
- **CUANDO** se pide crear un turno para la Dra. A el lunes a las 10:00
- **ENTONCES** el resultado es rechazado con motivo `PROFESSIONAL_TIME_OFF`

### Requirement: Sin solapamiento con turnos del mismo profesional (RN-TU-01)

El sistema MUST rechazar con `OVERLAPS_EXISTING` todo turno que se superponga con un turno en estado `scheduled` del mismo profesional. Los turnos se tratan como rangos semiabiertos [inicio, fin): dos turnos se superponen solo si cada uno empieza antes de que termine el otro. Los turnos en estado `cancelled` (y cualquier otro estado distinto de `scheduled`) SHALL ignorarse. Los turnos de otros profesionales SHALL ignorarse: dos profesionales distintos pueden atender a la misma hora. No se valida nada por paciente.

#### Scenario: Pisa a otro turno del mismo profesional (error de negocio)
- **DADO** que la Dra. A tiene un turno `scheduled` el lunes de 10:00 a 10:30
- **CUANDO** se pide crear otro turno para la Dra. A el lunes a las 10:00
- **ENTONCES** el resultado es rechazado con motivo `OVERLAPS_EXISTING`

#### Scenario: Empieza justo cuando termina otro (borde)
- **DADO** que la Dra. A tiene un turno `scheduled` el lunes de 10:00 a 10:30
- **CUANDO** se pide crear un turno para la Dra. A el lunes a las 10:30
- **ENTONCES** el resultado es aceptado y el turno termina a las 11:00

#### Scenario: Termina justo cuando empieza otro (borde)
- **DADO** que la Dra. A tiene un turno `scheduled` el lunes de 10:00 a 10:30
- **CUANDO** se pide crear un turno para la Dra. A el lunes a las 09:30
- **ENTONCES** el resultado es aceptado y el turno termina a las 10:00

#### Scenario: Mismo horario con otro profesional
- **DADO** que la Dra. A tiene un turno `scheduled` el lunes de 10:00 a 10:30
- **CUANDO** se pide crear un turno para el Dr. B el lunes a las 10:00
- **ENTONCES** el resultado es aceptado y el turno termina a las 10:30

#### Scenario: Un turno cancelado no ocupa el horario
- **DADO** que la Dra. A tiene un turno `cancelled` el lunes de 10:00 a 10:30
- **CUANDO** se pide crear un turno para la Dra. A el lunes a las 10:00
- **ENTONCES** el resultado es aceptado y el turno termina a las 10:30

### Requirement: Un solo motivo con orden fijo de evaluación

Cuando un turno incumple varias reglas a la vez, el sistema SHALL devolver un único motivo: el de la primera regla incumplida según este orden fijo: (1) anticipación mínima, (2) grilla, (3) horario de trabajo, (4) licencia, (5) solapamiento.

#### Scenario: Anticipación insuficiente y fuera de la grilla
- **DADO** que el momento actual es el lunes a las 08:00
- **CUANDO** se pide crear un turno para la Dra. A el lunes a las 10:10
- **ENTONCES** el resultado es rechazado con motivo `INSUFFICIENT_NOTICE`

#### Scenario: Licencia y solapamiento a la vez
- **DADO** que la Dra. A tiene licencia el lunes y además un turno `scheduled` el lunes de 10:00 a 10:30 (cargado antes de la licencia)
- **CUANDO** se pide crear un turno para la Dra. A el lunes a las 10:00
- **ENTONCES** el resultado es rechazado con motivo `PROFESSIONAL_TIME_OFF`
