# Evidencia: aplicación de la skill `revisor-escenarios-turnos` al explore de C-05b

Fecha: 2026-11-03. Change: C-05b `calcular-slots-disponibles` (fase explore).

## Cómo se usó

La skill se invocó **como skill**, con la herramienta Skill (`skill: "revisor-escenarios-turnos"`). Cargó sus instrucciones y se siguieron al pie de la letra: el agente leyó las reglas de la KB en el momento (05, 10, 09, 04, `CHANGES.md` y la spec `appointment-creation`) y respondió con el formato obligatorio. La skill no ejecuta código propio: lo que produce es la revisión que sigue.

## Solicitud realizada (argumentos)

Propuesta de firma: `compute_slots(*, professional_id, day, working_hours, time_off, existing_appointments, slot_minutes=30, timezone=BA)` que devuelve franjas ordenadas con estado FREE / BUSY / OUTSIDE_HOURS (instantes UTC). Zona Buenos Aires, slot 30, Dra. A atiende lunes 09:00-13:00 y 14:00-18:00; lunes 5/10/2026. Escenarios del borrador:

- E1 (esperado) lunes sin turnos: 8 franjas FREE de 09:00 a 13:00 y 8 de 14:00 a 18:00; el hueco 13:00-14:00 figura OUTSIDE_HOURS.
- E2 (esperado) turno scheduled 10:00-10:30: franja 10:00 BUSY, vecinas 09:30 y 10:30 FREE.
- E3 (esperado) turno cancelled 10:00-10:30: la franja 10:00 queda FREE.
- E4 (esperado) turno scheduled de otro profesional a las 10:00: la franja de la Dra. A queda FREE.
- E5 (negocio) licencia que cubre el lunes: todas las franjas OUTSIDE_HOURS (o estado propio?).
- E6 (entrada) slot_minutes <= 0 o day que no es date: ValueError.
- E7 (borde) tramo 09:00-13:15 con slot 30: la franja 13:00-13:30 no se ofrece como FREE.
- E8 (borde) tramo que arranca 09:15: grilla 09:15, 09:45...
- E9 (borde) día sin tramos (domingo): lista vacía o día entero OUTSIDE_HOURS?
- E10 (borde zona horaria) el lunes local va de 03:00 UTC del lunes a 03:00 UTC del martes.
- E11 (borde) turno desalineado 10:15-10:45: BUSY las franjas 10:00 y 10:30.
- E12 (borde) turno pasado o con menos de 6 h de anticipación: FREE u OUTSIDE_HOURS?
- E13 licencia de varios días (viernes a martes) con el lunes adentro.
- E14 consistencia: toda franja FREE debe ser aceptada por `validate_appointment` (salvo anticipación).

## Salida completa de la skill

### Resumen
14 escenarios revisados, 12 hallazgos (2 ambigüedades, 4 bordes faltantes, 1 regla solapada, 1 pregunta abierta, 2 sin respaldo, 2 contrato incompleto, 0 contradicciones).

### Hallazgos
| # | Tipo | Escenario afectado | Qué pasa | Respaldo en la KB | Sugerencia (a confirmar) |
|---|------|--------------------|----------|-------------------|--------------------------|
| 1 | Contrato incompleto | E1 a E14 | La firma de `CHANGES.md` C-05 no trae `timezone` (hace falta para pasar el día local a UTC) ni `professional_id` (E4). Tampoco define el tipo de salida. | RN-GL-01, RN-TU-09; `CHANGES.md` C-05 | Agregar `timezone` y `professional_id` como en `validate_appointment`; tipo `Slot` con UTC y estado. |
| 2 | Ambigüedad | E1, E9 | No está dicho qué franjas se devuelven: día completo, rango entre primer y último tramo, o solo franjas dentro de tramos. | US-006 (`06_funcionalidades.md`); sin respaldo en la KB sobre el rango | Devolver el día local completo en pasos de `slot_minutes`. |
| 3 | Decisión sin respaldo | E5, E13 | Un cuarto estado `TIME_OFF` no figura en ninguna RN; la KB y C-09 nombran tres estados. | RN-HO-03; C-09 en `CHANGES.md`; sin respaldo para un cuarto estado | Tres estados; licencia como `OUTSIDE_HOURS`. |
| 4 | Contrato incompleto | E12, E14 | `compute_slots` no recibe `now`; RN-TU-12 exige anticipación mínima. | RN-TU-12, DD-14; C-05a | Que la anticipación la rechace `validate_appointment`; o pasar `now` opcional. |
| 5 | Borde faltante | E2, E3 | Falta `completed` y `no_show`: ocupan la franja? El constraint solo excluye `scheduled`. | RN-TU-01, RN-TU-05; constraint en `04_modelo_de_datos.md`; sin respaldo para slots | Seguir C-05a: solo `scheduled` ocupa; agregar escenario. |
| 6 | Borde faltante | E8 | Falta el caso de dos tramos contiguos con anclas distintas. | RN-TU-02, RN-HO-02 | Agregar escenario de tramos pegados. |
| 7 | Ambigüedad | E7 | La franja 13:00-13:30 no entra en el tramo: se omite o es `OUTSIDE_HOURS`? | RN-TU-03; sin respaldo para la representación | Informarla como `OUTSIDE_HOURS` (consistente con #2). |
| 8 | Decisión sin respaldo | E6 | `ValueError` para `slot_minutes <= 0` o `day` inválido no está en ninguna RN; solo hay precedente en C-05a. | Spec `appointment-creation`; sin respaldo para `slot_minutes <= 0` | Mantener la convención de error de programación. |
| 9 | Pregunta abierta | E10 | La conversión de día local a UTC depende de la zona (SU-01, sin confirmar) y del slot real. | SU-01; preguntas de zona horaria y duración de slot en `10_preguntas_abiertas.md` | Declarar zona sin DST como supuesto. |
| 10 | Regla solapada | E14 | "Salvo anticipación" sin citar la regla; RN-TU-04 quedó reemplazada por RN-TU-12. | RN-TU-04, RN-TU-12; DD-14 | Citar RN-TU-12. |
| 11 | Borde faltante | E5, E13 | Falta la licencia de un solo día y sus días vecinos. | RN-HO-03; CHECK `starts_on <= ends_on` | Agregar escenario. |
| 12 | Borde faltante | E1, E8 | Falta slot que no divide el tramo (45) y fijar `weekday` 0 = lunes (`04_modelo_de_datos.md` solo dice 0-6). | RN-TU-02; `weekday` en `04_modelo_de_datos.md` | Escenario con slot 45 y mención de 0 = lunes. |

### Escenarios sin hallazgos
E2 (aparte de #5), E3, E4 (resuelto #1), E10 (aparte de #9), E11, E13 (aparte de #11).

### Decisiones que necesitan al usuario
1. ¿`compute_slots` recibe `timezone` y `professional_id`, y qué tipo devuelve? (#1)
2. ¿La grilla cubre el día local completo o solo los tramos? ¿Qué devuelve un día sin tramos? (#2, #7)
3. ¿La licencia se informa como `OUTSIDE_HOURS` o con estado propio? (#3)
4. ¿La anticipación mínima se aplica en `compute_slots` (con `now`) o solo en `validate_appointment`? (#4, #10)
5. ¿Solo los turnos `scheduled` ocupan una franja? (#5)
6. ¿Qué error se lanza con `slot_minutes <= 0` o un `day` inválido? (#8)
7. ¿Se declara la zona sin horario de verano como supuesto (SU-01)? (#9)

## Qué aportó al change

Las 7 decisiones de arriba se trasladaron a la lista de decisiones abiertas de `docs/opsx/explore-calcular-slots-disponibles.md`. Los escenarios E5 a E13 se reescribieron con los bordes que la revisión señaló. Ningún hallazgo se tomó como hecho: todos quedan como "decisión del usuario".
