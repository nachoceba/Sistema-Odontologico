# Tasks

Strict TDD: en cada grupo de comportamiento el orden es RED (test que falla) → GREEN (código mínimo) → TRIANGULATE (segundo caso con otros datos) → REFACTOR (tests siguen en verde). Cada test corresponde a un escenario de `specs/appointment-creation/spec.md` (mapeo en `design.md` D8). Comando de verificación, desde `backend/`: `python -m pytest`.

## 1. Arranque mínimo de backend (sin tests de comportamiento)

- [x] 1.1 Safety net: confirmar que no existen tests previos (no hay `backend/` ni archivos `.py`); registrar "baseline: 0 tests" en las notas del apply
- [x] 1.2 Crear `backend/pyproject.toml` según design D6 (Python >=3.12, sin dependencias de runtime de framework, `tzdata`, pytest en el grupo `dev`, `[tool.pytest.ini_options]` con `testpaths = ["tests"]` y `pythonpath = ["."]`); verificar que no menciona FastAPI, SQLAlchemy, Celery, Redis ni Docker
- [x] 1.3 Crear los paquetes `backend/app/__init__.py`, `backend/app/domain/__init__.py`, `backend/app/domain/appointments/__init__.py` y la carpeta `backend/tests/unit/domain/appointments/`; verificar con `python -m pytest` que la suite corre (0 tests recolectados, sin errores de importación)

## 2. Tipos y caso feliz

- [x] 2.1 RED: escribir `test_accepts_free_slot_and_computes_ends_at` (escenario "Turno libre dentro del horario") con helpers de hora local y horario de la Dra. A; verificar que falla porque `validate_appointment` no existe
- [x] 2.2 GREEN: crear `backend/app/domain/appointments/types.py` (`AppointmentStatus`, `WorkingHours`, `TimeOff`, `ExistingAppointment`, `RejectionReason`, `ValidationResult`) y `validation.py` con `validate_appointment` mínima según design D1/D2; verificar que el test pasa
- [x] 2.3 TRIANGULATE: agregar `test_utc_instant_is_evaluated_in_clinic_local_time` (escenario "El instante en UTC se interpreta en hora local") y `test_naive_datetime_raises_value_error` (design D3); generalizar el cálculo de `ends_at` y la validación de zona; verificar suite en verde
- [x] 2.4 REFACTOR: mover helpers de test a `conftest.py` si se repiten, revisar type hints y re-exportar la API desde `appointments/__init__.py`; verificar suite en verde y que `domain/` no importa nada fuera de la librería estándar

## 3. Anticipación mínima (RN-TU-12, cubre RN-TU-04)

- [x] 3.1 RED: escribir `test_rejects_insufficient_notice`; verificar que falla
- [x] 3.2 GREEN: implementar la regla 1 (`starts_at < now + min_notice_hours` → `INSUFFICIENT_NOTICE`); verificar que pasa
- [x] 3.3 TRIANGULATE: agregar `test_accepts_exactly_min_notice` (límite inclusivo), `test_rejects_start_in_the_past` y `test_rejects_with_configured_12h_notice`; verificar suite en verde
- [x] 3.4 REFACTOR: extraer la regla a una función privada con nombre claro; verificar suite en verde

## 4. Grilla de slots (RN-TU-02)

- [x] 4.1 RED: escribir `test_rejects_off_grid_start` (10:10); verificar que falla
- [x] 4.2 GREEN: implementar la regla 2 (inicio local dentro de un tramo y no múltiplo de `slot_minutes` desde el inicio del tramo → `OFF_GRID`); verificar que pasa
- [x] 4.3 TRIANGULATE: agregar `test_grid_is_anchored_to_block_start` (tramo 09:15, turno 09:45 aceptado); verificar suite en verde
- [x] 4.4 REFACTOR: extraer la conversión a hora local y la búsqueda de tramos del día a helpers privados reutilizables; verificar suite en verde

## 5. Horario de trabajo (RN-TU-03)

- [x] 5.1 RED: escribir `test_rejects_before_working_hours` (08:30); verificar que falla
- [x] 5.2 GREEN: implementar la regla 3 (turno completo dentro de un tramo del weekday local, 0 = lunes → si no, `OUTSIDE_WORKING_HOURS`); verificar que pasa
- [x] 5.3 TRIANGULATE: agregar `test_rejects_gap_between_blocks` (13:00), `test_accepts_last_slot_ending_at_block_end` (12:30) y `test_rejects_day_without_working_hours` (martes); verificar suite en verde
- [x] 5.4 REFACTOR: revisar nombres y duplicación con la regla de grilla; verificar suite en verde

## 6. Licencias (RN-TU-03, RN-HO-03)

- [x] 6.1 RED: escribir `test_rejects_on_last_day_of_time_off` (licencia 1 al 5 inclusive, turno el 5); verificar que falla
- [x] 6.2 GREEN: implementar la regla 4 (fecha local dentro de `[starts_on, ends_on]` → `PROFESSIONAL_TIME_OFF`); verificar que pasa
- [x] 6.3 TRIANGULATE: agregar un caso con el día siguiente al fin de la licencia (debe aceptarse) para fijar el límite inclusivo; verificar suite en verde
- [x] 6.4 REFACTOR: extraer la regla a una función privada; verificar suite en verde

## 7. No solapamiento (RN-TU-01)

- [x] 7.1 RED: escribir `test_rejects_overlap_with_same_professional` (error de negocio); verificar que falla
- [x] 7.2 GREEN: implementar la regla 5 (mismo `professional_id`, `status == SCHEDULED`, rangos `[inicio, fin)` → `OVERLAPS_EXISTING`); verificar que pasa
- [x] 7.3 TRIANGULATE: agregar `test_accepts_back_to_back_after_existing` (10:30, borde), `test_accepts_back_to_back_before_existing` (09:30), `test_accepts_same_time_other_professional` y `test_cancelled_appointment_does_not_block`; verificar suite en verde
- [x] 7.4 REFACTOR: extraer el predicado de superposición a una función pura con nombre propio; verificar suite en verde

## 8. Orden fijo de evaluación

- [x] 8.1 RED/GREEN: escribir `test_notice_wins_over_off_grid` y `test_time_off_wins_over_overlap`; si alguno falla, ajustar el orden de evaluación en `validate_appointment` hasta que pasen (orden: anticipación, grilla, horario, licencia, solapamiento)
- [x] 8.2 REFACTOR: dejar el orden explícito y legible en `validate_appointment` (una secuencia de chequeos) con docstring que cite RN-TU-12, RN-TU-02, RN-TU-03, RN-HO-03 y RN-TU-01; verificar suite en verde

## 9. Verificación final y documentación

- [x] 9.1 Correr toda la suite desde `backend/` con `python -m pytest -v`; verificar que pasan los 21+ tests y que cada escenario del spec tiene su test (tabla D8 de `design.md`)
- [x] 9.2 Verificar con una búsqueda en `backend/app/domain/` que no hay imports de FastAPI, SQLAlchemy, Celery, Redis ni lecturas del reloj (`datetime.now`, `utcnow`)
- [x] 9.3 Revisar que la documentación actualizada en la fase propose (`knowledge-base/05`, `04`, `09`, `10` y la nota de C-05 en `CHANGES.md`) coincide con lo implementado (nombres de motivos, default de 6 h, convenciones); corregir cualquier diferencia y anotarla
