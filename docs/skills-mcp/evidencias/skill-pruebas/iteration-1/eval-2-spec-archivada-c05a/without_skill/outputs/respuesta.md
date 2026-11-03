# Revision de `openspec/specs/appointment-creation/spec.md` (C-05a) contra la KB

Veredicto: la spec esta bien armada y es fiel a RN-TU-01/02/03/12 y RN-HO-03 (resultado cerrado de 5 motivos, limites inclusivos/semiabiertos bien definidos, escenarios de borde utiles). No hay contradicciones con la KB. Tiene, sin embargo, algunas decisiones sin respaldo en la KB y varios bordes sin escenario. Ninguno es bloqueante para C-05a; los marcados (A) conviene cerrarlos antes de C-05b/C-07/C-08.

## 1. Decisiones de la spec que la KB no respalda (ambiguedades de la KB que la spec resolvio sola)

1. (A) Numeracion de weekday: la spec fija 0 = lunes. La KB (`04_modelo_de_datos.md`, `working_hours.weekday smallint (0-6)`) no dice cual es el dia 0. Hay que anotarlo en la KB (o un DD), porque el seed, la API y el frontend deben coincidir (Python `weekday()` vs. JS `getDay()` donde 0 = domingo).
2. (A) La grilla "se cuenta desde el inicio de cada tramo". RN-TU-02 solo dice "grilla de slots del horario del profesional". Es una decision razonable (escenario del Dr. B 09:15), pero no tiene DD asociado. Registrarla en `09_decisiones_y_supuestos.md`.
3. Orden fijo de evaluacion (anticipacion, grilla, horario, licencia, solapamiento): la KB no define precedencia. Es decision de la spec; deberia quedar como DD.
4. Solo `scheduled` bloquea. Coincide con el `WHERE status='scheduled'` del constraint, pero implica que `completed` y `no_show` liberan el horario. Es consistente con la KB, solo hay que saber que es intencional (hoy solo ocurre con turnos pasados, que igual caen por anticipacion).

## 2. Huecos respecto de la KB

1. Profesional inactivo (`professionals.active = false`): sin motivo de rechazo ni mencion de que queda fuera del alcance.
2. Paciente inactivo (RN-PA-04) y paciente inexistente: la spec dice "no se valida nada por paciente", pero RN-PA-04 es una regla de turnos nuevos. Falta declararla explicitamente fuera de C-05a (y a que change pasa), si no queda sin dueno.
3. Reprogramacion (RN-TU-06): al reprogramar, el turno que se mueve no debe contar como solapamiento consigo mismo. La spec no tiene parametro/escenario para excluir un turno propio. Ademas RN-TU-06 cita "RN-TU-01 a RN-TU-04" y no menciona RN-TU-12: la KB es ambigua sobre si reprogramar exige anticipacion minima.
4. Carrera/concurrencia (reglas duras 3 y 6): la spec valida en dominio, pero no menciona que una violacion del constraint de exclusion en la base debe traducirse al mismo motivo `OVERLAPS_EXISTING`. Es del change de persistencia, pero conviene dejarlo anotado.
5. RN-HO-04 (turnos existentes que quedan fuera de un horario modificado o en una licencia nueva): no afecta la creacion, pero la spec no aclara que esos turnos `scheduled` siguen bloqueando solapamiento.
6. Configuracion: `slot_minutes` es configurable (`clinic_settings`) pero ningun escenario usa un valor distinto de 30; solo `min_notice_hours` se prueba con valor no default.

## 3. Bordes sin escenario / ambiguedades de entrada

1. Instante sin zona horaria (datetime naive): RN-GL-01 manda UTC; la spec no dice si se rechaza, se asume UTC o se asume hora local.
2. Licencia vs. dia local en el borde de UTC: un turno a las 22:00 locales (01:00 UTC del dia siguiente) debe evaluarse contra el dia local. Hay escenario UTC -> local solo para el caso feliz, no para licencia ni dia de semana. Falta, por ejemplo, 23:30 local un dia con licencia / un dia sin horario.
3. Licencia: solo se prueba el ultimo dia. Faltan primer dia, dia anterior y posterior a la licencia (acepta), licencia de un solo dia (`starts_on = ends_on`) y licencia de otro profesional (el requisito lo dice pero no hay escenario).
4. Licencia en un dia sin horario de trabajo: con el orden fijado (horario antes que licencia) el motivo es `OUTSIDE_WORKING_HOURS`, no `PROFESSIONAL_TIME_OFF`. Es coherente con el orden, pero poco informativo para el usuario; vale un escenario que lo deje explicito (o replantear el orden).
5. Tramos contiguos (09:00-13:00 y 13:00-17:00, no prohibido por RN-HO-02): un turno 12:45-13:15 queda rechazado por "completo dentro de un tramo". Falta definirlo y probarlo.
6. Tramo cuya duracion no es multiplo de `slot_minutes` (ej. 09:00-13:15): el ultimo slot parcial se rechaza por `OUTSIDE_WORKING_HOURS`; no hay escenario.
7. Inicio con segundos/microsegundos (10:00:30) o inicio dentro de un tramo pero con fin que lo excede y ademas fuera de grilla: precedencia OFF_GRID vs OUTSIDE_WORKING_HOURS no probada. Tambien el caso de una hora fuera de todo tramo pero que "no cae en grilla" (la spec lo deriva a horario, pero sin escenario con inicio fuera de tramo y fuera de multiplo, p. ej. 08:10).
8. Solapamiento parcial: los escenarios solo cubren igual / justo antes / justo despues. Falta el parcial (existente 10:15-10:45 por un cambio previo de grilla o `slot_minutes`, nuevo 10:00-10:30), que es el unico tipo posible de solape real distinto del exacto y el que mas justifica el rango semiabierto.
9. Solapamiento con estados distintos de `cancelled` (`completed`, `no_show`): el requisito lo menciona pero solo hay escenario para `cancelled`.
10. Orden: solo hay dos escenarios de combinacion. Faltan pares como grilla+horario, horario+licencia y licencia/horario+solape para cubrir la cadena completa; tampoco "turno pasado en dia sin horario".
11. Hora local inexistente o ambigua por cambio de horario de verano: America/Argentina/Buenos_Aires hoy no tiene DST, pero `timezone` es configurable. Declararlo fuera de alcance o definirlo.
12. Valores raros de configuracion (`min_notice_hours = 0` o negativo, `slot_minutes <= 0`): sin definicion.
13. Escenarios "Anticipacion..." no fijan fecha completa (solo "lunes"); funcionan, pero para mantener la determinacion conviene usar fechas absolutas (como ya hacen los de UTC y licencia).

## 4. Conclusion

Spec solida y coherente con la KB. Acciones sugeridas: (1) pasar a la KB/DD las decisiones weekday 0 = lunes, grilla desde inicio de tramo y orden de evaluacion; (2) aclarar en la spec el alcance excluido (paciente/profesional inactivo, reprogramacion, mapeo del constraint de BD); (3) agregar escenarios para solape parcial, bordes de licencia, dia local vs UTC, tramos contiguos y `slot_minutes` distinto de 30 en el change que retome estas reglas (C-05b/C-05c).
