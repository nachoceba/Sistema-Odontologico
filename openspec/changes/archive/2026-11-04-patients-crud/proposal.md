# Proposal: patients-crud (C-06)

> **Gobernanza BAJA** (ABM de pacientes, `CHANGES.md`), pero con datos personales (ficticios, RN-PR-01). Las decisiones de dominio P-1 a P-12 de `design.md` fueron **confirmadas por la usuaria el 2026-11-04** (opción recomendada en todas; DD-73 a DD-78 en la KB). Las specs reflejan esas opciones.

## Why

Hoy los pacientes solo existen por el seed (10 ficticios): no hay forma de dar de alta, buscar, editar ni desactivar un paciente desde la app (US-003). El puerto `PatientRepository` de C-05d solo sabe buscar por id (DD-34) y la agenda de C-08 ya lo usa para RN-PA-04, pero la recepción no puede cargar a quien llama por primera vez. C-10 (pantalla para agendar) depende de este change para "buscar o crear el paciente" desde el turno (Flujo 2, paso 2).

## What Changes

- **Reglas puras de datos del paciente** en `app/domain/patients/`: normalizar y validar documento (RN-PA-01), nombre y apellido, email obligatorio (RN-PA-02, reusa `is_valid_email` de C-04), teléfono opcional y fecha de nacimiento opcional (sin fecha futura). Sin FastAPI ni SQLAlchemy.
- **Repositorio de pacientes ampliado** (memoria y PostgreSQL, misma batería de contrato): leer la ficha completa, buscar por apellido o documento, dar de alta, editar, activar/desactivar y (si P-6 = A) borrar un paciente sin turnos. El documento repetido se rechaza también si dos altas llegan a la vez (UNIQUE de la base, C-02).
- **Casos de uso** en `app/application/patients.py`: listar y buscar, ver, alta, edición, desactivación (devuelve sus turnos `scheduled` futuros **sin cancelarlos**, DD-25), reactivación y borrado definitivo restringido (P-6). El rol se chequea también en el caso de uso (RN-PR-02).
- **API** `/api/v1/patients` con JWT y `require_role`: listado/búsqueda, detalle, alta, edición, desactivar, reactivar y borrar. Permisos según la matriz (`03_actores_y_roles.md`): administración todo, recepción crear/leer/editar (incluye desactivar y reactivar), odontólogo solo lectura (alcance en P-4). Cada endpoint con su test de permisos por rol.
- **Errores nuevos** en el modelo uniforme: `DOCUMENT_TAKEN` (409), `PATIENT_HAS_APPOINTMENTS` (409, solo si P-6 = A) y `INVALID_PATIENT_DATA` (400, fecha de nacimiento futura). Los mensajes no repiten datos del paciente; los 422 siguen sin eco.
- **Pantalla `/pacientes`** (P-11): listado con búsqueda, alta, edición, desactivar/reactivar con aviso de turnos futuros; recepción y administración editan, el odontólogo la ve en modo lectura. El buscador y el formulario quedan como componentes reutilizables para el selector de paciente de C-10.
- Regla dura 6: no se toca la agenda ni el constraint de exclusión; desactivar no cambia ningún turno y la suite de C-08 corre como red de seguridad.

## Capabilities

### New Capabilities
- `patient-data-rules`: reglas puras para normalizar y validar los datos de un paciente (documento, nombres, email, teléfono, fecha de nacimiento).
- `patient-management`: casos de uso de pacientes (listar/buscar, ver, alta, edición, desactivar con turnos futuros listados, reactivar, borrado restringido) con alcance por rol.
- `patient-api`: endpoints `/api/v1/patients`, su formato, validación y matriz de permisos por rol.
- `frontend-patient-management`: pantalla `/pacientes` y componentes reutilizables de búsqueda y formulario (sujeta a P-11).

### Modified Capabilities
- `patient-repository`: además de `get(id)`, ficha completa, búsqueda, alta con documento único, edición, cambio de estado activo y borrado sin turnos.
- `error-model`: la tabla de códigos suma `DOCUMENT_TAKEN` y `PATIENT_HAS_APPOINTMENTS` (409) e `INVALID_PATIENT_DATA` (400).

## Impact

- **Código nuevo**: `app/domain/patients/rules.py` y `errors.py`, tipos nuevos en `app/domain/patients/types.py`, métodos nuevos en el puerto (`ports.py`), `app/infrastructure/in_memory/patients.py` y `app/infrastructure/db/repositories/patients.py`; `app/application/patients.py`; `app/api/patients.py`, fábrica en `app/api/dependencies.py`, inclusión en `app/api/router.py`; `STATUS_BY_CODE` en `app/api/errors.py`.
- **Frontend**: `frontend/src/api/patients.ts`, `frontend/src/pages/PatientsPage.tsx`, componentes en `frontend/src/patients/`, ruta y enlace en `App.tsx`.
- **Tests**: dominio puro, batería de contrato (memoria y PostgreSQL), casos de uso en memoria con reloj fijo, API con tabla de permisos por rol, integración con el seed, Vitest.
- **Sin** migraciones, variables de entorno ni dependencias nuevas con las opciones recomendadas (P-3 = B "ignorar acentos" sí exigiría una migración con `unaccent`).
- **Consumidores**: C-08 sigue usando `get(id)` sin cambios; C-10 usará la búsqueda y el formulario; C-11/C-12 leerán el email vigente del paciente al enviar (editar el email cambia a dónde llegan los avisos siguientes).
