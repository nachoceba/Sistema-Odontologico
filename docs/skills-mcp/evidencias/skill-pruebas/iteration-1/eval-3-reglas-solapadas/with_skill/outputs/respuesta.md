## Revisión de escenarios: futura spec de agenda (anticipación, estados y turnos del paciente)

### Resumen
4 escenarios revisados, 7 hallazgos (1 ambigüedad, 2 bordes faltantes, 2 reglas solapadas, 1 pregunta abierta, 1 sin respaldo).

Escenarios listados:
1. Rechazar un turno con inicio en el pasado (cita RN-TU-04) -> rechazo.
2. Aceptar un turno que empieza dentro de 5 horas -> aceptado (según el escenario).
3. Un turno `cancelled` pasa a `completed` -> permitido (según el escenario).
4. Dos turnos del mismo paciente el mismo día con distintos profesionales -> aceptados.

### Hallazgos
| # | Tipo | Escenario afectado | Qué pasa | Respaldo en la KB | Sugerencia (a confirmar) |
|---|------|--------------------|----------|-------------------|--------------------------|
| 1 | Regla solapada/reemplazada | 1 | El escenario cita RN-TU-04, pero esa regla dice que "queda cubierto por RN-TU-12" y que RN-TU-12 la reemplaza en la práctica (DD-14). Citar la equivocada deja el escenario atado a una regla vacía. | `RN-TU-04`, `RN-TU-12`, `05_reglas_de_negocio.md`; `DD-14`, `09_decisiones_y_supuestos.md` | Citar RN-TU-12 como regla gobernante y RN-TU-04 solo como caso particular (decisión a confirmar). |
| 2 | Borde faltante | 1 | Un inicio en el pasado es un caso muy lejano al límite. Falta el escenario de borde de RN-TU-12: inicio exactamente igual a `now + min_notice_hours` (se acepta) y un instante antes (se rechaza). | `RN-TU-12`, `05_reglas_de_negocio.md` | Agregar ambos escenarios de límite exacto (el aceptado y el rechazado por un minuto). |
| 3 | Regla solapada/reemplazada | 2 | Con `min_notice_hours` = 6 por defecto, un turno que empieza en 5 horas se RECHAZA, no se acepta. El escenario contradice RN-TU-12. | `RN-TU-12`, `05_reglas_de_negocio.md`; `DD-14` | Invertir el resultado: debe rechazarse (error de negocio). Si se quiere aceptar, tendría que cambiarse la configuración, no la regla. |
| 4 | Sin respaldo / pregunta abierta | 2 | Aun si el consultorio configurara otro valor, el escenario no declara el valor de `min_notice_hours` de partida. Además, queda abierta la excepción urgente del mismo día: el escenario podría estar presuponiendo que existe. | `min_notice_hours` en `04_modelo_de_datos.md` (default 6); pregunta abierta de emergencia en `10_preguntas_abiertas.md` (RN-TU-12, DD-14, prioridad Media) | Fijar el valor en el escenario (6 por defecto) y no asumir ninguna excepción de emergencia hasta que se responda la pregunta. |
| 5 | Ambigüedad | 3 | RN-TU-07 dice que un turno `cancelled` no cambia de estado, así que `cancelled` -> `completed` debe rechazarse; el escenario no indica resultado. Además RN-TU-07 dice que `completed` y `no_show` se marcan "desde el turno ya iniciado": no está definido qué pasa con un turno `scheduled` futuro (no iniciado). | `RN-TU-07`, `05_reglas_de_negocio.md`; estados en `04_modelo_de_datos.md` | Escribir el escenario como error de negocio (transición rechazada). Agregar escenarios para `scheduled` -> `completed` antes y después del inicio (decisión a confirmar qué error se devuelve). |
| 6 | Borde faltante | 3 | Faltan las demás transiciones de estado: `completed`/`no_show` -> otro estado, y `cancelled` -> `scheduled` (reactivar). La KB solo fija que `cancelled` no cambia; el resto no está dicho. | `RN-TU-07`, `05_reglas_de_negocio.md`; sobre `completed`/`no_show` finales: sin respaldo en la KB | No inventar la matriz de transiciones; pedirla al usuario (ver decisión 3). |
| 7 | Pregunta abierta que bloquea | 4 | El escenario da por cierto que se aceptan varios turnos del mismo paciente el día, pero RN-TU-08 lo marca como suposición SU-05 "a validar", y sigue abierta (Media, bloquea la validación de turnos). Además el caso con el MISMO profesional se superpondría con RN-TU-01; el escenario solo cubre profesionales distintos y no hay escenario con turnos solapados del mismo paciente con dos profesionales distintos. | `RN-TU-08`, `05_reglas_de_negocio.md`; `SU-05`, `09_decisiones_y_supuestos.md`; pregunta SU-05 en `10_preguntas_abiertas.md` | Marcar el escenario como "supuesto, sujeto a SU-05". Decidir si el mismo paciente puede tener dos turnos a la misma hora con profesionales distintos (decisión a confirmar). |

### Escenarios sin hallazgos
Ninguno queda sin observaciones. El menos afectado es el 1 (el resultado, rechazo, es correcto; solo cambia la regla citada).

Cobertura del conjunto (lo exige la spec de un change): hay un escenario de error de negocio (1), pero no hay escenario esperado claro (el 2 hoy es incorrecto) ni un borde bien definido (falta el límite exacto, hallazgo 2). Es un hallazgo en sí mismo.

### Decisiones que necesitan al usuario
1. ¿Se reescribe el escenario 1 citando RN-TU-12 (con RN-TU-04 como caso incluido), y se agregan los dos escenarios de límite exacto de `min_notice_hours`?
2. ¿El escenario 2 debe pasar a "rechazar un turno que empieza en 5 horas" (con `min_notice_hours` = 6)? ¿Hace falta un escenario de aceptación con más de 6 horas y otro con `min_notice_hours` = 12?
3. ¿Cuál es la matriz completa de transiciones de estado permitidas (`scheduled`, `cancelled`, `completed`, `no_show`)? ¿Un turno `scheduled` futuro puede marcarse `completed`? La KB solo fija que `cancelled` no cambia (RN-TU-07).
4. ¿Se confirma SU-05 (varios turnos del paciente el mismo día), y se permite que se solapen en horario con profesionales distintos?
5. ¿Se contesta ya la pregunta de la excepción de emergencia (RN-TU-12), o la spec dice explícitamente que queda fuera?

Nota: ninguna de las sugerencias se registró en la KB; quedan pendientes de la confirmación del usuario.
