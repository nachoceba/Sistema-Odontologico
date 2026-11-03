# Design: completar-dominio-agenda (C-05c)

## Context

Motivación y alcance: ver `proposal.md`. Requisitos: ver `specs/schedule-validation`, `specs/appointment-status-transitions` y `specs/patient-booking-eligibility`.

Estado del código al proponer (verificado leyendo `backend/app/domain/`):

- `appointments/types.py` define `WorkingHours`, `TimeOff`, `ExistingAppointment`, `AppointmentStatus` (4 estados), `RejectionReason`, `ValidationResult`, `Slot`, `SlotStatus`.
- `appointments/rules.py` concentra los helpers compartidos de C-05a y C-05b (DD-20), entre ellos `is_on_time_off` (licencia inclusiva, RN-HO-03).
- `validate_appointment` y `compute_slots` asumen que los tramos son válidos (`start < end`, sin superposición): nadie lo verifica todavía.
- No existen `domain/schedules/`, `domain/patients/` ni reglas de transición de estado.
- 71 tests en verde (`backend/tests/unit/`), estilo: helpers de datos ficticios en `tests/unit/domain/appointments/helpers.py`, dataclasses inmutables, resultados con motivo en lugar de excepciones.

Restricciones: regla dura 2 (dominio puro, solo librería estándar), Strict TDD, governance MEDIO.

## Goals / Non-Goals

**Goals:**

- Que C-07 pueda rechazar un horario o una licencia inválidos con una sola llamada al dominio, mostrando todos los problemas a la vez.
- Que C-08 tenga un único lugar que diga qué cambios de estado y qué reprogramaciones se permiten, y si un paciente puede recibir turnos.
- Cero cambios de comportamiento en `appointment-creation` y `slot-availability`.

**Non-Goals:**

- Detectar turnos en conflicto con un horario o licencia nuevos (RN-HO-04, C-07).
- Validar que un tramo sea compatible con `slot_minutes` (ver P-10).
- Persistir cambios de estado, `cancel_reason` o quién canceló (C-08; pregunta "Baja" de auditoría en `10_preguntas_abiertas.md`).
- Puertos de repositorios y repositorios en memoria (ver §Partición: se proponen como C-05d).

## Decisions

### D-1 — Partición: C-05c solo reglas puras; puertos de repositorios a C-05d

El alcance restante de C-05 mezcla dos cosas distintas: reglas puras (tramos, licencias, transiciones, paciente inactivo) y la forma de los puertos de repositorio con sus implementaciones en memoria. Los puertos describen qué consultas necesitan los casos de uso (C-07, C-08); definirlos antes de esos casos de uso obliga a adivinar firmas (por ejemplo, si `AppointmentRepository` busca por rango UTC o por día local, o si el repositorio traduce el error del constraint de exclusión). **Recomendación**: C-05c cubre solo las reglas; C-05d `puertos-repositorios-dominio` se prepara inmediatamente antes de C-07/C-08 (o se absorbe en C-08). **Alternativa descartada**: meter todo en C-05c; el change crecería con interfaces sin consumidor real y tests que solo prueban diccionarios.

### D-2 — Ubicación de los módulos

- `backend/app/domain/schedules/validation.py`: `validate_working_hours`, `validate_time_off`, `is_date_in_time_off`. Respaldo: estructura de directorios de `08_arquitectura_propuesta.md` (`domain/schedules/ # working_hours, time_off`).
- `backend/app/domain/appointments/transitions.py`: `validate_status_change` y `validate_reschedule_eligibility`.
- `backend/app/domain/patients/eligibility.py`: `check_patient_can_book`.
- `WorkingHours` y `TimeOff` **se quedan** en `appointments/types.py` y `schedules` los importa. Mover los tipos rompería los imports de 71 tests y de `compute_slots` sin beneficio funcional. Alternativa (mover tipos a `schedules/types.py` y reexportar) queda para un refactor posterior si hace falta.

### D-3 — `is_date_in_time_off` reutiliza el helper existente

`is_on_time_off` pasa a vivir en `domain/schedules` con el nombre público `is_date_in_time_off`, y `appointments/rules.py` lo importa desde ahí (una sola fuente, DD-20). Dirección de dependencia: `appointments` → `schedules`, nunca al revés. Los 71 tests existentes son la red de seguridad (task de safety net antes y después). Alternativa descartada: una segunda implementación en `schedules` (dos copias de RN-HO-03 podrían divergir).

### D-4 — Forma de los resultados

- Tramos: `ScheduleValidationResult(valid: bool, problems: tuple[ScheduleProblem, ...])`, con `ScheduleProblem(code: ScheduleProblemCode, block_indexes: tuple[int, ...])`. Los índices se refieren a la posición del tramo en la entrada original (C-07 los usa para señalar la fila en pantalla). `valid` es `True` si y solo si `problems` está vacío. Problemas ordenados de forma determinista: primero por índice menor, luego por código. Para superposición, `block_indexes` lleva el par ordenado de menor a mayor, una vez por par.
- Licencia: mismo `ScheduleValidationResult` con un único problema `END_BEFORE_START` y `block_indexes=()`.
- Transiciones y reprogramación: `TransitionResult(allowed: bool, reason: TransitionRejection | None)`, con `accept()` / `reject(reason)` como `ValidationResult` de C-05a.
- Paciente: `EligibilityResult(allowed: bool, reason: EligibilityRejection | None)`.
- Por qué todos los problemas y no el primero (a diferencia de C-05a): en C-07 el administrador edita la semana entera de una vez y conviene marcarle todas las filas mal. En la creación de un turno, un solo motivo alcanza.

### D-5 — Algoritmo de superposición de tramos

Primero se marcan los problemas individuales (`INVALID_WEEKDAY`, `START_NOT_BEFORE_END`, `SUB_MINUTE_PRECISION`); los tramos sin problemas individuales se agrupan por `weekday` y se comparan por pares con la regla semiabierta `a.start < b.end and b.start < a.end` (misma semántica que `ranges_overlap` de `rules.py`). O(n²) por día es suficiente: un profesional tiene pocos tramos por día. Alternativa (ordenar y comparar vecinos) informa menos pares cuando tres tramos se solapan entre sí, y el spec pide uno por par.

### D-6 — Precondiciones que lanzan `ValueError`

Igual que C-05a y C-05b (DD-18): datetimes sin zona en transiciones, y un `active` que no es `bool` en elegibilidad. Son errores del llamador, no motivos de negocio. `bool` se chequea con `isinstance(active, bool)` para no aceptar `"false"` como verdadero.

### D-7 — Orden de evaluación de transiciones

Un único motivo, en el orden del spec: estado final `cancelled` → asistencia ya registrada → destino inválido → reglas de tiempo. Así un `cancelled` siempre responde `CANCELLED_IS_FINAL` (RN-TU-07), sin importar el destino pedido.

### Decisiones de dominio CONFIRMADAS por el usuario (P-1 a P-10, recomendaciones aceptadas; registradas como DD-21 a DD-30)

Ninguna de estas tiene respaldo directo en la KB; el usuario aceptó cada recomendación tal cual. P-6 descartó explícitamente un tope de horario configurable.

| # | Pregunta | Recomendación | Respaldo |
|---|----------|---------------|----------|
| P-1 | ¿Se puede cancelar un turno `scheduled` que ya inició o pasó? | No: solo antes del inicio; después corresponde `no_show` o `completed`. | RN-TU-05 no pone límite de tiempo: **sin respaldo en la KB** |
| P-2 | ¿`completed` y `no_show` son finales, o se puede corregir un error de carga (`completed` ↔ `no_show`)? | Finales en v1 (`ATTENDANCE_ALREADY_RECORDED`); la corrección queda para después junto con la auditoría. | RN-TU-07 solo dice que `cancelled` no cambia: **sin respaldo en la KB** |
| P-3 | "Ya iniciado" (US-010): ¿`now >= starts_at` o `now >= ends_at`? | `now >= starts_at`, con el inicio exacto incluido. | RN-TU-07 y US-010 ("ya iniciados"); el borde exacto **sin respaldo en la KB** |
| P-4 | ¿Qué turnos se pueden reprogramar? | Solo `scheduled` y antes de su inicio. | RN-TU-06 habla solo de las validaciones del nuevo horario: **sin respaldo en la KB** |
| P-5 | ¿RN-PA-04 aplica también al reprogramar? ¿Qué pasa con los turnos `scheduled` futuros de un paciente que se desactiva? | Que C-08 lo aplique también al reprogramar; desactivar no cancela turnos (se listan, como RN-HO-04). Afecta a C-06/C-08, no a la función de este change. | RN-PA-03, RN-PA-04, RN-TU-06: **sin respaldo en la KB** para ambos casos |
| P-6 | ¿Un tramo puede cruzar la medianoche o terminar a las 24:00? | No (último fin posible 23:59); `start_time < end_time` literal. | RN-HO-02 y constraint de `working_hours`; el caso 24:00 **sin respaldo en la KB** |
| P-7 | ¿Dos tramos contiguos (uno termina 13:00 y el otro empieza 13:00) se superponen? | No (semiabierto), coherente con el escenario ya archivado "Tramos contiguos con anclas distintas" de `slot-availability`. | RN-HO-02 no define el borde |
| P-8 | ¿Se aceptan licencias superpuestas entre sí o con fechas pasadas? | Sí: la validación solo exige `starts_on <= ends_on`; superponerlas no cambia la disponibilidad. | Constraint de `time_off` en `04_modelo_de_datos.md`; el resto **sin respaldo en la KB** |
| P-9 | ¿Se rechazan tramos con segundos (09:00:30)? | Sí (`SUB_MINUTE_PRECISION`): la grilla trabaja en minutos y `minutes_of_day` ignora segundos. | **sin respaldo en la KB** |
| P-10 | ¿Un tramo más corto que `slot_minutes` es válido? | Sí: la validación no depende de `slot_minutes` (que puede cambiar en `clinic_settings`); `compute_slots` ya lo muestra `OUTSIDE_HOURS`. | RN-TU-02, DD-15; la validez del tramo **sin respaldo en la KB** |

### Revisión de escenarios (skill `revisor-escenarios-turnos`)

Revisión hecha sobre el borrador de las tres specs, leyendo en el momento `05_reglas_de_negocio.md`, `10_preguntas_abiertas.md`, `09_decisiones_y_supuestos.md`, `04_modelo_de_datos.md` y la entrada C-05 de `CHANGES.md`.

**Resumen**: 43 escenarios revisados, 14 hallazgos (2 ambigüedades, 2 bordes faltantes, 1 regla solapada, 1 pregunta abierta, 7 sin respaldo, 1 contrato incompleto, 0 contradicciones).

| # | Tipo | Escenario afectado | Qué pasa | Respaldo en la KB | Sugerencia (a confirmar) |
|---|------|--------------------|----------|-------------------|--------------------------|
| 1 | Contrato incompleto | Fecha local dentro de una licencia | `CHANGES.md` (C-05) pide `is_date_in_time_off` en `domain/schedules`, pero la regla ya existe como `is_on_time_off` en `appointments/rules.py` | `CHANGES.md` §C-05, RN-HO-03 | Exponerla desde `schedules` sin duplicar (D-3) |
| 2 | Sin respaldo | Cancelar un turno ya iniciado | RN-TU-05 no limita en el tiempo la cancelación | sin respaldo en la KB | P-1 |
| 3 | Sin respaldo | Asistencia ya registrada | RN-TU-07 solo declara final a `cancelled` | sin respaldo en la KB | P-2 |
| 4 | Ambigüedad | Marcar en el instante exacto del inicio | "ya iniciado" admite inicio o fin del turno | RN-TU-07, US-010 (`06_funcionalidades.md`) | P-3 |
| 5 | Sin respaldo | Reprogramar un turno ya iniciado / cancelado | RN-TU-06 no dice qué estados se reprograman | sin respaldo en la KB | P-4 |
| 6 | Pregunta abierta | Paciente inactivo | "turnos nuevos" no aclara si reprogramar cuenta | RN-PA-04, RN-TU-06 | P-5 (decide C-08) |
| 7 | Borde faltante | Paciente inactivo con turnos futuros | No hay regla para los turnos ya agendados al desactivar | RN-PA-03 | P-5; fuera de este change (C-06/C-08) |
| 8 | Sin respaldo | Tramo que intenta cruzar la medianoche | 24:00 no es representable con `start_time < end_time` | RN-HO-02, `04_modelo_de_datos.md` §working_hours | P-6 |
| 9 | Ambigüedad | Tramos contiguos | "no se superponen" no define el borde | RN-HO-02 | P-7 (coherente con `slot-availability`) |
| 10 | Sin respaldo | Validez de una licencia | Licencias superpuestas o pasadas | `04_modelo_de_datos.md` §time_off (solo `starts_on <= ends_on`) | P-8 |
| 11 | Sin respaldo | Tramo con segundos | Precisión de los tramos | sin respaldo en la KB | P-9 |
| 12 | Sin respaldo | Tramo más corto que un slot | ¿Tramo inútil es válido? | RN-TU-02, DD-15 | P-10 |
| 13 | Regla solapada | Validación de tramos | Cambiar horarios dispara conflictos (RN-HO-04); la validación no los detecta | RN-HO-04, Flujo 5 | Dejar explícito que los conflictos son de C-07 (Non-Goals) |
| 14 | Borde faltante | Matriz de transiciones | Faltaba `scheduled` → `scheduled` y `cancelled` → `cancelled` | RN-TU-07 | Agregados: `INVALID_TARGET_STATUS` y `CANCELLED_IS_FINAL` |

Pregunta abierta de la KB relacionada que **no bloquea** este change: SU-06 (quién edita horarios) afecta permisos de C-07, no la validez de un tramo. SU-05 (varios turnos por paciente el mismo día) no se toca: la elegibilidad del paciente solo mira `active`.

Cobertura mínima por capability: `schedule-validation` (esperado, error de negocio y bordes: sí), `appointment-status-transitions` (sí), `patient-booking-eligibility` (sí).

## Risks / Trade-offs

- [Las respuestas a P-1..P-10 cambian escenarios] → Cada escenario afectado está marcado; las tasks agrupan los tests pendientes para poder ajustarlos sin rehacer el resto. Recomendado: confirmar antes de `/opsx:apply`.
- [Mover `is_on_time_off` rompe imports de C-05a/C-05b] → Safety net de 71 tests antes y después; `rules.py` reexporta el nombre viejo durante el change si algún test lo importa directo.
- [`validate_working_hours` y el constraint de la base pueden divergir] → El constraint de `working_hours` solo cubre `start_time < end_time`; la no superposición no tiene constraint en el modelo. C-07 debe decidir si agrega un `EXCLUDE` análogo al de `appointments` (fuera de este change).
- [Puertos postergados a C-05d] → C-07/C-08 no arrancan sin ellos; se mitiga preparándolos justo antes, con las firmas que pidan esos casos de uso.
- [Sin typecheck ni lint locales (mypy, ruff no instalados)] → Igual que C-05b; se deja anotado en el reporte de apply.

## Migration Plan

No aplica: código nuevo puro y un movimiento interno sin cambio de comportamiento. Rollback = revertir el commit.

## Open Questions

Las decisiones P-1 a P-10 están confirmadas (ver tabla). Queda D-1 (partición en C-05d). Ninguna cambia la estructura de módulos ni la forma de los resultados; solo el resultado esperado de los escenarios marcados.
