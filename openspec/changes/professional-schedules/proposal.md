# Proposal: professional-schedules (C-07)

> **Gobernanza MEDIA.** Las decisiones de dominio P-1 a P-11 de `design.md` están **CONFIRMADAS** por la usuaria (todas las opciones recomendadas). Las specs coinciden con esas opciones.

## Why

Hoy los horarios de trabajo y las licencias de cada profesional solo se pueden cargar con el seed o tocando la base: el dominio (C-05c), los repositorios en memoria y PostgreSQL (C-05d, C-02) y la agenda que los consume (C-08) ya existen, pero no hay casos de uso, endpoints ni pantalla para administrarlos (US-004, US-005, Flujo 5). Sin eso el administrador no puede cambiar la disponibilidad real, y nadie se entera de los turnos que quedan afuera cuando cambia un horario o se carga una licencia (RN-HO-04). C-04 dejó además para este change la edición de la ficha del profesional (nombre a mostrar y matrícula, DD-60). C-09 (vistas de agenda) espera a C-07.

## What Changes

- **Regla pura de conflictos (RN-HO-04, Flujo 5 paso 3)** en `app/domain/schedules/`: dados los tramos, las licencias, los turnos y el momento actual, devuelve los turnos `scheduled` que todavía no empezaron y que ya no entran completos en un tramo o caen en un día de licencia. No cancela ni modifica nada.
- **Casos de uso** en `app/application/professionals.py` (sin FastAPI ni SQLAlchemy):
  - Listar fichas y ver una ficha (el odontólogo, solo la propia, RN-AU-04).
  - Editar la ficha: nombre a mostrar y matrícula (solo administración; DD-60).
  - Leer y **reemplazar la semana completa** de tramos de un profesional, validada con `validate_working_hours` (RN-HO-01, RN-HO-02, DD-26 a DD-30); devuelve los turnos en conflicto con el horario nuevo.
  - Listar y **cargar licencias** validadas con `validate_time_off` (DD-28), con motivo opcional (US-005); devuelve los turnos en conflicto.
  - **Borrar una licencia** cargada por error (P-4, recomendada; sin respaldo en la KB).
  - **Consultar los conflictos actuales** de un profesional (calculados en el momento, sin marca guardada; P-1).
- **API** bajo `/api/v1/professionals` con JWT y `require_role`: listado, detalle, edición de ficha, horarios (`GET`/`PUT`), licencias (`GET`/`POST`/`DELETE`) y conflictos (`GET`). Solo el administrador escribe (DD-48); recepción lee todo; el odontólogo lee solo lo propio (DD-53). Cada endpoint con su test de permisos por rol.
- **Repositorios**: escritura de la ficha en `ProfessionalRepository` y borrado de licencia en `TimeOffRepository`, en memoria y PostgreSQL, con la batería de contrato extendida. Sin migraciones (el esquema de C-02 alcanza).
- **Errores nuevos** en el modelo uniforme: `INVALID_WORKING_HOURS` y `INVALID_TIME_OFF` (400), `TIME_OFF_NOT_FOUND` (404).
- **Pantalla `/profesionales`** (P-9, recomendada según CHANGES.md): listado, edición de ficha, editor de la semana con varios tramos por día, carga y borrado de licencias, y lista de turnos en conflicto tras guardar. Solo el administrador edita; recepción y odontólogo la ven en modo lectura según la matriz.
- No cambia el contrato de C-08: agendar, reprogramar y franjas siguen leyendo horarios y licencias de los mismos repositorios en cada pedido, así que los cambios se reflejan de inmediato (US-004).

## Capabilities

### New Capabilities
- `schedule-conflicts`: regla pura que detecta los turnos `scheduled` futuros que quedan fuera del horario o dentro de una licencia (RN-HO-04).
- `professional-schedule-use-cases`: casos de uso de ficha, horarios semanales, licencias y conflictos, con validación de dominio y alcance por rol.
- `professional-schedule-api`: endpoints `/api/v1/professionals/...` de ficha, horarios, licencias y conflictos, su formato y la matriz de permisos por rol.
- `frontend-professional-schedules`: pantalla `/profesionales` (sujeta a P-9).

### Modified Capabilities
- `professional-repository`: se agrega la edición de nombre a mostrar y matrícula de una ficha.
- `schedule-repository`: se agrega borrar una licencia de un profesional (sujeto a P-4).
- `error-model`: la tabla de códigos suma `INVALID_WORKING_HOURS`, `INVALID_TIME_OFF` (400) y `TIME_OFF_NOT_FOUND` (404).

## Impact

- **Código nuevo**: `app/domain/schedules/conflicts.py` (+ errores), `app/application/professionals.py`, `app/api/professionals.py`, inclusión en `app/api/router.py`, fábrica en `app/api/dependencies.py`; métodos nuevos en `app/infrastructure/in_memory/{professionals,schedules}.py` y `app/infrastructure/db/repositories/{professionals,schedules}.py`; `STATUS_BY_CODE` en `app/api/errors.py`.
- **Frontend** (si P-9 = A): `frontend/src/pages/ProfessionalsPage.tsx`, `frontend/src/api/professionals.ts`, componentes en `frontend/src/professionals/`, ruta y enlace en `App.tsx`.
- **Tests**: dominio puro, casos de uso con repositorios en memoria y reloj fijo, API con tabla de permisos por rol, batería de contrato (memoria y PostgreSQL), integración con el seed, Vitest.
- **Sin** migraciones, variables de entorno ni dependencias nuevas. Regla dura 6: la no superposición de turnos no se toca; los tests de C-08 siguen como red de seguridad y se agrega el caso "cambiar el horario no deja agendar encima de un turno existente".
- **Roadmap**: habilita C-09 (vistas) y aporta a C-10 el endpoint de conflictos para su indicador (RN-HO-04).
