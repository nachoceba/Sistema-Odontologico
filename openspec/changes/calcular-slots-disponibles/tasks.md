# Tasks

Strict TDD: en cada grupo de comportamiento el orden es RED (test que falla) → GREEN (código mínimo) → TRIANGULATE (más casos con otros datos, hasta cubrir todos los escenarios del requisito) → REFACTOR (tests siguen en verde). Cada escenario de las specs tiene su test; los bordes de un mismo requisito van en un `@pytest.mark.parametrize` con `pytest.param(..., id="...")` y el id indicado en cada tarea (evidencia: `docs/skills-mcp/evidencias/aplicacion/context7-c05b-pytest.md`). Comando de verificación, desde `backend/`: `python -m pytest` (un caso suelto: `python -m pytest -k <id>`). Los 33 tests de C-05a (`tests/unit/domain/appointments/test_validate_appointment.py`) son la red de seguridad de todo el change: cualquier rojo en ellos detiene el trabajo. Datos ficticios (Dra. A `dra-a`, Dr. B `dr-b`, Dr. C `dr-c`, Dr. D `dr-d`); lunes = 5 de octubre de 2026.

## 1. Red de seguridad y estructura (sin tests de comportamiento)

- [ ] 1.1 Safety net: correr `python -m pytest` y registrar en las notas del apply "baseline: 33 passed"; si algo falla, detenerse y reportarlo como falla previa
- [ ] 1.2 Crear `backend/app/core/__init__.py` (vacío, design D-T4) y `backend/tests/unit/core/__init__.py`; verificar que `python -m pytest` sigue recolectando 33 tests sin errores de importación

## 2. Zona horaria del consultorio (`clinic-timezone`, RN-GL-01)

Archivo: `backend/tests/unit/core/test_timezone.py`; código: `backend/app/core/timezone.py` (design D-T4).

- [ ] 2.1 RED: escribir `test_to_local_converts_utc_instant` con `pytest.param(..., id="conversion_simple_12utc_09local")` (escenario "Conversión simple"); verificar que falla porque `app.core.timezone` no existe
- [ ] 2.2 GREEN: crear `to_local(instant, timezone)` mínima; verificar que pasa
- [ ] 2.3 TRIANGULATE: agregar al mismo parametrize `id="cambia_fecha_0130utc_martes_es_2230_lunes"` (escenario "La conversión cambia la fecha") y `test_to_local_rejects_naive_instant` (escenario "Instante sin zona", `pytest.raises(ValueError)`); verificar suite en verde
- [ ] 2.4 RED → GREEN: `test_to_utc_converts_local_wall_clock` con `id="hora_local_0900_es_1200utc"` (escenario "Hora local a UTC", verifica `utcoffset() == timedelta(0)`) y `test_to_utc_rejects_aware_datetime` (escenario "Hora local que ya trae zona"); implementar `to_utc(local_naive, timezone)`; verificar suite en verde
- [ ] 2.5 RED → GREEN: `test_local_day_bounds` con `id="lunes_05_10_de_03utc_a_03utc"` (escenario "Límites del lunes…", incluye que la diferencia es de 24 horas) y `test_day_end_belongs_to_next_day` con `id="fin_lunes_es_inicio_martes"` (escenario "El fin del día pertenece al día siguiente"); implementar `local_day_bounds(day, timezone)`; verificar suite en verde
- [ ] 2.6 REFACTOR: revisar type hints y docstrings (citar RN-GL-01 y el supuesto SU-01 sin horario de verano); verificar que `timezone.py` solo importa librería estándar y suite en verde (33 + 7)

## 3. Refactor D-8 (parte 1): `validation.py` usa `app/core/timezone.py`

- [ ] 3.1 Reemplazar `_to_local` de `validation.py` por `to_local` de `app.core.timezone`, sin cambiar comportamiento (design D-8); verificar que los 33 tests de C-05a y los 7 de zona horaria siguen en verde y que `validation.py` ya no importa `ZoneInfo`

## 4. Tipos de salida y día sin turnos (`slot-availability`: "Franjas del día local completo")

Archivo: `backend/tests/unit/domain/appointments/test_compute_slots.py`; código: `compute_slots` en `backend/app/domain/appointments/slots.py` y `Slot` / `SlotStatus` en `types.py` (design D-1, D-T1).

- [ ] 4.1 RED: escribir `test_monday_without_appointments_returns_full_local_day` (escenario "Lunes sin turnos": 48 franjas, 16 `FREE` que empiezan de 09:00 a 12:30 y de 14:00 a 17:30, 32 `OUTSIDE_HOURS`, 0 `BUSY`); agregar a `helpers.py` lectores de franjas (por ejemplo `slot_at(slots, hour, minute)` y `count_by_status(slots)`); verificar que falla porque `compute_slots` no existe
- [ ] 4.2 GREEN: crear `SlotStatus`, `Slot` y `compute_slots` mínima (cursor por el día local con la grilla de D-2a, sin turnos ni licencias); verificar que pasa
- [ ] 4.3 TRIANGULATE: agregar `test_slots_are_contiguous_and_in_utc` (escenario "Inicio y fin de cada franja en UTC": primera 03:00-03:30 UTC del 5/10, franja 09:00 local = 12:00-12:30 UTC, última termina 03:00 UTC del 6/10, todas con `utcoffset() == timedelta(0)`, y cada `ends_at` igual al `starts_at` siguiente); verificar suite en verde
- [ ] 4.4 REFACTOR: exportar `compute_slots`, `Slot` y `SlotStatus` desde `appointments/__init__.py`; usar `local_day_bounds` y `to_utc` de `app.core.timezone`; verificar suite en verde

## 5. Grilla anclada al tramo y franja que no entra (RN-TU-02, RN-TU-03, design D-2/D-2a)

- [ ] 5.1 RED: escribir `test_grid_and_partial_remainder` parametrizado con `pytest.param(..., id="tramo_14_a_1545_resto_1530_outside")` (escenario "Tramo que no es múltiplo del slot": 14:00, 14:30 y 15:00 `FREE`; 15:30-15:45 `OUTSIDE_HOURS`; la siguiente empieza 15:45); verificar que falla si la grilla todavía no recorta
- [ ] 5.2 GREEN: recortar el resto del tramo al fin del tramo y reanudar la grilla fuera de horario desde ahí; verificar que pasa
- [ ] 5.3 TRIANGULATE: agregar `id="dr_b_tramo_0915_grilla_anclada"` (escenario "La grilla se cuenta desde el inicio del tramo"), `id="slot_45_ultimo_libre_1200_resto_1245"` (escenario "Slot de 45 minutos") e `id="tramos_contiguos_1315_anclas_distintas"` (escenario "Tramos contiguos con anclas distintas"); verificar suite en verde
- [ ] 5.4 REFACTOR: extraer la generación de franjas de un tramo y de un hueco a funciones privadas con nombre claro; verificar suite en verde

## 6. Ocupación por turnos `scheduled` (RN-TU-01, RN-TU-05, RN-TU-09, RN-TU-10, design D-5)

- [ ] 6.1 RED: escribir `test_occupancy` parametrizado con `pytest.param(..., id="scheduled_1000_busy_pegados_libres")` (escenario "Turno ocupado y turnos pegados": 10:00 `BUSY`, 09:30 y 10:30 `FREE`); verificar que falla
- [ ] 6.2 GREEN: marcar `BUSY` las franjas de tramo que se solapan `[inicio, fin)` con un `scheduled` del mismo profesional; verificar que pasa
- [ ] 6.3 TRIANGULATE: agregar `id="cancelado_libera_1000"` (escenario "Un turno cancelado libera la franja"), `id="completed_y_no_show_no_ocupan"` (escenario "Turnos `completed` o `no_show` no ocupan"), `id="turno_de_dr_b_no_ocupa_dra_a"` (escenario "El turno de otro profesional no ocupa"), `id="desalineado_1015_ocupa_1000_y_1030"` (escenario "Turno existente desalineado con la grilla") e `id="consecutivos_1000_y_1030_ambos_busy"` (escenario "Turnos consecutivos de un tratamiento largo"); verificar suite en verde
- [ ] 6.4 REFACTOR: revisar nombres; verificar suite en verde (la extracción compartida con `validation.py` va en el grupo 10)

## 7. Licencias (RN-HO-03, RN-TU-03, design D-3)

- [ ] 7.1 RED: escribir `test_time_off` parametrizado con `pytest.param(..., id="licencia_jueves_a_lunes_todo_outside")` (escenario "Día cubierto por una licencia": 48 franjas `OUTSIDE_HOURS`, ninguna `FREE`); verificar que falla
- [ ] 7.2 GREEN: si el día local está en una licencia inclusiva, todas las franjas `OUTSIDE_HOURS` con la misma grilla; verificar que pasa
- [ ] 7.3 TRIANGULATE: agregar `id="licencia_un_dia_lunes_5_y_lunes_12_libre"` (escenario "Licencia de un solo día y día siguiente": el 5 sin `FREE`, el 12 con 16 `FREE`); verificar suite en verde
- [ ] 7.4 REFACTOR: revisar duplicación con la regla de licencia de `validation.py` (se unifica en el grupo 10); verificar suite en verde

## 8. Precedencia de estados y conflictos (RN-HO-04, design D-T2)

- [ ] 8.1 RED: escribir `test_state_precedence` parametrizado con `pytest.param(..., id="licencia_prevalece_sobre_scheduled_1000")` (escenario "La licencia prevalece sobre un turno ya cargado") e `id="scheduled_1300_en_hueco_queda_outside"` (escenario "Turno `scheduled` fuera de tramo dentro del mismo día": 13:00 `OUTSIDE_HOURS`, 12:30 y 14:00 `FREE`); verificar que falla si la implementación marca `BUSY` fuera de tramo (si ya pasa por cómo quedó el grupo 6, forzar el rojo comentando temporalmente la condición de tramo y registrar la evidencia)
- [ ] 8.2 GREEN: asegurar la precedencia `OUTSIDE_HOURS` > `BUSY` > `FREE` en un único punto; verificar suite en verde
- [ ] 8.3 REFACTOR: documentar la precedencia en el docstring de `compute_slots` (y que no informa conflictos: C-07 / C-09); verificar suite en verde

## 9. Día sin tramos y día local por zona horaria (RN-GL-01, RN-TU-01, design D-2, D-9)

- [ ] 9.1 RED: escribir `test_day_without_working_hours` con `pytest.param(..., id="martes_sin_tramos_48_outside")` (escenario "Martes sin tramos"); verificar que falla o, si ya pasa por la grilla del grupo 4, registrarlo como caso de triangulación y forzar el rojo con un esperado incorrecto temporal
- [ ] 9.2 RED → GREEN: escribir `test_local_day_boundaries` parametrizado con `id="dr_c_turno_00utc_martes_es_2100_lunes_busy"` (escenario "Turno del lunes local que en UTC cae el martes": 21:00 `BUSY`, 20:30 `FREE`) e `id="dr_c_turno_03utc_martes_no_toca_lunes"` (escenario "Turno del martes a las 00:00 locales no pertenece al lunes"); ajustar la implementación si hace falta; verificar suite en verde
- [ ] 9.3 TRIANGULATE: agregar `id="dr_d_cruza_medianoche_busy_martes_0000"` (escenario "Turno que cruza la medianoche local": martes 00:00 `BUSY`, 00:30 `FREE`; lunes 23:30 `OUTSIDE_HOURS`); verificar suite en verde
- [ ] 9.4 REFACTOR: revisar que el filtrado de turnos no recorte por fecha UTC (design D-9); verificar suite en verde

## 10. Refactor D-8 (parte 2): helpers compartidos con `validation.py`

- [ ] 10.1 Safety net: correr `python -m pytest` y registrar el total en verde (33 de C-05a + los nuevos) antes de tocar `validation.py`
- [ ] 10.2 Extraer a `backend/app/domain/appointments/rules.py` los helpers compartidos (solapamiento semiabierto, ocupación por `scheduled` del mismo profesional, licencia inclusiva, minutos del día / anclaje de grilla al tramo) y hacer que `validation.py` y `slots.py` los usen, sin cambiar comportamiento (design D-8); correr la suite después de cada helper movido; verificar que los 33 tests de C-05a y todos los de C-05b siguen en verde
- [ ] 10.3 Verificar que ningún archivo de `app/domain/` importa FastAPI, SQLAlchemy, Celery ni Redis (búsqueda de imports) y que solo importan librería estándar y `app.core.timezone` (regla dura 2)

## 11. Anticipación mínima fuera del cálculo y entradas inválidas (RN-TU-12, DD-14, design D-4, D-6, D-6a)

- [ ] 11.1 RED → GREEN: escribir `test_slots_ignore_min_notice` con `pytest.param(..., id="1000_free_aunque_now_0800_y_validate_rechaza")` (escenario "Franja libre aunque falten menos de 6 horas": la franja 10:00 es `FREE` y `validate_appointment` con `now` = lunes 08:00 devuelve `INSUFFICIENT_NOTICE`); verificar suite en verde
- [ ] 11.2 RED: escribir `test_invalid_inputs_raise_value_error` parametrizado con `id="slot_minutes_cero"`, `id="slot_minutes_negativo"` (escenario "Duración de slot no positiva"), `id="day_texto"` e `id="day_datetime"` (escenario "Día que no es una fecha"); verificar que fallan
- [ ] 11.3 GREEN: validar entradas al inicio de `compute_slots` (chequear `datetime` antes que `date`, design D-6a); verificar suite en verde
- [ ] 11.4 REFACTOR: mensajes de error claros y docstring con el contrato; verificar suite en verde

## 12. Coherencia con `appointment-creation` (verificación de integración entre C-05a y C-05b)

- [ ] 12.1 Escribir `test_every_free_slot_is_accepted_by_validate_appointment` (escenario "Toda franja libre es aceptada al validar": turno `scheduled` 10:15-10:45 y `cancelled` 15:00-15:30, `now` = sábado 3/10 10:00; las 14 franjas `FREE` dan aceptado y `ends_at` igual al fin de la franja); verificar que pasa (si falla, es una divergencia real entre las dos funciones: corregir en `rules.py`, no en el test)
- [ ] 12.2 Verificación final: `python -m pytest` con todo en verde (33 de C-05a + 7 de `clinic-timezone` + los de `slot-availability`), ningún test omitido; registrar en las notas del apply la tabla de evidencia TDD (tarea, test, RED, GREEN, TRIANGULATE, REFACTOR) y dejar constancia de que el proyecto todavía no tiene typecheck ni lint configurados en `pyproject.toml` (regla dura 9: proponer su incorporación, no agregarlos en este change)
