## Revisión de escenarios: spec vigente `appointment-creation` (change archivado C-05a)

### Resumen
20 escenarios revisados, 10 hallazgos (1 ambigüedad, 4 bordes faltantes, 1 regla solapada, 3 preguntas abiertas, 1 sin respaldo).

Veredicto: la spec está bien para el recorte C-05a. Cada escenario mapea a una regla (RN-TU-01, -02, -03, -04, -12, RN-HO-03, RN-GL-01) y cubre un caso feliz, errores de negocio y bordes inclusivos. Tiene huecos de bordes y dos decisiones de dominio que figuran como hechos sin respaldo en la KB.

### Hallazgos
| # | Tipo | Escenario afectado | Qué pasa | Respaldo en la KB | Sugerencia (a confirmar) |
|---|------|--------------------|----------|-------------------|--------------------------|
| 1 | Borde faltante | Req. "Fuera de las licencias" (un solo escenario) | Solo se prueba el último día de una licencia. Faltan: licencia de un único día, primer día, día siguiente al fin (debe aceptar) y licencia de otro profesional (el texto lo dice, sin escenario). | RN-HO-03, `05_reglas_de_negocio.md` | Agregar esos escenarios, en particular el día siguiente al fin y la licencia de un solo día. |
| 2 | Borde faltante | "El instante en UTC se interpreta en la hora local" | Solo hay un caso (13:00 UTC = 10:00 local), sin cambio de día. Falta un turno cuyo día local difiere del día UTC (p. ej. 23:00 local = 02:00 UTC del día siguiente). Eso afecta el día de la semana del horario y la licencia. No se dice qué día cuenta si el turno cruza medianoche local. | RN-GL-01, `05_reglas_de_negocio.md` | Escenario de cambio de día; definir que el día local del inicio decide horario y licencia. Decisión a confirmar. |
| 3 | Pregunta abierta | Todos los escenarios con hora local | La spec asume una hora local fija (el ejemplo implica UTC-3) sin nombrar la zona. La zona del consultorio es un supuesto sin confirmar. | SU-01 (`09_decisiones_y_supuestos.md`); pregunta "¿Cuál es la zona horaria del consultorio?", prioridad Media (`10_preguntas_abiertas.md`) | Nombrar la zona en la spec como supuesto SU-01 hasta que el dueño la confirme. |
| 4 | Sin respaldo | Req. "Un solo motivo con orden fijo de evaluación" | El orden (anticipación, grilla, horario, licencia, solapamiento) y la lista cerrada de 5 motivos no están en ninguna RN, DD ni SU. Solo se prueban 2 pares de reglas, y falta p. ej. día con licencia y sin horario. | sin respaldo en la KB | Registrar el orden como DD con justificación, o agregarlo a RN-TU. Decisión a confirmar. |
| 5 | Ambigüedad | Req. "Turno completo dentro del horario" y "grilla" | (a) Tramo cuyo largo no es múltiplo de `slot_minutes` (p. ej. 09:00-13:15): el inicio 13:00 está en grilla pero el fin 13:30 se pasa. Debería dar `OUTSIDE_WORKING_HOURS`, pero no hay escenario. (b) Dos tramos pegados (09-13 y 13-18): RN-HO-02 prohíbe solapar, no que se toquen. No se aclara si un turno puede cruzar el borde entre ambos. | RN-TU-02 y RN-TU-03; RN-HO-02 (`05_reglas_de_negocio.md`) | Escenario del slot que no entra completo; tratar "dentro de un tramo" como un único tramo, sin unir adyacentes. A confirmar. |
| 6 | Borde faltante | Req. "Inicio dentro de la grilla" | Todos los escenarios usan 30 min y un solo tramo. Faltan: `slot_minutes` distinto de 30 y un día con dos tramos donde la grilla se reinicia en el segundo. La duración real del slot sigue abierta. | RN-TU-02; pregunta "duración de slot" Baja (`10_preguntas_abiertas.md`) | Escenario con `slot_minutes = 20` y otro con segundo tramo desfasado (14:15). |
| 7 | Regla solapada | Req. "Anticipación mínima (RN-TU-12)" | RN-TU-04 y RN-TU-12 se pisan. `min_notice_hours` es configurable, pero la KB no dice qué pasa con 0 o negativo, que dejaría pasar el pasado y contradeciría RN-TU-04 ("nunca es válido"). No hay escenario del borde exacto de 12 h configurado. | RN-TU-04, RN-TU-12, DD-14 (`05_reglas_de_negocio.md`, `09_decisiones_y_supuestos.md`) | Fijar que el pasado se rechaza siempre aunque `min_notice_hours` sea 0; validar el rango del setting. A confirmar. |
| 8 | Pregunta abierta | Req. "Sin solapamiento": "No se valida nada por paciente" | RN-PA-04 prohíbe turnos nuevos a un paciente inactivo y RN-TU-08/SU-05 (varios turnos por día) está sin validar. La spec no tiene motivo de rechazo para el paciente inactivo y no aclara si queda diferido. | RN-PA-04, RN-TU-08; SU-05 y pregunta Media (`10_preguntas_abiertas.md`) | Anotar en la spec que el paciente queda fuera de C-05a y se cubre en un change posterior. |
| 9 | Pregunta abierta | Req. "Anticipación mínima" | No hay excepción para urgencias del mismo día. La KB lo deja abierto y la spec no lo menciona como fuera de alcance. | DD-14 (trade-offs) y pregunta Media sobre saltar la anticipación (`10_preguntas_abiertas.md`) | Una línea en la spec: "sin excepciones en v1 (pregunta abierta)". |
| 10 | Borde faltante | Req. "Sin solapamiento": ignorar estados distintos de `scheduled` | Solo se prueba `cancelled`. El texto dice "cualquier otro estado" (`completed`, `no_show`) sin escenario. | RN-TU-01, RN-TU-05, RN-TU-07 (`05_reglas_de_negocio.md`) | Escenario con `no_show` o `completed`. Es de bajo riesgo porque RN-TU-07 los ubica en turnos ya iniciados. |

Sospechas sin cita en la KB, que no cuento como hallazgos: no consulté `04_modelo_de_datos.md`. No sé si hace falta cubrir un profesional inexistente o inactivo, ni una licencia con fin anterior al inicio. Conviene revisarlo contra ese archivo antes de decidir.

### Escenarios sin hallazgos
- Turno libre dentro del horario (feliz).
- Anticipación insuficiente, anticipación exacta de 6 h, turno en el pasado.
- Inicio fuera de la grilla; la grilla se cuenta desde el inicio del tramo.
- Antes del inicio del horario, hueco entre dos tramos, último slot del tramo, día sin horario.
- Pisa a otro turno, empieza justo cuando termina otro, termina justo cuando empieza otro, mismo horario con otro profesional, turno cancelado.
- Anticipación insuficiente + fuera de grilla, licencia + solapamiento (válidos, pero ver hallazgo 4 sobre el orden).

### Decisiones que necesitan al usuario
1. Zona horaria del consultorio: ¿se confirma `America/Argentina/Buenos_Aires` (SU-01)? Hoy la spec la usa sin nombrarla.
2. Si un turno cruza la medianoche local, ¿qué día manda para el horario de trabajo y la licencia: el del inicio o el del fin? (sugerencia: el del inicio)
3. ¿Se registra como decisión (DD) el orden fijo de evaluación y la lista cerrada de motivos?
4. ¿Se rechaza siempre el pasado aunque `min_notice_hours` sea 0, y se valida el rango del setting?
5. ¿Dos tramos pegados (09-13 y 13-18) se tratan como tramos separados, de modo que un turno no puede cruzar entre ellos?
6. ¿La validación de paciente inactivo (RN-PA-04) y de varios turnos por día (SU-05) queda formalmente fuera de esta spec y se difiere a otro change?
7. ¿Se agregan los escenarios de bordes (hallazgos 1, 2, 5, 6, 10) como un nuevo recorte (C-05b/C-05c) o con un update del change?
