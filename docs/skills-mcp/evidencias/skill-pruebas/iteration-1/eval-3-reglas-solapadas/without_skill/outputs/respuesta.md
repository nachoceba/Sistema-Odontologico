# Revision de escenarios de agenda (contra knowledge-base/)

Fuentes: 05_reglas_de_negocio.md (RN-TU-01..12), 09_decisiones_y_supuestos.md (DD-14, SU-05), 04_modelo_de_datos.md (enum status).

## 1. Rechazar un turno cuyo inicio esta en el pasado (RN-TU-04)
- Correcto en el resultado (se rechaza), pero la regla efectiva es RN-TU-12 (DD-14): RN-TU-04 "queda cubierto" por la anticipacion minima. Citar RN-TU-12 como regla primaria; RN-TU-04 queda como caso particular.
- Faltan casos de borde: inicio exactamente "ahora"; inicio en el pasado inmediato (hace 1 minuto); comparacion en UTC vs. zona del consultorio (RN-GL-01, SU-01 abierta); reprogramacion (RN-TU-06) con nuevo inicio en el pasado.
- Dato inyectable: la funcion de dominio debe recibir "ahora" como parametro (pura).

## 2. Aceptar un turno que empieza dentro de 5 horas -- ERRONEO
- Contradice RN-TU-12: `min_notice_hours` por defecto es 6, asi que un turno a 5 h se RECHAZA con la config por defecto. Solo se aceptaria si el valor configurado fuera <= 5.
- Reescribir: "rechazar turno a 5 h (min_notice 6)"; agregar los pares de borde: exactamente 6 h se ACEPTA (limite inclusivo, explicito en RN-TU-12) y 6 h menos un instante se rechaza.
- Agregar escenario con `min_notice_hours` configurado distinto (p. ej. 4 -> 5 h se acepta) y con 0.
- Ademas debe cumplir RN-TU-01/02/03 (grilla, horario laboral, licencias); el escenario no lo aclara.

## 3. Un turno `cancelled` pasa a `completed` -- ERRONEO
- Contradice RN-TU-07: un turno `cancelled` no cambia de estado. Debe RECHAZARse.
- Reescribir como rechazo. Casos faltantes: `cancelled` -> `no_show`, `cancelled` -> `scheduled`; `scheduled` -> `completed`/`no_show` solo si el turno ya inicio (RN-TU-07: "desde el turno ya iniciado"), por lo que un `scheduled` futuro -> `completed` debe rechazarse; transiciones desde `completed`/`no_show` (la KB no define si son terminales: ambiguedad a registrar en preguntas abiertas); permisos por rol.

## 4. Dos turnos del mismo paciente el mismo dia con distintos profesionales se aceptan -- Correcto, pero incompleto
- Respaldado por RN-TU-08 (varios turnos por dia), aunque es suposicion SU-05 "a validar": marcar el escenario como dependiente de un supuesto no confirmado.
- Ojo: RN-TU-08 no restringe "distintos profesionales"; tambien aplicaria con el mismo profesional en horarios distintos. Y el mismo paciente en dos turnos que se SOLAPAN en tiempo con profesionales distintos: la KB no lo prohibe (RN-TU-01 es por profesional; RN-TU-09: no hay control de recurso fisico) -> ambiguedad no cubierta; decidir y documentar.
- Casos faltantes: mismo paciente, mismo profesional, mismo dia, sin solape (se acepta); solape exacto del mismo paciente con dos profesionales; paciente inactivo (RN-PA-03).

## Resumen
| # | Veredicto |
|---|-----------|
| 1 | Valido, citar RN-TU-12 ademas de RN-TU-04; agregar bordes |
| 2 | Invalido con la config por defecto (6 h); reescribir como rechazo + limite exacto |
| 3 | Invalido (RN-TU-07); debe ser rechazo |
| 4 | Valido con reservas (SU-05 sin validar; solape del paciente sin definir) |

Escenarios 2 y 3 contradicen reglas vigentes de la KB.
