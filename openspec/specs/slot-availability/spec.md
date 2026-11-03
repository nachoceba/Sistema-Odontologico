# slot-availability Specification

## Purpose
Calcular, sin pantalla ni base de datos, cómo está cada franja del día local de un profesional del consultorio (libre, ocupada o fuera de horario) a partir de sus tramos de horario, sus licencias y los turnos existentes, de forma coherente con la validación de un turno nuevo (`appointment-creation`).

## Requirements

> Datos comunes de los escenarios (salvo que el escenario diga otra cosa): zona del consultorio `America/Argentina/Buenos_Aires` (UTC-3, sin horario de verano, supuesto SU-01); `slot_minutes = 30`; la Dra. A (profesional ficticia `dra-a`) atiende los lunes de 09:00 a 13:00 y de 14:00 a 18:00 (hora local) y no atiende otros días; "el lunes" es el lunes 5 de octubre de 2026 (local), que en UTC va del 5 de octubre a las 03:00 al 6 de octubre a las 03:00. Las horas sin aclaración son locales. Todos los datos son ficticios.

### Requirement: Franjas del día local completo, ordenadas y en UTC

El sistema SHALL devolver, para un profesional y un día local, la lista de franjas que cubre el día local completo (de las 00:00 a las 24:00 locales), en orden cronológico ascendente, contiguas, sin huecos ni solapes. Cada franja MUST tener inicio y fin como instantes UTC con zona y exactamente uno de estos tres estados: `FREE` (libre), `BUSY` (ocupada) u `OUTSIDE_HOURS` (fuera de horario). No existe un cuarto estado. El cálculo MUST ser determinista: con los mismos datos devuelve siempre la misma lista.

La grilla de franjas se arma así: dentro de cada tramo de horario, franjas de `slot_minutes` contadas desde el inicio del tramo (RN-TU-02); fuera de los tramos, franjas de `slot_minutes` contadas desde las 00:00 locales o desde el fin del tramo anterior, recortadas al llegar al inicio del tramo siguiente o al fin del día. Solo las franjas de estado `OUTSIDE_HOURS` pueden durar menos de `slot_minutes`; toda franja `FREE` o `BUSY` dura exactamente `slot_minutes`.

#### Scenario: Lunes sin turnos (funcionamiento esperado)
- **DADO** que la Dra. A no tiene turnos ni licencias
- **CUANDO** se calculan las franjas de la Dra. A para el lunes
- **ENTONCES** se devuelven 48 franjas de 30 minutos, de las 00:00 a las 24:00 locales
- **Y** las 8 franjas que empiezan de 09:00 a 12:30 y las 8 que empiezan de 14:00 a 17:30 son `FREE` (16 en total)
- **Y** las 18 franjas de 00:00 a 09:00, las 2 de 13:00 a 14:00 y las 12 de 18:00 a 24:00 son `OUTSIDE_HOURS` (32 en total)
- **Y** ninguna franja es `BUSY` (RN-TU-02, RN-TU-03)

#### Scenario: Inicio y fin de cada franja en UTC
- **DADO** que la Dra. A no tiene turnos ni licencias
- **CUANDO** se calculan las franjas de la Dra. A para el lunes
- **ENTONCES** la primera franja va del 5 de octubre de 2026 a las 03:00 UTC a las 03:30 UTC, la franja de las 09:00 locales va de las 12:00 UTC a las 12:30 UTC, y la última termina el 6 de octubre de 2026 a las 03:00 UTC
- **Y** el inicio y el fin de todas las franjas tienen desplazamiento UTC igual a cero (RN-GL-01)

### Requirement: Grilla anclada al tramo y franja que no entra completa (RN-TU-02, RN-TU-03)

Dentro de un tramo, la grilla SHALL contarse desde el inicio del tramo en pasos de `slot_minutes`. Una franja que empieza dentro de un tramo pero no termina dentro de él MUST salir `OUTSIDE_HOURS`, recortada al fin del tramo. Una franja que termina exactamente cuando termina el tramo SHALL poder ser `FREE`.

#### Scenario: Tramo que no es múltiplo del slot (borde)
- **DADO** que la Dra. A atiende el lunes solo de 14:00 a 15:45
- **CUANDO** se calculan sus franjas para el lunes
- **ENTONCES** las franjas de las 14:00, 14:30 y 15:00 son `FREE`
- **Y** la franja que empieza a las 15:30 es `OUTSIDE_HOURS` y termina a las 15:45
- **Y** la franja siguiente empieza a las 15:45 y es `OUTSIDE_HOURS`

#### Scenario: La grilla se cuenta desde el inicio del tramo
- **DADO** que el Dr. B (profesional ficticio `dr-b`) atiende el lunes de 09:15 a 13:15 y no tiene turnos
- **CUANDO** se calculan sus franjas para el lunes
- **ENTONCES** la franja de las 09:00 es `OUTSIDE_HOURS` y termina a las 09:15
- **Y** hay 8 franjas `FREE` que empiezan a las 09:15, 09:45, …, 12:45, y la última termina a las 13:15

#### Scenario: Slot de 45 minutos
- **DADO** que `slot_minutes` es 45 y la Dra. A atiende el lunes solo de 09:00 a 13:00
- **CUANDO** se calculan sus franjas para el lunes
- **ENTONCES** son `FREE` las franjas de las 09:00, 09:45, 10:30, 11:15 y 12:00 (la última termina a las 12:45)
- **Y** la franja de las 12:45 es `OUTSIDE_HOURS` y termina a las 13:00

#### Scenario: Tramos contiguos con anclas distintas
- **DADO** que la Dra. A atiende el lunes de 09:00 a 13:15 y de 13:15 a 17:00
- **CUANDO** se calculan sus franjas para el lunes
- **ENTONCES** la franja de las 12:30 es `FREE` y termina a las 13:00
- **Y** la franja de las 13:00 es `OUTSIDE_HOURS` y termina a las 13:15
- **Y** la franja de las 13:15 es `FREE` y termina a las 13:45

### Requirement: Ocupación por turnos `scheduled` del mismo profesional (RN-TU-01, RN-TU-05, RN-TU-09)

Una franja dentro de un tramo y fuera de licencia MUST salir `BUSY` si se superpone con algún turno en estado `scheduled` del mismo profesional; si no, SHALL salir `FREE`. Los turnos y las franjas se tratan como rangos semiabiertos [inicio, fin): tocarse en el borde no es superponerse. Los turnos en cualquier otro estado (`cancelled`, `completed`, `no_show`) y los turnos de otros profesionales SHALL ignorarse. Un turno que se superpone con varias franjas las marca `BUSY` a todas.

#### Scenario: Turno ocupado y turnos pegados (borde)
- **DADO** que la Dra. A tiene un turno `scheduled` el lunes de 10:00 a 10:30
- **CUANDO** se calculan sus franjas para el lunes
- **ENTONCES** la franja de las 10:00 es `BUSY`
- **Y** las franjas de las 09:30 y de las 10:30 son `FREE`

#### Scenario: Un turno cancelado libera la franja
- **DADO** que la Dra. A tiene un turno `cancelled` el lunes de 10:00 a 10:30
- **CUANDO** se calculan sus franjas para el lunes
- **ENTONCES** la franja de las 10:00 es `FREE` (RN-TU-05)

#### Scenario: Turnos `completed` o `no_show` no ocupan
- **DADO** que la Dra. A tiene un turno `completed` el lunes de 10:00 a 10:30 y otro `no_show` de 11:00 a 11:30
- **CUANDO** se calculan sus franjas para el lunes
- **ENTONCES** las franjas de las 10:00 y de las 11:00 son `FREE`

#### Scenario: El turno de otro profesional no ocupa
- **DADO** que el Dr. B tiene un turno `scheduled` el lunes de 10:00 a 10:30 y la Dra. A no tiene turnos
- **CUANDO** se calculan las franjas de la Dra. A para el lunes
- **ENTONCES** la franja de las 10:00 de la Dra. A es `FREE` (RN-TU-09)

#### Scenario: Turno existente desalineado con la grilla
- **DADO** que la Dra. A tiene un turno `scheduled` el lunes de 10:15 a 10:45
- **CUANDO** se calculan sus franjas para el lunes
- **ENTONCES** las franjas de las 10:00 y de las 10:30 son `BUSY`
- **Y** las franjas de las 09:30 y de las 11:00 son `FREE`

#### Scenario: Turnos consecutivos de un tratamiento largo (borde)
- **DADO** que la Dra. A tiene dos turnos `scheduled` el lunes, de 10:00 a 10:30 y de 10:30 a 11:00 (RN-TU-10, DD-03)
- **CUANDO** se calculan sus franjas para el lunes
- **ENTONCES** las franjas de las 10:00 y de las 10:30 son `BUSY`
- **Y** las franjas de las 09:30 y de las 11:00 son `FREE`

### Requirement: Precedencia de estados y conflictos (RN-HO-04)

Cada franja SHALL recibir un único estado con esta precedencia: `OUTSIDE_HOURS` (fuera de todo tramo, resto parcial de un tramo o día de licencia) prevalece sobre `BUSY`, y `BUSY` prevalece sobre `FREE`. Un turno `scheduled` que cae fuera de tramo o en un día de licencia (por ejemplo, porque cambió el horario o se cargó la licencia después, RN-HO-04) MUST NOT cambiar el estado `OUTSIDE_HOURS` de esas franjas. El cálculo de franjas MUST NOT informar conflictos: detectar y listar los turnos afectados por un cambio de horario o una licencia corresponde a la gestión de horarios (C-07), y la vista de agenda (C-09) muestra los turnos con su propia consulta.

#### Scenario: Turno `scheduled` fuera de tramo dentro del mismo día
- **DADO** que la Dra. A tiene un turno `scheduled` el lunes de 13:00 a 13:30 (en el hueco entre sus dos tramos, por ejemplo porque su horario cambió después de agendarlo)
- **CUANDO** se calculan sus franjas para el lunes
- **ENTONCES** la franja de las 13:00 es `OUTSIDE_HOURS`
- **Y** las franjas de las 12:30 y de las 14:00 son `FREE`

### Requirement: Licencias del profesional (RN-HO-03, RN-TU-03)

Si el día local pedido cae dentro de una licencia del profesional (días completos, inicio y fin inclusivos), todas las franjas del día MUST salir `OUTSIDE_HOURS`, aunque haya turnos `scheduled` cargados ese día. Las licencias no agregan un estado propio.

#### Scenario: Día cubierto por una licencia (caso de negocio: día no disponible)
- **DADO** que la Dra. A tiene licencia del jueves 1 al lunes 5 de octubre de 2026, ambos inclusive
- **CUANDO** se calculan sus franjas para el lunes
- **ENTONCES** las 48 franjas son `OUTSIDE_HOURS` y ninguna es `FREE`

#### Scenario: Licencia de un solo día y día siguiente
- **DADO** que la Dra. A tiene licencia solo el lunes 5 de octubre de 2026 (inicio y fin el mismo día)
- **CUANDO** se calculan sus franjas para el lunes y para el lunes 12 de octubre de 2026
- **ENTONCES** el lunes 5 no tiene ninguna franja `FREE`
- **Y** el lunes 12 tiene 16 franjas `FREE`

#### Scenario: La licencia prevalece sobre un turno ya cargado
- **DADO** que la Dra. A tiene licencia el lunes y además un turno `scheduled` el lunes de 10:00 a 10:30 (cargado antes de la licencia, RN-HO-04)
- **CUANDO** se calculan sus franjas para el lunes
- **ENTONCES** la franja de las 10:00 es `OUTSIDE_HOURS`

### Requirement: Día sin horario de trabajo

Un día local cuyo día de la semana no tiene tramos para el profesional MUST devolver el día completo con todas sus franjas `OUTSIDE_HOURS` (no una lista vacía).

#### Scenario: Martes sin tramos (borde)
- **DADO** que la Dra. A no atiende los martes
- **CUANDO** se calculan sus franjas para el martes 6 de octubre de 2026
- **ENTONCES** se devuelven 48 franjas, todas `OUTSIDE_HOURS`

### Requirement: Día local según la zona del consultorio (RN-GL-01, RN-TU-01)

El día pedido SHALL interpretarse como fecha local de la zona del consultorio. Un turno existente MUST contar en una franja si se superpone con ella como instantes, aunque su fecha en UTC sea otra; un turno que cruza la medianoche local cuenta en cada franja que toca de cada día.

#### Scenario: Turno del lunes local que en UTC cae el martes
- **DADO** que el Dr. C (profesional ficticio `dr-c`) atiende el lunes de 18:00 a 22:00
- **Y** tiene un turno `scheduled` del martes 6 de octubre de 2026 de 00:00 a 00:30 UTC (lunes de 21:00 a 21:30 local)
- **CUANDO** se calculan sus franjas para el lunes
- **ENTONCES** la franja de las 21:00 locales es `BUSY` y la de las 20:30 es `FREE`

#### Scenario: Turno del martes a las 00:00 locales no pertenece al lunes
- **DADO** que el Dr. C tiene un turno `scheduled` del martes 6 de octubre de 2026 de 03:00 a 03:30 UTC (martes 00:00 local)
- **CUANDO** se calculan sus franjas para el lunes
- **ENTONCES** ninguna franja del lunes es `BUSY`
- **Y** la última franja del lunes termina el martes a las 03:00 UTC

#### Scenario: Turno que cruza la medianoche local
- **DADO** que el Dr. D (profesional ficticio `dr-d`) atiende los martes de 00:00 a 02:00
- **Y** tiene un turno `scheduled` del lunes a las 23:45 al martes 6 de octubre a las 00:15 (hora local)
- **CUANDO** se calculan sus franjas para el martes 6 de octubre de 2026
- **ENTONCES** la franja de las 00:00 es `BUSY` y la de las 00:30 es `FREE`
- **Y** en las franjas del lunes, la franja de las 23:30 es `OUTSIDE_HOURS` (el lunes no tiene tramo a esa hora)

### Requirement: Sin anticipación mínima en el cálculo (RN-TU-12, DD-14)

El cálculo de franjas MUST NOT depender del momento actual: no recibe la hora actual ni aplica la anticipación mínima. Una franja puede salir `FREE` aunque la validación de un turno nuevo la rechace con `INSUFFICIENT_NOTICE`; esa regla la sigue resolviendo la validación (`appointment-creation`).

#### Scenario: Franja libre aunque falten menos de 6 horas
- **DADO** que la Dra. A no tiene turnos y el momento actual es el lunes a las 08:00
- **CUANDO** se calculan sus franjas para el lunes
- **ENTONCES** la franja de las 10:00 es `FREE`
- **Y** la validación de un turno nuevo para la Dra. A el lunes a las 10:00 con ese momento actual lo rechaza con `INSUFFICIENT_NOTICE`

### Requirement: Entradas inválidas

El cálculo de franjas no tiene motivos de rechazo de negocio (un día no disponible se informa con franjas `OUTSIDE_HOURS`); sus únicos errores son de entrada. El sistema MUST lanzar `ValueError` (error de programación, no motivo de negocio) si `slot_minutes` es menor o igual que cero o si el día pedido no es una fecha de calendario. Un valor con hora (fecha y hora) no es un día válido y MUST rechazarse igual.

#### Scenario: Duración de slot no positiva (error de entrada)
- **DADO** los datos comunes
- **CUANDO** se calculan las franjas del lunes con `slot_minutes = 0` o con `slot_minutes = -30`
- **ENTONCES** se lanza `ValueError` y no se devuelve ninguna lista

#### Scenario: Día que no es una fecha
- **DADO** los datos comunes
- **CUANDO** se calculan las franjas pasando como día el texto `"2026-10-05"` o la fecha y hora `2026-10-05 10:00`
- **ENTONCES** se lanza `ValueError`

### Requirement: Coherencia con la validación de un turno nuevo

Toda franja `FREE` MUST ser aceptada por la validación de un turno nuevo (`appointment-creation`) cuando se le pasan el mismo profesional, los mismos tramos, licencias, turnos, `slot_minutes` y zona, con un momento actual suficientemente anterior para que no aplique la anticipación mínima.

#### Scenario: Toda franja libre es aceptada al validar
- **DADO** que la Dra. A tiene un turno `scheduled` el lunes de 10:15 a 10:45 y otro `cancelled` de 15:00 a 15:30
- **Y** el momento actual es el sábado 3 de octubre de 2026 a las 10:00
- **CUANDO** se calculan sus franjas para el lunes y se valida un turno nuevo en el inicio de cada franja `FREE`
- **ENTONCES** las 14 validaciones dan aceptado y cada turno termina en el fin de su franja
