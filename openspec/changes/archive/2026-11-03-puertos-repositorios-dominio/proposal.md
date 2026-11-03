# Proposal: puertos-repositorios-dominio (C-05d)

## Why

C-05 `domain-scheduling-core` tiene tres recortes archivados (C-05a, C-05b, C-05c): todas las reglas puras de la agenda existen, pero reciben sus datos ya cargados en listas (`working_hours`, `time_off`, `existing_appointments`) y nadie define todavía **de dónde salen esos datos ni cómo se guardan los turnos**. El único punto del alcance de C-05 sin código es "Puertos (interfaces) de repositorios + repos en memoria para tests" (`CHANGES.md`, entrada C-05). C-07 (horarios y licencias), C-08 (casos de uso de turnos), C-06 (pacientes) y C-09 (vistas de agenda) necesitan esas interfaces para escribir sus casos de uso y sus tests sin levantar PostgreSQL, y C-08 necesita además que un repositorio de prueba se comporte como el constraint de exclusión de la base (regla dura 6). Este change cierra C-05.

Evidencia del código actual (`backend/app/`):

- Solo existen `domain/` (`appointments`, `schedules`, `patients`) y `core/timezone.py`. No hay `application/` ni `infrastructure/`.
- Los tipos de dominio no tienen identidad: `ExistingAppointment` no lleva `id` ni paciente, `TimeOff` no lleva `id` ni motivo. Un caso de uso no puede cancelar "el turno X" ni listar licencias con su motivo (US-005) con los tipos actuales.
- La regla de solapamiento ya tiene una sola fuente (`rules.overlaps_scheduled`, DD-20) que el repositorio en memoria puede reutilizar.

## What Changes

- **Puertos** (interfaces puras, solo librería estándar, sin FastAPI, SQLAlchemy, Celery ni Redis) dentro de `domain/`:
  - Repositorio de turnos: guardar un turno nuevo, buscar uno por identificador, cambiar su estado (cancelar con motivo, atendido, ausente), reprogramarlo en una sola operación y listar los turnos de un profesional o de un paciente en un rango de tiempo.
  - Repositorio de horarios: leer los tramos de un profesional y reemplazar el conjunto completo.
  - Repositorio de licencias: listar las licencias de un profesional (con motivo) y agregar una.
  - Repositorio de pacientes (mínimo): buscar un paciente por identificador para saber si existe y si está activo (RN-PA-04).
  - Configuración del consultorio (solo lectura): duración del slot, zona horaria y anticipación mínima.
- **Tipos con identidad** que devuelven los puertos: turno guardado (con id, paciente, estado y motivo de cancelación), licencia guardada (con id y motivo) y paciente; con conversión a los tipos que ya consumen `validate_appointment` y `compute_slots`, sin cambiarlos.
- **Error de dominio de solapamiento**: guardar o reprogramar un turno `scheduled` que se superpone con otro `scheduled` del mismo profesional se rechaza con un error de dominio, el mismo que C-08 traducirá desde el constraint de exclusión ("el slot acaba de ocuparse").
- **Repositorios en memoria** que implementan cada puerto y reproducen las garantías de la base: no solapamiento (`WHERE status = 'scheduled'`, rango semiabierto), `starts_at < ends_at`, fechas con zona.
- **Tests de contrato compartidos**: una sola batería por puerto que hoy corre contra el repositorio en memoria y que C-02/C-08 podrán correr contra el repositorio SQLAlchemy agregando una fábrica, sin reescribir escenarios.

Formas de búsqueda, de error, de retorno y la existencia de una "unidad de trabajo" quedaron **confirmadas por el usuario** (P-1 a P-6 en `design.md`, registradas como DD-31 a DD-36 en la KB).

No incluye: base de datos, modelos SQLAlchemy, migraciones ni el repositorio SQLAlchemy (C-02/C-08); casos de uso (`agendar_turno`, etc., C-08); detección de conflictos RN-HO-04 (C-07); búsqueda, alta y unicidad de documento de pacientes (C-06); repositorio de profesionales y de usuarios (C-04/C-07); notificaciones por email (C-11/C-12); borrar o editar licencias (sin respaldo en la KB).

## Capabilities

### New Capabilities

- `appointment-repository`: cómo se guardan, buscan, cambian de estado, reprograman y listan los turnos, incluida la garantía de que un profesional nunca queda con dos turnos `scheduled` superpuestos.
- `schedule-repository`: cómo se leen y reemplazan los tramos de horario de un profesional y cómo se listan y agregan sus licencias.
- `patient-repository`: cómo se consulta si un paciente existe y está activo para poder darle turnos.
- `clinic-settings-repository`: cómo se leen la duración del slot, la zona horaria y la anticipación mínima del consultorio.

### Modified Capabilities

Ninguna. `appointment-creation`, `slot-availability`, `schedule-validation`, `appointment-status-transitions`, `patient-booking-eligibility` y `clinic-timezone` no cambian de requisitos.

## Impact

- Código nuevo (en la implementación posterior): `backend/app/domain/appointments/ports.py`, `backend/app/domain/appointments/errors.py`, `backend/app/domain/schedules/ports.py`, `backend/app/domain/patients/ports.py`, `backend/app/domain/settings/` (puerto y tipo de configuración), tipos nuevos en `appointments/types.py` y `patients/`; `backend/app/infrastructure/in_memory/` con los cuatro repositorios.
- Tests nuevos: `backend/tests/contract/` (batería compartida con fixture parametrizada por fábrica) y un test de importación que protege contra el ciclo `appointments` ↔ `schedules`.
- Sin dependencias externas nuevas. `mypy --strict app/` debe seguir limpio y los 131 tests existentes en verde.
- Desbloquea C-07, C-08 y C-09 (dependen de "C-05" completo) y deja la batería de contrato lista para el repositorio SQLAlchemy.
