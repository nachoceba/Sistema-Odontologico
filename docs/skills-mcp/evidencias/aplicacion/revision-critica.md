# Revisión crítica: correcciones a la spec de C-05b por la skill `revisor-escenarios-turnos`

Fecha: 2026-11-03. Change: C-05b `calcular-slots-disponibles`, fase PROPOSE. Archivo corregido: `openspec/changes/calcular-slots-disponibles/specs/slot-availability/spec.md`. Salida completa de la skill: `skill-revisor-c05b-spec.md`.

La skill revisó el primer borrador completo (29 escenarios) y encontró 8 hallazgos. Tres eran defectos reales del borrador y se corrigieron en la spec (abajo, con el antes y el después). Los otros cinco no cambian la spec: dos quedan como decisión de diseño sin respaldo en la KB en `design.md`, dos como preguntas abiertas para el usuario y uno como supuesto declarado. Los cálculos (conteos de franjas y horas UTC) los recalculó la skill y estaban bien: no hubo errores numéricos.

## Corrección 1: la precedencia `OUTSIDE_HOURS` > `BUSY` estaba solo implícita y chocaba con RN-HO-04

- **Qué se detectó**: la spec ponía `OUTSIDE_HOURS` sobre franjas con un turno `scheduled` real (licencia cargada después, turno que cruza medianoche fuera de tramo) sin decirlo como regla general, y sin aclarar que así el cálculo de franjas no muestra el conflicto que RN-HO-04 pide marcar para recepción.
- **Fuente**: `RN-HO-04` en `knowledge-base/05_reglas_de_negocio.md` ("el sistema los marca como conflicto para que recepción los resuelva"); `US-004` en `06_funcionalidades.md` ("Si un cambio afecta turnos existentes, se listan para revisión"). La precedencia en sí: sin respaldo en la KB.
- **Antes** (único texto que la fijaba, dentro del requisito de ocupación):

  > Una franja dentro de un tramo y fuera de licencia MUST salir `BUSY` si se superpone con algún turno en estado `scheduled` del mismo profesional; si no, SHALL salir `FREE`.

  y, solo para la licencia: "todas las franjas del día MUST salir `OUTSIDE_HOURS`, aunque haya turnos `scheduled` cargados ese día". Nada para un turno fuera de tramo dentro de un día normal.
- **Después**: requisito nuevo "Precedencia de estados y conflictos (RN-HO-04)":

  > Cada franja SHALL recibir un único estado con esta precedencia: `OUTSIDE_HOURS` (fuera de todo tramo, resto parcial de un tramo o día de licencia) prevalece sobre `BUSY`, y `BUSY` prevalece sobre `FREE`. Un turno `scheduled` que cae fuera de tramo o en un día de licencia (…) MUST NOT cambiar el estado `OUTSIDE_HOURS` de esas franjas. El cálculo de franjas MUST NOT informar conflictos: detectar y listar los turnos afectados por un cambio de horario o una licencia corresponde a la gestión de horarios (C-07), y la vista de agenda (C-09) muestra los turnos con su propia consulta.

  con el escenario nuevo "Turno `scheduled` fuera de tramo dentro del mismo día" (turno 13:00-13:30 en el hueco entre tramos: la franja de las 13:00 es `OUTSIDE_HOURS`; 12:30 y 14:00 son `FREE`).

## Corrección 2: faltaba el borde de turnos consecutivos

- **Qué se detectó**: no había escenario de dos turnos `scheduled` seguidos del mismo profesional, que es como la KB resuelve los tratamientos largos y el borde del rango semiabierto visto desde dos turnos.
- **Fuente**: `RN-TU-10` (`05_reglas_de_negocio.md`: "Un tratamiento más largo que `slot_minutes` se agenda con turnos consecutivos") y `DD-03` (`09_decisiones_y_supuestos.md`).
- **Antes**: el requisito de ocupación terminaba en el escenario "Turno existente desalineado con la grilla".
- **Después**: escenario nuevo:

  > #### Scenario: Turnos consecutivos de un tratamiento largo (borde)
  > - **DADO** que la Dra. A tiene dos turnos `scheduled` el lunes, de 10:00 a 10:30 y de 10:30 a 11:00 (RN-TU-10, DD-03)
  > - **ENTONCES** las franjas de las 10:00 y de las 10:30 son `BUSY`
  > - **Y** las franjas de las 09:30 y de las 11:00 son `FREE`

## Corrección 3: un escenario rotulado "error de negocio" que no es un error

- **Qué se detectó**: el escenario de licencia decía "(error de negocio)", pero el cálculo no rechaza: devuelve franjas `OUTSIDE_HOURS`. El rótulo sugería que la función lanza o rechaza, en contra de la decisión 3 (licencia = `OUTSIDE_HOURS`).
- **Fuente**: `RN-HO-03` y `US-005` ("Los días de licencia no ofrecen slots"), `06_funcionalidades.md`.
- **Antes**:

  > #### Scenario: Día cubierto por una licencia (error de negocio)

  y el requisito de entradas inválidas empezaba directamente con "El sistema MUST lanzar `ValueError`…".
- **Después**:

  > #### Scenario: Día cubierto por una licencia (caso de negocio: día no disponible)

  y el requisito de entradas inválidas aclara: "El cálculo de franjas no tiene motivos de rechazo de negocio (un día no disponible se informa con franjas `OUTSIDE_HOURS`); sus únicos errores son de entrada."

## Hallazgos que no cambiaron la spec

| Hallazgo | Destino | Motivo |
|----------|---------|--------|
| 3: grilla fuera de tramos anclada a las 00:00 o al fin del tramo anterior, con recorte | `design.md`, decisión de diseño sin respaldo en la KB | Es necesaria para cumplir la decisión 2 (día completo, sin huecos ni solapes); la KB no la define |
| 4: una fecha y hora como día se rechaza con `ValueError` | `design.md`, decisión de diseño sin respaldo en la KB | Aplica la decisión 6; rechazarla evita ignorar una hora en silencio |
| 5: zona horaria inexistente | `design.md`, pregunta abierta para el usuario | Ninguna decisión la cubre; no se inventa comportamiento |
| 6: turnos existentes sin zona | `design.md`, pregunta abierta (precondición heredada de C-05a) | Ídem |
| 8: dependencia de SU-01 y de la duración real del slot | `design.md`, riesgos | Ya declarado como supuesto; no bloquea |

Resultado: la spec final tiene 31 escenarios (24 de `slot-availability` y 7 de `clinic-timezone`).
