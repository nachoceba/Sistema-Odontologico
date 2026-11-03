# Tasks

Strict TDD: en cada grupo de comportamiento el orden es RED (test que falla) → GREEN (código mínimo) → TRIANGULATE (más casos con otros datos hasta cubrir todos los escenarios del requisito) → REFACTOR (tests siguen en verde). Cada escenario de las specs tiene su test; los bordes de un mismo requisito van en un `@pytest.mark.parametrize` con `pytest.param(..., id="...")`. Comando de verificación, desde `backend/`: `python -m pytest`. Los 71 tests existentes (C-05a y C-05b) son la red de seguridad: cualquier rojo en ellos detiene el trabajo. Datos ficticios (Dra. A `dra-a`; turno del lunes 5 de octubre de 2026 a las 10:00 locales). Las decisiones P-1 a P-10 fueron confirmadas por el usuario (DD-21 a DD-30).

## 0. Confirmación previa

- [x] 0.1 Confirmar con el usuario las decisiones P-1 a P-10 de `design.md` y la partición D-1 (C-05d); si alguna cambia, actualizar con `/opsx:update` los escenarios marcados antes de seguir. Verificación: cada P-n figura como confirmada o cambiada en `design.md`

## 1. Red de seguridad y estructura

- [x] 1.1 Safety net: correr `python -m pytest` y registrar "baseline: 71 passed"; si algo falla, detenerse y reportarlo como falla previa
- [x] 1.2 Crear `backend/app/domain/schedules/__init__.py`, `backend/app/domain/patients/__init__.py`, `backend/tests/unit/domain/schedules/__init__.py` y `backend/tests/unit/domain/patients/__init__.py`; verificar que `python -m pytest` sigue recolectando 71 tests sin errores de importación

## 2. Licencias en `domain/schedules` (`schedule-validation`: "Fecha local dentro de una licencia", "Validez de una licencia")

Archivo: `backend/tests/unit/domain/schedules/test_time_off.py`; código: `backend/app/domain/schedules/validation.py` (design D-3, D-4).

- [x] 2.1 RED → GREEN: `test_is_date_in_time_off` parametrizado con ids `dentro`, `primer_dia`, `ultimo_dia`, `dia_siguiente`, `sin_licencias` (4 escenarios del requisito); implementar `is_date_in_time_off` moviendo la lógica de `is_on_time_off` desde `appointments/rules.py`; verificar en verde
- [x] 2.2 REFACTOR D-3: `appointments/rules.py` importa `is_date_in_time_off` desde `domain/schedules` (sin segunda implementación); verificar que los 71 tests existentes siguen en verde y que `grep` no encuentra otra comparación `starts_on <= ... <= ends_on` en `domain/`
- [x] 2.3 RED → GREEN → TRIANGULATE: `test_validate_time_off` con ids `varios_dias`, `un_solo_dia`, `fin_antes_de_inicio`; crear `ScheduleValidationResult`, `ScheduleProblem`, `ScheduleProblemCode` y `validate_time_off`; verificar en verde

## 3. Tramos de horario (`schedule-validation`: tramos)

Archivo: `backend/tests/unit/domain/schedules/test_working_hours.py`; código: `validate_working_hours` en `backend/app/domain/schedules/validation.py` (design D-4, D-5).

- [x] 3.1 RED → GREEN: `test_valid_weekly_schedule` (escenario "Horario semanal válido") y `test_empty_schedule_is_valid`; implementación mínima; verificar en verde
- [x] 3.2 RED → GREEN → TRIANGULATE: `test_start_not_before_end` con ids `inicio_posterior`, `duracion_cero`, `cruza_medianoche` (P-6); verificar en verde
- [x] 3.3 RED → GREEN: `test_invalid_weekday` con ids `dia_7`, `dia_negativo_y_domingo`; verificar en verde
- [x] 3.4 RED → GREEN → TRIANGULATE: `test_overlapping_blocks` con ids `superpuestos`, `contenido`, `duplicado`, `tres_por_pares`, y `test_non_overlapping_blocks` con ids `contiguos` (P-7), `dias_distintos`; verificar en verde
- [x] 3.5 RED → GREEN: `test_input_order_does_not_change_result` y `test_invalid_block_skips_overlap_check`; verificar en verde
- [x] 3.6 RED → GREEN: `test_sub_minute_precision` (P-9) y `test_block_shorter_than_slot_is_valid` (P-10); verificar en verde
- [x] 3.7 RED → GREEN: `test_multiple_problems_reported_together` (escenario "Varios problemas a la vez"), con orden determinista de problemas (D-4); verificar en verde
- [x] 3.8 REFACTOR: type hints, docstrings que citan RN-HO-01/RN-HO-02, exportaciones en `schedules/__init__.py`; verificar que `schedules/` solo importa librería estándar y `app.domain.appointments.types`, y suite en verde

## 4. Transiciones de estado (`appointment-status-transitions`)

Archivo: `backend/tests/unit/domain/appointments/test_status_transitions.py`; código: `backend/app/domain/appointments/transitions.py` y tipos en `types.py` (design D-4, D-6, D-7).

- [x] 4.1 RED → GREEN: `test_cancel_before_start_is_allowed` (escenario esperado); crear `TransitionResult`, `TransitionRejection` y `validate_status_change` mínima; verificar en verde
- [x] 4.2 RED → GREEN → TRIANGULATE: `test_cancelled_is_final` parametrizado por destino (`completed`, `no_show`, `scheduled`, `cancelled`); `test_attendance_already_recorded` con ids `completed_a_no_show`, `completed_a_cancelled`, `no_show_a_completed` (P-2); `test_target_scheduled_is_invalid`; verificar en verde
- [x] 4.3 RED → GREEN → TRIANGULATE: `test_mark_attendance` con ids `completed_despues_inicio`, `inicio_exacto` (P-3), `dias_despues`; `test_mark_before_start_rejected` con ids `no_show_0959`, `instantes_no_hora_local`; verificar en verde
- [x] 4.4 RED → GREEN: `test_cancel_one_minute_before` y `test_cancel_after_start_rejected` (P-1); verificar en verde
- [x] 4.5 RED → GREEN: `test_naive_datetime_raises` (`pytest.raises(ValueError)`); verificar en verde
- [x] 4.6 RED → GREEN → TRIANGULATE: `test_reschedule_eligibility` con ids `futuro_permitido`, `cancelado`, `ya_iniciado` (P-4); implementar `validate_reschedule_eligibility` reutilizando las reglas de 4.2–4.4; verificar en verde
- [x] 4.7 REFACTOR: un único punto de orden de evaluación (D-7), docstrings con RN-TU-05/06/07, exportaciones en `appointments/__init__.py`; verificar suite en verde

## 5. Elegibilidad del paciente (`patient-booking-eligibility`)

Archivo: `backend/tests/unit/domain/patients/test_eligibility.py`; código: `backend/app/domain/patients/eligibility.py` (design D-4, D-6).

- [x] 5.1 RED → GREEN → TRIANGULATE: `test_active_patient_can_book`, `test_inactive_patient_rejected` (`PATIENT_INACTIVE`, RN-PA-04) y `test_non_bool_active_raises` con ids `none`, `texto_false`; verificar en verde
- [x] 5.2 REFACTOR: docstring con RN-PA-04 y la nota de P-5; exportaciones en `patients/__init__.py`; verificar suite en verde

## 6. Verificación de integración

- [x] 6.1 Correr `python -m pytest` completo: 71 existentes + nuevos en verde (anotar el total); verificar con `grep` que ningún archivo de `backend/app/domain/` importa `fastapi`, `sqlalchemy`, `celery` ni `redis` (regla dura 2)
- [x] 6.2 Intentar typecheck y lint (`mypy`, `ruff`); si no están instalados, dejarlo anotado en el reporte de apply (regla dura 9)
- [x] 6.3 `openspec validate completar-dominio-agenda --strict` en verde
