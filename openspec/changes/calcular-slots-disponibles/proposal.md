# Proposal: calcular-slots-disponibles (C-05b)

## Why

La agenda (US-006, C-09) y el primer paso del Flujo 2 ("la UI pide la disponibilidad: `domain` calcula slots a partir de `working_hours`, `time_off` y turnos `scheduled`") necesitan saber, para un profesional y un día, qué franjas están libres, ocupadas o fuera de horario. Hoy solo existe `validate_appointment` (C-05a), que responde por un turno suelto, y no hay un único lugar que convierta entre UTC y la zona del consultorio (RN-GL-01). C-05b es el segundo recorte de C-05 `domain-scheduling-core` y desbloquea C-07, C-08 y C-09.

## What Changes

- Nueva función pura `compute_slots` en `backend/app/domain/appointments`: recibe el profesional (`professional_id`), el día local, sus tramos, sus licencias, los turnos existentes, `slot_minutes` y la zona horaria del consultorio, y devuelve la lista ordenada de franjas del día local completo, cada una con inicio y fin en UTC y un estado `FREE`, `BUSY` u `OUTSIDE_HOURS`.
- Nuevos tipos de salida `Slot` (inmutable) y `SlotStatus` (tres estados, los que nombra US-006; no hay cuarto estado).
- Nuevo módulo `backend/app/core/timezone.py`: conversión UTC <-> zona del consultorio e inicio y fin del día local en UTC (RN-GL-01), solo librería estándar.
- Refactor sin cambio de comportamiento de `validation.py` (C-05a): los helpers que comparten ambas funciones (solapamiento semiabierto, ocupación por `scheduled` del mismo profesional, licencia por días inclusivos, conversión a hora local) pasan a un módulo común y a `app/core/timezone.py`. Los 33 tests de C-05a son la red de seguridad y deben seguir en verde.
- Entradas inválidas (`slot_minutes <= 0`, `day` que no es una fecha) lanzan `ValueError`, como la convención de C-05a para datetimes sin zona.

No incluye: base de datos, red, pantallas, login ni emails; validación de tramos (RN-HO-02, los tramos se tratan como dato de confianza); transiciones de estado (RN-TU-05, RN-TU-07) más allá de que un `cancelled` libera la franja; regla de paciente inactivo (RN-PA-04); puertos de repositorios; anticipación mínima (la sigue resolviendo `validate_appointment`, RN-TU-12, DD-14); soporte de horario de verano (supuesto SU-01).

## Capabilities

### New Capabilities

- `slot-availability`: clasificación de las franjas del día local de un profesional como libres, ocupadas o fuera de horario, a partir de sus tramos, licencias y turnos `scheduled`, coherente con las reglas de `appointment-creation`.
- `clinic-timezone`: conversión entre instantes UTC y la hora local del consultorio, e inicio y fin del día local expresados en UTC (RN-GL-01).

### Modified Capabilities

Ninguna. `appointment-creation` no cambia de requisitos: el refactor de `validation.py` es interno y se verifica con sus 33 tests existentes.

## Impact

- Código nuevo: `backend/app/core/__init__.py`, `backend/app/core/timezone.py`, `compute_slots` y los tipos `Slot` / `SlotStatus` en `backend/app/domain/appointments/`.
- Código modificado (refactor sin cambio de comportamiento): `backend/app/domain/appointments/validation.py` y `__init__.py` (exportaciones).
- Tests nuevos: `backend/tests/unit/core/test_timezone.py` y `backend/tests/unit/domain/appointments/test_compute_slots.py`, puros, sin base ni red.
- Dependencias: ninguna nueva (solo `zoneinfo`, `dataclasses`, `enum`, `datetime` de la librería estándar).
- Documentación a actualizar por el usuario (fuera de este change): la firma de `compute_slots` en la entrada C-05 de `CHANGES.md` y posibles entradas DD/SU en `knowledge-base/09_decisiones_y_supuestos.md`.
- Consumidores futuros: C-08 (casos de uso), C-09 (vista de agenda) y C-07 (la licencia bloquea disponibilidad).
- Governance: MEDIO (lógica de negocio pura).
