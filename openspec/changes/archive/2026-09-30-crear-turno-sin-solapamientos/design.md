# Design: crear-turno-sin-solapamientos

## Context

- Motivación y alcance: ver `proposal.md` (Why, Non-goals). Requisitos y escenarios: ver `specs/appointment-creation/spec.md`.
- Estado del repo: no existe `backend/` ni ningún archivo Python ni tests (ver `docs/opsx/explore-crear-turno-sin-solapamientos.md` §2). Todo el código es nuevo.
- En el roadmap, C-05 depende de C-01 (`foundation-setup`), que todavía no se hizo. C-01 completo (Docker, FastAPI, Celery, frontend) no hace falta para una función pura.
- Restricciones duras (`AGENTS.md`): type hints en todo el código Python (regla 1); `domain/` sin FastAPI, SQLAlchemy, Celery ni Redis, sin I/O (regla 2); todo cambio de agenda incluye un test de no superposición (regla 6).
- Datos del modelo (`04_modelo_de_datos.md`): `working_hours` (`weekday`, `start_time`, `end_time`, hora local), `time_off` (`starts_on`, `ends_on`, fechas locales inclusivas), `appointments` (`starts_at`, `ends_at` en UTC, `status`), `clinic_settings` (`slot_minutes`, `timezone`, y desde este change `min_notice_hours`).

## Goals / Non-Goals

**Goals:**
- Una función pura y determinista que valide la creación de un turno y devuelva un resultado tipado.
- Esqueleto mínimo de `backend/` que C-01 pueda extender sin rehacer.
- Cada escenario del spec verificado por al menos un test unitario con pytest.

**Non-Goals (de diseño):**
- No se define el caso de uso de aplicación (C-08), ni cómo se cargan los datos desde la base (repositorios), ni el mapeo del resultado a errores HTTP (`app/core/errors.py`, C-01/C-08).
- No se modela `compute_slots` ni transiciones de estado; el diseño deja la lógica de "grilla" y "tramo" en funciones auxiliares reutilizables por `compute_slots` más adelante, pero sin exponerlas como API pública todavía.
- No se soportan horas inexistentes o repetidas por horario de verano (la zona por defecto no tiene DST hoy).

## Decisions

### D1. Firma de la función

Módulo `backend/app/domain/appointments/validation.py`, re-exportado desde `backend/app/domain/appointments/__init__.py`.

```python
def validate_appointment(
    *,
    professional_id: str,
    starts_at: datetime,                       # aware, UTC
    now: datetime,                             # aware, UTC (inyectado)
    working_hours: Sequence[WorkingHours],     # tramos del profesional
    time_off: Sequence[TimeOff],               # licencias del profesional
    existing_appointments: Sequence[ExistingAppointment],
    slot_minutes: int = 30,
    timezone: str = "America/Argentina/Buenos_Aires",
    min_notice_hours: int = 6,
) -> ValidationResult: ...
```

- Argumentos solo por nombre (`*`) para evitar confundir `starts_at` y `now`.
- `now` se inyecta: el dominio nunca lee el reloj (testeable y determinista).
- `min_notice_hours`, `slot_minutes` y `timezone` son parámetros con los defaults de `clinic_settings`; el caso de uso (C-08) los leerá de la base.
- `existing_appointments` puede traer turnos de varios profesionales; la función filtra por `professional_id` y `status == SCHEDULED`. `working_hours` y `time_off` se asumen ya filtrados del profesional (los carga el caso de uso por profesional); se documenta en el docstring.
- `professional_id` es `str` (un uuid serializado). Alternativa: `uuid.UUID`; se descarta para no forzar conversiones en tests. C-02/C-08 pueden cambiarlo a un alias `ProfessionalId` sin tocar la lógica.

### D2. Tipos (en `backend/app/domain/appointments/types.py`)

Todos `@dataclass(frozen=True)` o `enum.Enum` de la librería estándar, sin ORM:

- `AppointmentStatus(Enum)`: `SCHEDULED`, `CANCELLED`, `COMPLETED`, `NO_SHOW` (espejo del enum de la base).
- `WorkingHours`: `weekday: int` (0 = lunes ... 6 = domingo), `start_time: time`, `end_time: time` (hora local).
- `TimeOff`: `starts_on: date`, `ends_on: date` (fechas locales, inclusivas).
- `ExistingAppointment`: `professional_id: str`, `starts_at: datetime`, `ends_at: datetime`, `status: AppointmentStatus`.
- `RejectionReason(Enum)`: `INSUFFICIENT_NOTICE`, `OFF_GRID`, `OUTSIDE_WORKING_HOURS`, `PROFESSIONAL_TIME_OFF`, `OVERLAPS_EXISTING`.
- `ValidationResult`: `accepted: bool`, `ends_at: datetime | None`, `reason: RejectionReason | None`, con constructores `ValidationResult.accept(ends_at)` y `ValidationResult.reject(reason)`. Invariante: aceptado ⇔ `ends_at` presente y `reason` ausente.

Alternativa considerada: dos clases `Accepted` / `Rejected` (unión discriminada). Se elige una sola dataclass por simplicidad de asserts en tests y de lectura para el equipo; la diferencia no cambia el comportamiento.

### D3. Resultado en vez de excepciones

El rechazo por regla de negocio es un resultado, no una excepción: es un caso esperado y frecuente, y el caso de uso (C-08) decide si lo convierte en el error tipado de `app/core/errors.py`. Un `datetime` sin zona (`starts_at` o `now` "naive") es un error de programación, no de negocio: se lanza `ValueError`. Esto no contradice el spec (que habla de motivos de negocio).

### D4. Orden fijo de evaluación y un solo motivo

Se evalúa en este orden y se devuelve el primer fallo:

1. **Anticipación** (RN-TU-12, cubre RN-TU-04): `starts_at < now + timedelta(hours=min_notice_hours)` → `INSUFFICIENT_NOTICE`. Igualdad se acepta.
2. **Grilla** (RN-TU-02): se pasa `starts_at` a hora local; se buscan los tramos del `weekday` local que contienen el inicio (`start_time <= inicio_local < end_time`). Si hay uno y `(inicio_local - start_time)` no es múltiplo de `slot_minutes` → `OFF_GRID`. Si el inicio no cae en ningún tramo, no se decide acá: pasa a la regla 3.
3. **Horario de trabajo** (RN-TU-03): `ends_at = starts_at + slot_minutes`. Debe existir un tramo del `weekday` local con `start_time <= inicio_local` y `fin_local <= end_time` → si no, `OUTSIDE_WORKING_HOURS`.
4. **Licencia** (RN-TU-03, RN-HO-03): fecha local del inicio dentro de algún `[starts_on, ends_on]` (inclusivo) → `PROFESSIONAL_TIME_OFF`.
5. **Solapamiento** (RN-TU-01): algún turno del mismo `professional_id` con `status == SCHEDULED` y `nuevo.start < existente.end and existente.start < nuevo.end` → `OVERLAPS_EXISTING`.
6. Si todo pasa → `accept(ends_at)`.

Razón del orden: de lo más barato y general (reloj, configuración) a lo que requiere datos de otros turnos; y es el orden que usa la KB al enumerar las reglas. Se evalúa "grilla" antes que "horario" para que un 10:10 dentro del horario diga `OFF_GRID` (mensaje más útil); un 08:30 fuera del tramo dice `OUTSIDE_WORKING_HOURS` aunque también esté "fuera de grilla" respecto de ningún tramo.

Alternativa: devolver todos los motivos. Descartada por el usuario para v1 (más difícil de testear y explicar); queda como mejora futura.

### D5. Convenciones

- `weekday`: 0 = lunes ... 6 = domingo, igual a `datetime.weekday()` de Python. El seed (C-02) y la carga de horarios (C-07) deben usar la misma convención.
- Grilla anclada al inicio de cada tramo, no a la hora en punto.
- Rangos semiabiertos `[inicio, fin)`, igual que `tstzrange` del constraint de exclusión de C-02: un turno que empieza cuando termina otro no se solapa.
- Comparación de horario y licencia en hora local del consultorio (`zoneinfo.ZoneInfo(timezone)`); anticipación y solapamiento en UTC (instantes absolutos). Cubre RN-GL-01 en lo mínimo.
- Solo `scheduled` ocupa. `cancelled`, `completed` y `no_show` se ignoran (igual que el `WHERE status = 'scheduled'` del constraint).

### D6. Arranque mínimo de `backend/` (DD local del change)

**Decisión**: crear solo lo necesario para correr pytest sobre funciones puras, sin ejecutar C-01:

- `backend/pyproject.toml`: proyecto `sistema-odontologico-backend`, `requires-python = ">=3.12"`, sin dependencias de runtime; pytest como dependencia de desarrollo (grupo opcional `dev`); `tzdata` como dependencia (necesaria en Windows para `zoneinfo`); `[tool.pytest.ini_options]` con `testpaths = ["tests"]` y `pythonpath = ["."]`.
- Paquetes: `backend/app/__init__.py`, `backend/app/domain/__init__.py`, `backend/app/domain/appointments/__init__.py`.
- Tests: `backend/tests/unit/domain/appointments/` (con `__init__.py` donde haga falta para pytest).
- Sin FastAPI, SQLAlchemy, Celery, Redis, Docker, ruff ni frontend.

**Por qué**: en `CHANGES.md` C-05 es "puro, sin BD" y paralelo a C-02; hacer C-01 completo antes retrasaría la regla central sin aportar nada a su verificación.

**Cómo lo absorbe C-01**: misma ruta `backend/`, mismo `pyproject.toml` (C-01 agrega dependencias, ruff y la carpeta de integración), mismos paquetes. C-01 no lo rehace ni lo contradice. Se registra como nota en C-05 de `CHANGES.md`.

**Alternativa**: hacer primero un C-01 recortado. Descartada por el usuario.

### D7. Cobertura de reglas

| Regla | Cubierta | Cómo |
|-------|----------|------|
| RN-TU-01 (sin solape por profesional) | Sí | Regla 5 |
| RN-TU-02 (duración `slot_minutes` y grilla) | Sí | Regla 2 y cálculo de `ends_at` |
| RN-TU-03 (dentro de tramo y fuera de licencia) | Sí | Reglas 3 y 4 |
| RN-HO-03 (licencia bloquea el día) | Sí | Regla 4 |
| RN-TU-04 (no en el pasado), reformulada | Sí | Cubierta por RN-TU-12, regla 1 |
| RN-TU-12 (anticipación mínima, nueva) | Sí | Regla 1 |
| RN-GL-01 (UTC y zona del consultorio) | Mínimo | Conversión a hora local para horario y licencia |
| RN-TU-08, RN-TU-09, RN-TU-10, RN-TU-11 | Como restricción | Sin validación por paciente; sin sillón; duración fija; sin parámetro de sobreturno |
| RN-TU-05/06/07, RN-PA-04, RN-HO-02, RN-HO-04, RN-NO-xx | No | Fuera de alcance (proposal, Non-goals) |

### D8. Verificación: mapeo escenario → test

Archivo: `backend/tests/unit/domain/appointments/test_validate_appointment.py` (un archivo; si crece, se divide por regla). Fixtures/helpers en el mismo módulo o `conftest.py`: horario de la Dra. A y del Dr. B, `now` por defecto, helper `local(año, mes, día, hh, mm)` que devuelve el instante UTC correspondiente a la hora local de Buenos Aires.

| Requisito | Escenario | Test |
|-----------|-----------|------|
| Resultado | Turno libre dentro del horario (feliz) | `test_accepts_free_slot_and_computes_ends_at` |
| Resultado | El instante en UTC se interpreta en hora local | `test_utc_instant_is_evaluated_in_clinic_local_time` |
| Anticipación | Anticipación insuficiente | `test_rejects_insufficient_notice` |
| Anticipación | Anticipación exacta de 6 h | `test_accepts_exactly_min_notice` |
| Anticipación | Turno en el pasado | `test_rejects_start_in_the_past` |
| Anticipación | Anticipación configurada en 12 h | `test_rejects_with_configured_12h_notice` |
| Grilla | Inicio fuera de la grilla | `test_rejects_off_grid_start` |
| Grilla | La grilla se cuenta desde el inicio del tramo | `test_grid_is_anchored_to_block_start` |
| Horario | Antes del inicio del horario | `test_rejects_before_working_hours` |
| Horario | En el hueco entre dos tramos | `test_rejects_gap_between_blocks` |
| Horario | Último slot del tramo | `test_accepts_last_slot_ending_at_block_end` |
| Horario | Día sin horario de trabajo | `test_rejects_day_without_working_hours` |
| Licencia | Turno en el último día de una licencia | `test_rejects_on_last_day_of_time_off` |
| Solapamiento | Pisa a otro turno del mismo profesional | `test_rejects_overlap_with_same_professional` |
| Solapamiento | Empieza justo cuando termina otro | `test_accepts_back_to_back_after_existing` |
| Solapamiento | Termina justo cuando empieza otro | `test_accepts_back_to_back_before_existing` |
| Solapamiento | Mismo horario con otro profesional | `test_accepts_same_time_other_professional` |
| Solapamiento | Turno cancelado no ocupa | `test_cancelled_appointment_does_not_block` |
| Orden | Anticipación insuficiente y fuera de grilla | `test_notice_wins_over_off_grid` |
| Orden | Licencia y solapamiento a la vez | `test_time_off_wins_over_overlap` |
| (diseño D3) | `datetime` sin zona | `test_naive_datetime_raises_value_error` |

## Risks / Trade-offs

- [C-05 completo es más grande que este change; C-07/C-08/C-09 podrían asumir que C-05 está terminado] → Nota explícita en C-05 de `CHANGES.md` indicando qué se hizo y qué queda pendiente.
- [Conflicto con C-01 si se hace en paralelo sobre `backend/pyproject.toml`] → C-01 parte del esqueleto existente; la nota en `CHANGES.md` lo indica.
- [La validación del dominio no evita la carrera entre dos recepcionistas (US-007)] → La garantía real es el constraint de exclusión de C-02; esta función es la primera línea y da el mensaje claro.
- [Zona horaria: DST en otras zonas puede producir horas inexistentes o repetidas] → Fuera de alcance; la zona por defecto no tiene DST. Se documenta como límite.
- [`working_hours`/`time_off` de otro profesional pasados por error] → El contrato dice que vienen filtrados; el caso de uso (C-08) es responsable. Se deja escrito en el docstring.
- [Turnos `completed`/`no_show` futuros (datos inconsistentes) no bloquean] → Coherente con el constraint de C-02; en la práctica son pasados y la anticipación ya los cubre.
- [Python 3.12 como mínimo no está fijado en la KB] → Se documenta en `pyproject.toml`; C-01 lo confirma con la imagen de Docker.

## Migration Plan

No hay datos ni despliegue: es código nuevo y documentación. Rollback = borrar `backend/` y revertir los cambios de documentación. `min_notice_hours` en `clinic_settings` solo se documenta en la KB; la columna real la crea C-02.

## Open Questions

- Versión exacta de Python para C-01 / Docker (se propone 3.12; no cambia la lógica).
- Si en el futuro `existing_appointments` llega solo del profesional (consulta filtrada en el repositorio), el filtro por `professional_id` de la función queda redundante pero inofensivo.
