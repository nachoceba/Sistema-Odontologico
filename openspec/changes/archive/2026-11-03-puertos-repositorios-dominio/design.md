# Design: puertos-repositorios-dominio (C-05d)

## Context

Motivación y alcance: ver `proposal.md`. Requisitos: ver `specs/appointment-repository`, `specs/schedule-repository`, `specs/patient-repository` y `specs/clinic-settings-repository`.

Estado del código al proponer (verificado leyendo `backend/app/`):

- `domain/appointments/types.py`: `ExistingAppointment(professional_id, starts_at, ends_at, status)` sin id ni paciente; `WorkingHours`, `TimeOff(starts_on, ends_on)` sin id ni motivo. Identificadores de profesional como `str`.
- `domain/appointments/rules.py`: `ranges_overlap` y `overlaps_scheduled` son la única fuente de la regla de solapamiento (DD-20).
- `core/timezone.py`: `local_day_bounds(day, tz)` ya da el rango UTC `[inicio, fin)` de un día local.
- Imports: `schedules/validation.py` importa `app.domain.appointments.types` en tiempo de ejecución y `appointments/slots.py` / `validation.py` importan `app.domain.schedules`. El ciclo se evita porque `schedules/__init__.py` importa primero `time_off.py`, que solo importa `TimeOff` bajo `TYPE_CHECKING`. Es frágil al orden de los imports.
- No existen `application/` ni `infrastructure/`. 131 tests en verde; `mypy --strict app/` limpio (mypy y ruff aún no están en `pyproject.toml`, pendiente de C-01).

Restricciones: regla dura 2 (nada de FastAPI, SQLAlchemy, Celery ni Redis en `domain/`), regla dura 6 (todo cambio en la agenda lleva su test de no solapamiento), Strict TDD, governance MEDIO.

## Goals / Non-Goals

**Goals:**

- Que C-07, C-08 y C-09 escriban casos de uso y tests de aplicación contra interfaces estables, sin PostgreSQL.
- Que el repositorio en memoria sea un doble fiel de la base en lo que importa a la agenda: el rechazo del solapamiento y los CHECK de rangos.
- Que la misma batería de contrato valide después el repositorio SQLAlchemy (C-02/C-08) agregando una sola fábrica.
- Cero cambios de comportamiento en las seis capabilities archivadas.

**Non-Goals:**

- Repositorio SQLAlchemy, sesión, modelos y migraciones (C-02/C-08).
- Concurrencia real: dos inserciones simultáneas las prueba C-08 contra PostgreSQL. El repositorio en memoria no es seguro entre hilos y no lo necesita.
- Validar reglas de negocio dentro del repositorio (grilla, horario, anticipación, transiciones): las aplica el caso de uso con las funciones de `domain/`. El repositorio solo replica lo que la base garantiza por sí misma.

## Decisions

### D-1 — Puertos como `typing.Protocol`, uno por subdominio

- `backend/app/domain/appointments/ports.py`: `AppointmentRepository`.
- `backend/app/domain/schedules/ports.py`: `WorkingHoursRepository`, `TimeOffRepository`.
- `backend/app/domain/patients/ports.py`: `PatientRepository`.
- `backend/app/domain/settings/ports.py` (+ `types.py`): `ClinicSettingsRepository` y `ClinicSettings(slot_minutes, timezone, min_notice_hours)`.

`Protocol` y no `ABC`: el repositorio SQLAlchemy no necesita heredar de nada del dominio (tipado estructural) y `mypy --strict` verifica la conformidad con una asignación anotada (`repo: AppointmentRepository = InMemoryAppointmentRepository()`) en los tests de contrato. Sin `@runtime_checkable`: la verificación es estática. Respaldo: patrones Repository y Puerto y adaptador de `08_arquitectura_propuesta.md`; estructura `domain/{appointments,schedules,patients}`. `settings/` es un subpaquete nuevo porque la configuración no pertenece a ningún subdominio existente. Alternativa descartada: un único `domain/ports.py` (mezcla subdominios y obliga a importar todos los tipos juntos, lo que reabre el ciclo de imports).

### D-2 — Ciclo de imports: los puertos solo importan tipos bajo `TYPE_CHECKING`

Cada `ports.py` usa `from __future__ import annotations` e importa los tipos de dominio dentro de `if TYPE_CHECKING:` (los `Protocol` solo los usan en anotaciones). Así `schedules/ports.py` no agrega ningún import en tiempo de ejecución hacia `appointments` (misma técnica que `schedules/time_off.py`). Los `__init__.py` reexportan los puertos **al final**, después de los imports existentes. Se agrega un test que importa cada paquete (`app.domain.schedules`, `app.domain.appointments`, `app.domain.patients`, `app.domain.settings`, `app.infrastructure.in_memory`) como primer import en un intérprete nuevo (`subprocess` con `python -c`), para detectar un ciclo según el orden de entrada.

### D-3 — Tipos con identidad, sin tocar los tipos existentes

En `appointments/types.py`: `NewAppointment(patient_id, professional_id, starts_at, ends_at, created_by)` (entrada) y `Appointment(id, patient_id, professional_id, starts_at, ends_at, status, cancel_reason, created_by)` (salida), ambos `frozen`, con `Appointment.to_existing() -> ExistingAppointment`. En `schedules/` (archivo `types.py` nuevo, importando `TimeOff` desde `appointments.types` igual que `validation.py`): `TimeOffEntry(id, professional_id, starts_on, ends_on, reason)` con `to_time_off() -> TimeOff`. En `patients/types.py`: `Patient(id, first_name, last_name, email, active)`. Identificadores `str` (como `professional_id` hoy); la implementación SQLAlchemy convierte desde `uuid`. Alternativa descartada: hacer que `Appointment` herede de `ExistingAppointment` (acopla el dato de entrada de las reglas al de persistencia y confunde cuál pasar a cada función). Alternativa descartada: cambiar `ExistingAppointment` para agregar id (rompería 131 tests sin beneficio).

### D-4 — Métodos del repositorio de turnos con intención explícita

`add(new) -> Appointment`, `get(id) -> Appointment | None`, `change_status(id, status, cancel_reason=None) -> Appointment`, `reschedule(id, starts_at, ends_at) -> Appointment`, `list_for_professional(professional_id, start, end=None) -> list[Appointment]`, `list_for_patient(patient_id, start, end=None) -> list[Appointment]`. Cada método corresponde a una operación de C-08 y a un único `INSERT`/`UPDATE`/`SELECT`, lo que hace evidente que `reschedule` es atómico (RN-TU-06, Flujo 3 paso 3). El id lo genera el repositorio (`uuid4` en memoria; `gen_random_uuid()` o `uuid4` en SQLAlchemy). Alternativa descartada: un `save(appointment)` genérico (mezcla alta, cambio de estado y reprogramación en un método; el caso de uso tendría que reconstruir el turno completo para cambiar un campo). Formas de retorno y de "no encontrado": confirmados (P-3, DD-33).

### D-5 — No solapamiento en memoria: misma regla, mismo momento que la base

`InMemoryAppointmentRepository` guarda los turnos en un `dict[str, Appointment]`. Antes de cualquier escritura que deje un turno `scheduled`, llama a `overlaps_scheduled` (única fuente, DD-20) contra los turnos `scheduled` del mismo profesional **excluyendo al propio turno**; si hay choque, lanza el error de turno ocupado sin modificar el `dict` (se calcula el turno nuevo, se valida y recién después se asigna). Valida también, con `ValueError`, instantes sin zona y `starts_at >= ends_at` (equivalente a los CHECK) y, en licencias, `starts_on > ends_on`. Esto reproduce `EXCLUDE ... WHERE (status = 'scheduled')` con rangos `[)`: tocarse en el borde no choca, `cancelled`/`completed`/`no_show` no bloquean, otro profesional no bloquea, un cambio a `scheduled` vuelve a chequear. Las listas se devuelven como copias nuevas (los tipos son inmutables), así un llamador no altera el estado interno.

### D-6 — Repositorios en memoria en `app/infrastructure/in_memory/`

Ubicación: `backend/app/infrastructure/in_memory/` (`appointments.py`, `schedules.py`, `patients.py`, `settings.py`). Justificación con la KB: (1) `08_arquitectura_propuesta.md` define `infrastructure/` como la capa de los adaptadores de los puertos ("Puerto y adaptador", "Repository: permite tests con repositorios en memoria"); un repositorio en memoria es otro adaptador del mismo puerto, igual que el SMTP falso que menciona la tabla; (2) quedan dentro de `mypy --strict app/`, que verifica que cumplen el `Protocol` (en `tests/` no se chequearían hoy); (3) los tests de aplicación de C-07, C-08 y C-09 los reutilizan sin importar desde `tests/`. Riesgo aceptado: un doble de prueba vive en el paquete de producción; se mitiga porque ningún módulo de `api/` ni de la composición lo conecta (C-08 conecta el de SQLAlchemy) y el nombre del paquete lo deja explícito. Alternativa descartada: `backend/tests/fakes/` (fuera del chequeo de mypy y obliga a `application/` tests a depender de rutas de test). El paquete `app/infrastructure/` se crea con su `__init__.py`; C-01 lo extiende con `db/`, `email/` y `tasks/` sin rehacerlo.

### D-7 — Tests de contrato compartidos parametrizados por fábrica

`backend/tests/contract/` con `conftest.py` que define fixtures parametrizadas (`appointment_repo`, `working_hours_repo`, `time_off_repo`, `patient_repo`, `settings_repo`) sobre una lista de fábricas; hoy solo `pytest.param(make_in_memory, id="in_memory")`. C-02/C-08 agrega `pytest.param(make_sqlalchemy, id="postgres", marks=pytest.mark.integration)` con una sesión en transacción revertida por test. Cada fábrica crea un repositorio vacío por test. Los tests solo usan el puerto (nunca atributos del repositorio en memoria), para que la batería sea portable. Los escenarios que necesitan estado inicial (paciente inactivo, configuración cargada) lo preparan con un parámetro de la fábrica (`make_in_memory(patients=[...])`, `settings=ClinicSettings(...)`), porque el puerto mínimo no tiene alta de pacientes ni escritura de configuración. Los escenarios de integración con reglas (`validate_appointment`, `compute_slots`, `check_patient_can_book`) viven en la misma batería: prueban que el dato del repositorio encaja con las funciones de dominio.

### D-8 — Los repositorios de horario no validan reglas de negocio

`replace_for_professional` guarda los tramos tal cual; el caso de uso de C-07 llama antes a `validate_working_hours`. La base tiene `CHECK (start_time < end_time)` pero la no superposición entre tramos no es un constraint de la base (`04_modelo_de_datos.md` la enuncia sin `EXCLUDE`); duplicar parte de la validación en el repositorio daría dos fuentes. Por eso la spec deja fuera del contrato qué pasa con tramos inválidos.

### Decisiones de diseño (CONFIRMADAS por el usuario)

Ninguna tenía respaldo directo en la KB. El usuario aceptó las seis recomendaciones tal cual; quedaron registradas como DD-31 (P-1), DD-32 (P-2), DD-33 (P-3), DD-34 (P-4), DD-35 (P-5) y DD-36 (P-6) en `knowledge-base/09_decisiones_y_supuestos.md`. El puerto de configuración del consultorio se mantiene.

| # | Pregunta (en lenguaje simple) | Decisión confirmada | Por qué | Respaldo |
|---|------|------|------|------|
| P-1 | Cuando el sistema pide "los turnos de la Dra. A", ¿los pide por **"desde tal momento hasta tal momento"** o por **"el día tal"**? | **Desde/hasta momento**. Quien pide un día lo convierte una vez con el reloj del consultorio (`local_day_bounds`). | La zona horaria queda en un solo lugar; sirve igual para el día, la semana de C-09 y "todos los futuros" de C-07 (sin fin). Un turno que cruza la medianoche aparece en los dos días, como en DD-19. | RN-GL-01; forma del rango **sin respaldo en la KB** |
| P-2 | Si al guardar un turno el horario ya está tomado (por ejemplo, dos recepcionistas al mismo tiempo), ¿cómo avisa el repositorio? Opciones: **(a)** una "alarma" (error) con nombre propio, `SLOT_TAKEN`, que el sistema convierte en el mensaje "el horario acaba de ocuparse"; **(b)** devolver una respuesta "aceptado / rechazado" como hace `validate_appointment`. Lo mismo para "el turno no existe" (`APPOINTMENT_NOT_FOUND`). | **(a) Error con nombre propio**, definido en `domain/appointments/errors.py` (C-01 lo podrá reexportar desde `core/errors.py`). | Es un caso raro que normalmente ya filtró `validate_appointment`; es exactamente lo que hace la base al rechazar, y C-08 lo traduce en un solo lugar (Flujo 2, casos de error). | Flujo 2 y entrada C-08 ("traduce el error del constraint"); forma del error **sin respaldo en la KB** |
| P-3 | ¿Qué devuelve el repositorio en cada operación? Propuesta: al guardar, **el turno o la licencia completos con su número nuevo**; al buscar algo que no existe, **"no encontrado" sin error**; al cancelar o reprogramar algo que no existe, **error** `APPOINTMENT_NOT_FOUND`. | **Aceptar la propuesta.** | Buscar y no encontrar es normal (por ejemplo, un enlace viejo); modificar algo que no existe es un error del llamador. Devolver el turno completo evita una segunda consulta. | **Sin respaldo en la KB** |
| P-4 | El repositorio de pacientes, ¿cubre **solo "este paciente existe y está activo"** (lo que necesita agendar) o ya **todo el ABM** (alta, búsqueda por apellido y documento, documento único)? | **Solo lo mínimo**; C-06 agrega alta, búsqueda y unicidad del documento al mismo puerto. | CHANGES.md pide en C-08 una "lectura mínima de paciente activo para RN-PA-04 (sin depender de la UI de C-06)"; definir el ABM ahora sería adivinar las firmas de C-06. | Entradas C-06 y C-08 de `CHANGES.md`, RN-PA-04 |
| P-5 | Cuando se listan los turnos de un profesional o paciente, ¿se devuelven **todos los estados** (agendado, cancelado, atendido, ausente) o **solo los agendados**? | **Todos**, ordenados por hora de inicio; cada pantalla o regla filtra lo que necesita. | `compute_slots` y `validate_appointment` ya ignoran los no agendados; la agenda (C-09) y el historial de un paciente necesitan ver los cancelados y atendidos. Con un filtro en el repositorio habría dos listados casi iguales. | RN-TU-05, DD-16; filtro **sin respaldo en la KB** |
| P-6 | ¿Hace falta ahora **"todo o nada" entre varias operaciones** (por ejemplo, guardar el turno y su aviso por email juntos), lo que se llama "unidad de trabajo"? | **No en C-05d.** Cada operación del repositorio ya es "todo o nada" por sí sola (incluida reprogramar). C-08 decide, con la base real, si agrupa turno y notificación en una misma transacción. | La KB dice que un fallo de email nunca impide agendar (RN-NO-04), así que el turno no depende del aviso; diseñar la agrupación sin base de datos sería adivinar. | RN-TU-06, RN-NO-04; unidad de trabajo **sin respaldo en la KB** |

Nota (decisión de alcance, confirmada): el puerto de configuración del consultorio (`clinic-settings-repository`) se incluye con solo tres campos de lectura; si el usuario prefiere que C-08 lea la configuración por su cuenta, se elimina esa spec sin afectar a las otras tres.

### Revisión de escenarios (skill `revisor-escenarios-turnos`)

Se revisaron los 51 escenarios contra `05_reglas_de_negocio.md`, `09_decisiones_y_supuestos.md`, `10_preguntas_abiertas.md`, `04_modelo_de_datos.md` y la entrada C-05 de `CHANGES.md`.

Resumen: 51 escenarios revisados, 6 hallazgos (1 ambigüedad, 2 bordes faltantes, 0 reglas solapadas, 1 pregunta abierta, 2 sin respaldo, 0 contrato incompleto, 0 contradicciones).

| # | Tipo | Escenario afectado | Qué pasa | Respaldo en la KB | Sugerencia (a confirmar) |
|---|------|--------------------|----------|-------------------|--------------------------|
| H-1 | Borde faltante (resuelto) | Solapamiento | No había escenario para un mismo paciente con dos profesionales a la misma hora | RN-TU-01 (solo profesional), RN-TU-08 / SU-05 | Agregado "Mismo paciente con dos profesionales a la misma hora": el repositorio lo acepta como la base; la regla para el paciente queda fuera (ver abajo) |
| H-2 | Pregunta abierta | H-1 | ¿Se debe impedir que un paciente tenga dos turnos superpuestos con profesionales distintos? | SU-05 (solo habla de "el mismo día"), `10_preguntas_abiertas.md` | Pregunta para C-08, no para C-05d (el repositorio replica la base) |
| H-3 | Ambigüedad | "Turno que cruza la medianoche choca por instantes" | Con DD-26 ningún tramo cruza la medianoche, así que ese turno no surge de un caso de uso válido | DD-19, DD-26 | Mantener: el contrato prueba equivalencia con el constraint, no la regla de horario |
| H-4 | Sin respaldo | Listar por paciente | La KB no pide listar turnos por paciente | DD-25 (los turnos futuros de un paciente desactivado "se listan") | Mantener; respaldo indirecto en DD-25 |
| H-5 | Sin respaldo | Forma de búsqueda, error, retorno, filtro de estados | Decisiones de diseño nuevas | **sin respaldo en la KB** | P-1, P-2, P-3, P-5 |
| H-6 | Borde faltante (resuelto) | Volver a `scheduled` | El repositorio podía dejar saltear la base si el caso de uso fallaba | RN-TU-01, constraint de exclusión | Agregado "Volver a scheduled sobre un horario ya tomado" |

Cobertura: hay escenarios esperados, de error de negocio (`SLOT_TAKEN`, `APPOINTMENT_NOT_FOUND`, `PATIENT_INACTIVE`) y de borde en el change. `schedule-repository` y `clinic-settings-repository` no tienen errores de negocio propios (solo errores de programación con `ValueError`): sus reglas de negocio están en `schedule-validation`.

### Fuera de C-05d (registrar en CHANGES.md al archivar)

- Repositorio SQLAlchemy de cada puerto y su fábrica en la batería de contrato (C-02/C-08); test de concurrencia real (C-08).
- Alta, búsqueda y unicidad de documento de pacientes (C-06, extiende `PatientRepository`).
- Repositorio de profesionales (listado, activo) y de usuarios (C-04/C-07).
- Borrar o editar licencias (sin respaldo en la KB; US-005 solo pide cargarlas).
- Listado de turnos de todos los profesionales en un rango, para los recordatorios (C-12) y `NotificationPort` (C-08/C-11).
- Datos del consultorio para emails (nombre, dirección, teléfono, hora del recordatorio) en `ClinicSettings` (C-11/C-12).
- Pregunta H-2 (paciente con dos turnos simultáneos con distintos profesionales), para C-08.

## Risks / Trade-offs

- [El repositorio en memoria diverge de PostgreSQL] → la batería de contrato se diseña para correr contra ambos; C-02/C-08 agrega la fábrica SQLAlchemy y cualquier diferencia aparece como test rojo.
- [Firmas definidas antes de sus consumidores (C-07, C-08, C-09)] → se limitan a lo que piden sus entradas en `CHANGES.md` y los flujos 2, 3 y 5; P-1 a P-6 confirman las formas antes de codear; un cambio posterior se hace con `/opsx:update` del change que lo necesite.
- [Reintroducir el ciclo de imports `appointments` ↔ `schedules`] → D-2 (`TYPE_CHECKING` en puertos, reexport al final) y test de import en intérprete nuevo.
- [Doble de prueba dentro de `app/`] → D-6: ningún módulo de producción lo conecta; nombre explícito.
- [Tests que solo prueban un diccionario] → cada escenario de la batería expresa una garantía de la base o una integración con las reglas de dominio, no detalles de almacenamiento.

## Migration Plan

No aplica: código nuevo sin datos ni despliegue. Rollback: revertir los archivos nuevos; nada existente cambia de comportamiento.
