# Proposal: crear-turno-sin-solapamientos

## Why

Hoy la recepción agenda en planilla o WhatsApp y es fácil darle a un mismo odontólogo dos pacientes a la misma hora. El sistema necesita responder una sola pregunta de negocio con reglas claras y comprobables: **"¿puedo crear este turno para este profesional?"**, y contestar "sí" o "no, por este motivo". Es la regla central de la agenda (RN-TU-01, regla dura 6 de `AGENTS.md`) y conviene tenerla antes que cualquier pantalla, base de datos o endpoint.

### Justificación de la elección

Elegimos este change porque es lo más importante del sistema: que a un mismo odontólogo no le den dos turnos al mismo tiempo. Está dentro del MVP que recomendamos en el informe y tiene reglas claras que se pueden probar sin pantallas ni base de datos, así que es chico y se puede terminar bien. Lo dejamos por profesional, sin sillones ni duraciones distintas por tratamiento, que quedan para más adelante. También pedimos que haya al menos 6 horas de anticipación para sacar un turno, así al doctor y al consultorio les da tiempo de prepararse; ese número se puede cambiar según lo llena que tenga la agenda cada consultorio.

Un consultorio puede tener uno o varios odontólogos. La regla se aplica a cada uno por separado: el mismo doctor no puede tener dos turnos que se pisen, pero dos doctores distintos sí pueden atender a la misma hora.

### Vínculo con el informe y el roadmap

- **Informe de Discovery, sección D (MVP imprescindible)**: cubre la parte "agenda multi-profesional con prevención de solapamientos" de D.3. Sillón/box y duración por prestación quedan fuera por DD-07 y DD-08 (cobertura "Parcial" ya registrada en `CHANGES.md`).
- **`CHANGES.md`, C-05 `domain-scheduling-core`**: este change ejecuta primero una porción de C-05 (`validate_appointment` para crear un turno) más un arranque mínimo de `backend/`. El resto de C-05 queda pendiente.

## What Changes

- Nueva función de dominio pura que decide si un turno puede crearse para un profesional y devuelve un resultado: **aceptado** (con la hora de fin calculada) o **rechazado** con **un solo motivo**.
- Reglas que valida, en este orden fijo: anticipación mínima (incluye "no en el pasado"), grilla de slots, horario de trabajo del profesional, licencias del profesional y solapamiento con otros turnos `scheduled` del mismo profesional.
- Nueva regla de negocio **RN-TU-12, anticipación mínima**: el turno debe empezar al menos `min_notice_hours` (6 por defecto, configurable) después del momento actual; el límite exacto se acepta. RN-TU-04 ("no en el pasado") queda cubierta por esta regla.
- Arranque mínimo del backend: `backend/pyproject.toml` con pytest y los paquetes `backend/app/domain/appointments/` y `backend/tests/unit/`, sin FastAPI, SQLAlchemy, Celery, Redis ni Docker. C-01 lo extiende sin rehacerlo.
- Actualización mínima de documentación: RN-TU-12 en reglas de negocio, `min_notice_hours` en `clinic_settings`, nueva decisión DD sobre la anticipación, nueva pregunta abierta sobre turnos urgentes y nota en C-05 de `CHANGES.md`.

## Non-goals

- Calcular slots libres para mostrar en pantalla (`compute_slots`).
- Cancelar, reprogramar, marcar atendido o ausente (transiciones de estado).
- Validaciones de pacientes (paciente inactivo, RN-PA-04) y cualquier límite por paciente (un paciente puede tener varios turnos, RN-TU-08).
- Repositorios, base de datos, migraciones, constraint de exclusión, endpoints, pantallas, login y emails.
- Concurrencia entre dos recepcionistas: la garantiza el constraint de exclusión de C-02; esta función es la primera línea, no la única.
- Sillones o boxes (RN-TU-09, DD-08), duración variable por prestación (RN-TU-10) y sobreturnos (RN-TU-11).
- Zona horaria más allá de lo necesario para comparar el turno con el horario local del profesional (sin soporte especial de horario de verano).
- Leer `min_notice_hours` desde `clinic_settings`: en este change llega como parámetro.

## Capabilities

### New Capabilities

- `appointment-creation`: validación de dominio para crear un turno de un profesional (anticipación mínima, grilla, horario de trabajo, licencias y no solapamiento), con resultado aceptado/rechazado y un único motivo.

### Modified Capabilities

(ninguna; no hay specs previas en `openspec/specs/`)

## Impact

- **Código nuevo**: `backend/pyproject.toml`, `backend/app/__init__.py`, `backend/app/domain/__init__.py`, `backend/app/domain/appointments/` (función y tipos), `backend/tests/unit/domain/appointments/` (tests).
- **Dependencias**: solo pytest como dependencia de desarrollo; zona horaria con `zoneinfo` de la librería estándar (en Windows puede requerir el paquete `tzdata`).
- **Documentación**: `knowledge-base/05_reglas_de_negocio.md`, `04_modelo_de_datos.md`, `09_decisiones_y_supuestos.md`, `10_preguntas_abiertas.md` y `CHANGES.md` (C-05).
- **Changes posteriores**: C-01 parte del esqueleto existente; C-08 (casos de uso) llama a esta función y convierte el rechazo en error; C-02 agrega `min_notice_hours` a `clinic_settings`.
- **Governance**: MEDIO (lógica de negocio, igual que C-05).

## Preguntas abiertas

1. ¿Se permite saltar la anticipación mínima para un turno urgente del mismo día y quién puede hacerlo? (registrada en `10_preguntas_abiertas.md`, fuera de este change).
2. ¿La versión mínima de Python que se fija en `pyproject.toml` (3.12 propuesta) es la que usará C-01 y la imagen de Docker? La KB no la fija.
3. RN-TU-03 y el modelo de datos tratan las licencias por días completos; si en el futuro hay licencias por horas, la regla de licencias cambia.
4. Turnos `completed` y `no_show` no cuentan como ocupados (igual que el constraint de C-02, que solo mira `scheduled`). En la práctica son turnos pasados y la anticipación mínima ya impide chocar con ellos; se deja escrito para revisión.
