# Proposal: completar-dominio-agenda (C-05c)

## Why

C-05 `domain-scheduling-core` ya tiene dos recortes archivados: C-05a (`validate_appointment`) y C-05b (`compute_slots` y `app/core/timezone.py`). Del alcance de C-05 en `CHANGES.md` siguen sin código tres reglas puras que C-07 (horarios) y C-08 (casos de uso de turnos) necesitan antes de tocar la base: la validación de los tramos y licencias de un profesional (RN-HO-02, restricción `starts_on <= ends_on` de `04_modelo_de_datos.md`), las transiciones de estado de un turno (RN-TU-05, RN-TU-07, US-010) y la regla de paciente inactivo (RN-PA-04). Hoy los tramos se tratan como "dato de confianza" (`compute_slots` y `validate_appointment` asumen tramos válidos) y no existe ningún lugar del dominio que diga si un turno puede cancelarse o marcarse como atendido.

Evidencia del código actual (`backend/app/domain/`):

- Solo existe el paquete `appointments/` (`types.py`, `rules.py`, `validation.py`, `slots.py`). No hay `schedules/` ni `patients/`.
- `rules.is_on_time_off` ya resuelve "la fecha cae en una licencia inclusiva" (RN-HO-03). El `is_date_in_time_off` que pide C-05 **ya está cubierto**: este change solo lo expone como API pública de `domain/schedules` sin duplicarlo.
- `AppointmentStatus` ya tiene los cuatro estados (`scheduled`, `cancelled`, `completed`, `no_show`), pero no hay reglas de cambio entre ellos.
- No hay ninguna validación de `WorkingHours` (`start_time < end_time`, superposición entre tramos, `weekday` 0-6) ni de `TimeOff` (`starts_on <= ends_on`).

## What Changes

- Nuevo paquete `backend/app/domain/schedules/` con:
  - `validate_working_hours(blocks)`: revisa un conjunto completo de tramos de un profesional y devuelve todos los problemas encontrados (tramo con `start_time >= end_time`, `weekday` fuera de 0-6, dos tramos del mismo día que se superponen). RN-HO-01, RN-HO-02.
  - `validate_time_off(leave)`: rechaza una licencia con `starts_on > ends_on` (constraint del modelo de datos).
  - `is_date_in_time_off(local_date, time_off)`: API pública; reutiliza el helper existente `is_on_time_off` (una sola fuente, sin cambio de comportamiento).
- Nueva función pura `validate_status_change` en `backend/app/domain/appointments/`: dado el estado actual, el estado pedido, el inicio del turno y `now` (inyectado), acepta o rechaza el cambio con un motivo. Cubre cancelar (RN-TU-05) y marcar `completed` / `no_show` solo en turnos `scheduled` ya iniciados (RN-TU-07, US-010); un `cancelled` no cambia más. La matriz completa de transiciones tiene puntos **pendientes de confirmar** (ver design).
- Nuevo paquete `backend/app/domain/patients/` con `check_patient_can_book(active)`: un paciente inactivo no puede recibir turnos nuevos (RN-PA-04). Es una función separada de `validate_appointment` para no modificar la capability `appointment-creation`; C-08 compone ambas.
- Errores de negocio como resultado (no excepciones), igual que C-05a; entradas mal tipadas (datetime sin zona) lanzan `ValueError`, igual que C-05a y C-05b.

No incluye: base de datos, API, pantallas, emails; detección de conflictos al cambiar horarios (RN-HO-04, es C-07); casos de uso `agendar` / `cancelar` / `reprogramar` / `marcar_atencion` (C-08); reprogramación como regla de dominio más allá de qué estados la admiten; **puertos de repositorios y repositorios en memoria** (se proponen como recorte C-05d, ver design §Partición).

## Capabilities

### New Capabilities

- `schedule-validation`: validez de los tramos de horario de un profesional (orden, día de la semana, no superposición) y de sus licencias (fechas ordenadas), y consulta "¿esta fecha local cae en una licencia?".
- `appointment-status-transitions`: qué cambios de estado de un turno se permiten y con qué motivo se rechazan los demás (cancelar, marcar atendido o ausente, estados terminales).
- `patient-booking-eligibility`: un paciente inactivo no puede recibir turnos nuevos.

### Modified Capabilities

Ninguna. `appointment-creation` y `slot-availability` no cambian de requisitos. Exponer `is_date_in_time_off` desde `domain/schedules` es un movimiento interno verificado con los 71 tests existentes.

## Impact

- Código nuevo: `backend/app/domain/schedules/` (`__init__.py`, `validation.py`, `types.py` para el resultado), `backend/app/domain/patients/` (`__init__.py`, `eligibility.py`), `backend/app/domain/appointments/transitions.py`.
- Código modificado (sin cambio de comportamiento): `backend/app/domain/appointments/rules.py` (el helper de licencias pasa a importarse desde `domain/schedules`), `backend/app/domain/appointments/__init__.py` y `types.py` (exportaciones y tipos de resultado de transiciones).
- Tests nuevos, puros: `backend/tests/unit/domain/schedules/`, `backend/tests/unit/domain/patients/`, `backend/tests/unit/domain/appointments/test_status_transitions.py`. Los 71 existentes son red de seguridad.
- Dependencias: ninguna nueva (solo librería estándar).
- Consumidores: C-07 (usa `validate_working_hours` y `validate_time_off` antes de guardar), C-08 (usa `validate_status_change` y `check_patient_can_book`).
- Documentación a actualizar por el usuario al archivar: entrada C-05 de `CHANGES.md` (nuevo recorte C-05c y, si se aprueba, C-05d) y las DD que surjan de las preguntas abiertas en `knowledge-base/09_decisiones_y_supuestos.md`.
- Governance: MEDIO (lógica de negocio pura). Las decisiones de dominio nuevas quedan pendientes de confirmación del usuario antes de implementar.
