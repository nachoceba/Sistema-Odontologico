# Verify: crear-turno-sin-solapamientos

Fecha: 2026-09-30. Change: `openspec/changes/crear-turno-sin-solapamientos/`.

Esta instalación de OpenSpec no ofrece la fase de verificación como comando propio (los comandos disponibles son explore, propose, apply, archive, sync y update). Se ejecutó la suite de tests a mano y se documenta el resultado, como indica la consigna.

## 1. Resultado de los tests

Comando (desde `backend/`, con el entorno virtual de Python 3.13.15):

```
.venv/Scripts/python.exe -m pytest -q
```

Resultado: **33 passed in 0.07s**, 0 fallas, 0 omitidos. No hay nada en rojo.

## 2. Chequeos de salud

| Chequeo | Comando o método | Resultado |
|---|---|---|
| Artefactos válidos | `openspec validate crear-turno-sin-solapamientos --strict` | Válido |
| Tareas completas | `openspec instructions apply ... --json` | 32 de 32, 0 pendientes (`all_done`) |
| Escenarios del spec | conteo de `#### Scenario` en `spec.md` | 20 |
| Dominio puro | revisión de los imports de `backend/app/domain` | Solo biblioteca estándar (`datetime`, `zoneinfo`, `dataclasses`, `enum`, `collections.abc`); sin FastAPI, SQLAlchemy, Celery ni Redis; sin leer el reloj del sistema |
| Entorno | `python --version` del entorno virtual | 3.13.15 (el diseño pide 3.12 o superior) |

No hay chequeo de endpoint de salud porque este change no tiene API: es solo lógica de dominio.

## 3. Cobertura de escenarios

Cada uno de los 20 escenarios del spec tiene un test automatizado (se comprobó que cada función de test existe en `tests/unit/domain/appointments/test_validate_appointment.py`).

| # | Escenario | Test |
|---|---|---|
| 1 | Turno libre dentro del horario (feliz) | `test_accepts_free_slot_and_computes_ends_at` |
| 2 | Un instante en UTC se evalúa en hora local | `test_utc_instant_is_evaluated_in_clinic_local_time` |
| 3 | Anticipación insuficiente | `test_rejects_insufficient_notice` |
| 4 | Anticipación exacta de 6 h (límite inclusivo) | `test_accepts_exactly_min_notice` |
| 5 | Turno en el pasado | `test_rejects_start_in_the_past` |
| 6 | Anticipación configurada en 12 h | `test_rejects_with_configured_12h_notice` |
| 7 | Inicio fuera de la grilla | `test_rejects_off_grid_start` |
| 8 | Grilla contada desde el inicio del tramo | `test_grid_is_anchored_to_block_start` |
| 9 | Antes del inicio del horario | `test_rejects_before_working_hours` |
| 10 | Hueco entre dos tramos | `test_rejects_gap_between_blocks` |
| 11 | Último slot del tramo | `test_accepts_last_slot_ending_at_block_end` |
| 12 | Día sin horario | `test_rejects_day_without_working_hours` |
| 13 | Último día de una licencia | `test_rejects_on_last_day_of_time_off` |
| 14 | Pisa a otro turno del mismo profesional (error de negocio) | `test_rejects_overlap_with_same_professional` |
| 15 | Empieza justo cuando termina otro (borde) | `test_accepts_back_to_back_after_existing` |
| 16 | Termina justo cuando empieza otro | `test_accepts_back_to_back_before_existing` |
| 17 | Mismo horario con otro profesional | `test_accepts_same_time_other_professional` |
| 18 | Turno cancelado no ocupa el horario | `test_cancelled_appointment_does_not_block` |
| 19 | Anticipación y grilla a la vez: gana anticipación | `test_notice_wins_over_off_grid` |
| 20 | Licencia y solapamiento a la vez: gana licencia | `test_time_off_wins_over_overlap` |

Además hay 13 tests de refuerzo (fecha sin zona horaria, turnos `completed` y `no_show`, otros tramos, entre otros).

## 4. Prueba de que los tests detectan errores (mutación manual)

Para comprobar que los tests no pasan "por casualidad", se rompió el código a propósito en los dos bordes más delicados y se restauró después:

| Cambio introducido | Resultado de pytest |
|---|---|
| Anticipación: de `<` a `<=` (rechazar justo las 6 h) | 1 test falló: `test_accepts_exactly_min_notice` |
| Solapamiento: de rangos semiabiertos a cerrados (turnos pegados se pisan) | 2 tests fallaron: los de "empieza justo cuando termina otro" y su espejo |
| Código restaurado | 33 passed; sin diferencias respecto del original |

## 5. Límites de esta verificación

- No se midió cobertura de líneas con una herramienta; la cobertura se verificó por escenario.
- No hay integración continua ni base de datos: la garantía contra la carrera entre dos recepcionistas pertenece al constraint de C-02 y no se prueba acá.
- La mutación fue manual y solo sobre dos reglas.
- Algunos tests de refuerzo pasaron en verde desde el primer intento (lo registró la fase Apply). No se considera un defecto, pero se deja constancia.

## 6. Conclusión

Todos los escenarios del spec tienen test y la suite está en verde, así que **se puede pasar a Archive**.
