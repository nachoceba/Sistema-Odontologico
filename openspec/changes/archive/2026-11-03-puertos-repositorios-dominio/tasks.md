# Tasks

Strict TDD: en cada grupo el orden es RED (test de contrato que falla) → GREEN (código mínimo) → TRIANGULATE (más casos con otros datos hasta cubrir todos los escenarios del requisito) → REFACTOR (tests siguen en verde). Cada escenario de las specs tiene su test en `backend/tests/contract/`; los bordes de un mismo requisito van en `@pytest.mark.parametrize` con `pytest.param(..., id="...")`. Los tests usan solo el puerto (design D-7). Comandos, desde `backend/`: `python -m pytest` y `mypy --strict app/`. Los 131 tests existentes son la red de seguridad: cualquier rojo en ellos detiene el trabajo. Datos ficticios: Dra. A `dra-a`, Dr. B `dr-b`, Juan Pérez `pac-1`, Ana Gómez `pac-2`, recepción `rec-1`, lunes 5 de octubre de 2026 en hora local.

## 0. Confirmación previa

- [x] 0.1 Confirmar con el usuario P-1 a P-6 de `design.md`; si alguna cambia, actualizar con `/opsx:update` antes de seguir. Verificación: cada P-n figura como confirmada en `design.md` y registrada como DD-31 a DD-36 en `knowledge-base/09_decisiones_y_supuestos.md` (confirmadas por el usuario: las seis recomendaciones tal cual)

## 1. Red de seguridad y estructura

- [x] 1.1 Safety net: correr `python -m pytest` y `mypy --strict app/`; registrar "baseline: 131 passed, mypy limpio"; si algo falla, detenerse y reportarlo como falla previa
- [x] 1.2 Crear `app/domain/settings/__init__.py`, `app/infrastructure/__init__.py`, `app/infrastructure/in_memory/__init__.py`, `tests/contract/__init__.py` y `tests/contract/conftest.py` con las fixtures parametrizadas por fábrica (design D-7, solo `id="in_memory"`); verificar que `python -m pytest` sigue recolectando 131 tests sin errores de importación
- [x] 1.3 RED → GREEN: `tests/contract/test_import_order.py` que importa en un intérprete nuevo (`subprocess`, `sys.executable -c`) cada uno de `app.domain.schedules`, `app.domain.appointments`, `app.domain.patients`, `app.domain.settings` y `app.infrastructure.in_memory` como primer import (design D-2); verificar en verde con los paquetes vacíos y repetirlo al final de cada grupo

## 2. Tipos y errores de turnos (`appointment-repository`: "Conversión al dato que consumen las reglas de agenda")

Archivos: `app/domain/appointments/types.py`, `app/domain/appointments/errors.py` (design D-3; forma del error: DD-32).

- [x] 2.1 RED → GREEN: test de `Appointment.to_existing()` (conserva profesional, inicio, fin y estado) y test de que `NewAppointment` y `Appointment` son inmutables; crear los tipos; verificar en verde
- [x] 2.2 RED → GREEN: tests de los errores `SLOT_TAKEN` (lleva profesional e inicio pedidos) y `APPOINTMENT_NOT_FOUND` (lleva el id), según la forma confirmada en P-2; crear `errors.py` y exportarlo desde `app/domain/appointments/__init__.py` al final; verificar en verde y los 131 tests previos en verde

## 3. Puerto y repositorio en memoria de turnos: guardar y buscar

Archivos: `app/domain/appointments/ports.py` (`Protocol`, imports bajo `TYPE_CHECKING`, D-1/D-2), `app/infrastructure/in_memory/appointments.py`, `tests/contract/test_appointment_repository.py`.

- [x] 3.1 RED → GREEN: escenario "La misma batería corre contra cada implementación" (la fixture devuelve un repo vacío por test y la asignación anotada `repo: AppointmentRepository = ...` pasa `mypy --strict`); verificar en verde
- [x] 3.2 RED → GREEN → TRIANGULATE: "Guardar y recuperar un turno", "Dos turnos guardados reciben identificadores distintos" y el mismo instante expresado en otra zona se recupera igual; verificar en verde
- [x] 3.3 RED → GREEN: parametrizado de `ValueError` con ids `inicio_sin_zona`, `inicio_igual_fin`, `inicio_posterior_fin`; verificar que el repo sigue vacío; en verde
- [x] 3.4 RED → GREEN: "Turno existente" y "Identificador inexistente" (DD-33); verificar en verde

## 4. No solapamiento al guardar (regla dura 6, RN-TU-01)

Mismo archivo de test; implementación con `overlaps_scheduled` de `rules.py` (única fuente, D-5).

- [x] 4.1 RED → GREEN: "Segundo turno superpuesto del mismo profesional" (error `SLOT_TAKEN` con profesional e inicio, listado con un único turno); verificar en verde
- [x] 4.2 TRIANGULATE: parametrizado de rechazo con ids `mismo_horario`, `contiene_a_otro`, `cruza_medianoche`; parametrizado de aceptación con ids `pegado_antes`, `pegado_despues`, `otro_profesional`, `mismo_paciente_otro_profesional`; verificar en verde
- [x] 4.3 RED → GREEN: "Un turno cancelado no bloquea" y "Turnos atendidos o ausentes no bloquean" (se preparan con `change_status`; si aún no existe, implementar el mínimo de 5.1 primero dentro de este paso); verificar en verde
- [x] 4.4 REFACTOR: extraer la verificación "validar y recién después escribir" a un único helper privado del repo en memoria; verificar `grep` de que no hay otra comparación de rangos fuera de `rules.py`; tests en verde

## 5. Cambiar estado y reprogramar

- [x] 5.1 RED → GREEN → TRIANGULATE: "Cancelar con motivo libera el horario" y "Marcar atendido"; verificar en verde
- [x] 5.2 RED → GREEN: "Volver a scheduled sobre un horario ya tomado" (sigue `cancelled`) y "Cambiar el estado de un turno inexistente" (`APPOINTMENT_NOT_FOUND`); verificar en verde
- [x] 5.3 RED → GREEN → TRIANGULATE: "Reprogramar a un horario libre", "Reprogramar sobre un turno ocupado no cambia el original", "Reprogramar solapando su propio horario anterior", "Reprogramar un turno inexistente", y `ValueError` con fin no posterior al inicio; verificar en verde

## 6. Listados

- [x] 6.1 RED → GREEN: "Turnos del día local de un profesional" usando `local_day_bounds` para el rango (DD-31, DD-35); verificar en verde
- [x] 6.2 TRIANGULATE: "Límites semiabiertos del rango", "Turno que cruza la medianoche aparece en ambos días", "Turnos futuros sin límite superior", "Profesional sin turnos" y parametrizado `ValueError` con ids `desde_sin_zona`, `desde_igual_hasta`, `desde_posterior_hasta`; verificar en verde
- [x] 6.3 RED → GREEN: "Turnos futuros de un paciente con varios profesionales" y "Paciente sin turnos"; REFACTOR del filtro de rango compartido entre ambos listados; verificar en verde
- [x] 6.4 RED → GREEN: "El listado alimenta la validación de un turno nuevo" (listado convertido con `to_existing` → `validate_appointment` rechaza `OVERLAPS_EXISTING`); verificar en verde, `mypy --strict app/` limpio y test de import en verde

## 7. Horarios y licencias (`schedule-repository`)

Archivos: `app/domain/schedules/types.py` (`TimeOffEntry`), `app/domain/schedules/ports.py`, `app/infrastructure/in_memory/schedules.py`, `tests/contract/test_schedule_repository.py`.

- [x] 7.1 RED → GREEN: "La batería corre contra cada implementación" para ambos puertos (asignaciones anotadas verificadas por mypy); verificar en verde
- [x] 7.2 RED → GREEN → TRIANGULATE: "Reemplazar y leer la semana de un profesional", "Un nuevo reemplazo descarta los tramos anteriores", "Reemplazar un profesional no toca a otro", "Profesional sin horario cargado"; verificar en verde
- [x] 7.3 RED → GREEN → TRIANGULATE: "Agregar y listar licencias con motivo", "Licencias de otro profesional no aparecen", "Licencias superpuestas se guardan las dos", "Licencia con fin anterior al inicio" (`ValueError`, sin cambios); verificar en verde
- [x] 7.4 RED → GREEN: "Las licencias guardadas bloquean la disponibilidad" (tramos + `to_time_off` → `compute_slots`, todo `OUTSIDE_HOURS`); verificar en verde, los 131 tests previos en verde y el test de import en verde (schedules no debe importar `app.domain.appointments` en tiempo de ejecución desde `ports.py`)

## 8. Pacientes (`patient-repository`)

Archivos: `app/domain/patients/types.py` (`Patient`), `app/domain/patients/ports.py`, `app/infrastructure/in_memory/patients.py` (la fábrica acepta pacientes iniciales, D-7), `tests/contract/test_patient_repository.py`. Alcance según DD-34.

- [x] 8.1 RED → GREEN → TRIANGULATE: "La batería corre contra cada implementación", "Paciente activo", "Paciente inexistente"; verificar en verde
- [x] 8.2 RED → GREEN: "Paciente inactivo, listo para la regla RN-PA-04" (`active` es `bool` y `check_patient_can_book` rechaza `PATIENT_INACTIVE`); verificar en verde

## 9. Configuración del consultorio (`clinic-settings-repository`)

Archivos: `app/domain/settings/types.py` (`ClinicSettings`), `app/domain/settings/ports.py`, `app/infrastructure/in_memory/settings.py`, `tests/contract/test_clinic_settings_repository.py`.

- [x] 9.1 RED → GREEN → TRIANGULATE: "Valores por defecto" y "Valores configurados"; verificar en verde
- [x] 9.2 RED → GREEN: "La configuración leída cambia las franjas calculadas" (slot de 20 → tres franjas `FREE` en 09:00–10:00); verificar en verde

## 10. Cierre e integración

- [x] 10.1 Verificación final desde `backend/`: `python -m pytest` (131 previos + los nuevos, todos en verde), `mypy --strict app/` limpio, test de import en verde, y `grep -rE "fastapi|sqlalchemy|celery|redis" app/domain` sin resultados (regla dura 2); registrar los números en este archivo. Resultado: 199 passed (131 previos + 68 nuevos), mypy --strict limpio (30 archivos), sin imports de fastapi/sqlalchemy/celery/redis en domain/ ni infrastructure/. Baseline previo: 131 passed, mypy limpio.
- [x] 10.2 Actualizar la entrada C-05 de `CHANGES.md` (C-05d archivado, C-05 completo) y registrar la lista "Fuera de C-05d" de `design.md` en las entradas C-02, C-06, C-08 y C-12 correspondientes; verificar con `openspec validate puertos-repositorios-dominio --strict`
