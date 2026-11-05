# Tasks: patients-crud (C-06)

> **Gobernanza BAJA, con datos personales ficticios.** El grupo 0 (confirmaciones P-1 a P-12) está resuelto: la usuaria confirmó la opción A en todas el 2026-11-04. Modo TDD estricto: en cada task de código, primero el test que falla (RED, se ejecuta y se ve fallar), después el mínimo código (GREEN), triangulación con un segundo caso (TRIANGULATE) y refactor con los tests en verde (REFACTOR). Antes de tocar un archivo existente, safety net con sus tests. Los tests de integración corren en el contenedor (`pytest -m integration`). No leer ni editar `.env` ni `.env.example`. `domain/` sin imports de FastAPI, SQLAlchemy, Celery ni Redis; type hints en todo; TypeScript estricto sin `any`. Regla dura 6: la no superposición de turnos no se toca y lleva su test. Nada de datos de pacientes en mensajes de error ni registros. Sin commits ni push sin pedido explícito, y sin `Co-Authored-By`.

## 0. Confirmaciones de la usuaria (CONFIRMADAS el 2026-11-04, opción A en todas)

- [x] 0.1 Obtener respuesta a P-1 (formato y unicidad del documento), P-2 (obligatorios y límites; email no único) y P-9 (qué se edita) y marcarlas CONFIRMADAS en `design.md`; si P-1 = B o C, rehacer la spec `patient-data-rules` con `/opsx:update`
- [x] 0.2 Obtener respuesta a P-3 (búsqueda) y P-5 (límite de 50 y activos por defecto) y marcarlas CONFIRMADAS; si P-3 = B, agregar al design la migración `unaccent` y sus tasks (es la única opción que exige migración)
- [x] 0.3 Obtener respuesta a P-4 (permisos; qué pacientes ve el odontólogo) y P-6 (borrado definitivo) y marcarlas CONFIRMADAS; si P-4 = B, reescribir los requirements de lectura; si P-6 = B, quitar `DELETE`, `PATIENT_HAS_APPOINTMENTS`, los requirements de borrado y las tasks 2.6, 3.6 y la parte de borrar de 7.6
- [x] 0.4 Obtener respuesta a P-7 (desactivar con turnos futuros), P-8 (recordatorio de turnos de pacientes inactivos, nota para C-12) y P-10 (privacidad de búsquedas y registros) y marcarlas CONFIRMADAS
- [x] 0.5 Obtener respuesta a P-11 (pantalla en C-06) y P-12 (uno o dos changes); si alguna respuesta difiere de la recomendación, ajustar specs, design y tasks; registrar las decisiones como DD-73 en adelante en `knowledge-base/09_decisiones_y_supuestos.md`; verificar `openspec validate patients-crud --strict` en verde

## 1. Preparación y reglas puras — spec patient-data-rules

- [x] 1.1 Safety net: correr en el contenedor `pytest`, `pytest -m integration`, `mypy --strict app/`, `ruff check` y `npm test`; anotar los números en verde (C-07 dejó 1101 por defecto, 237 de integración y 117 de frontend); si algo falla, frenar y reportarlo como falla previa
- [x] 1.2 RED: `tests/unit/domain/patients/test_rules.py` con los 16 escenarios de `patient-data-rules` (documento con puntos, pasaporte, corto, carácter inválido, largo 20/21; nombres, email, 100/101; teléfono local, con letras, en blanco; fecha futura, hoy, cambio de día por zona, 1899); ver que fallan
- [x] 1.3 GREEN → TRIANGULATE → REFACTOR: `app/domain/patients/rules.py` y `errors.py` (D-1; reusa `normalize_email`/`is_valid_email`) con test de códigos `DOCUMENT_TAKEN`, `PATIENT_HAS_APPOINTMENTS`, `INVALID_PATIENT_DATA`; verificar en verde y `tests/unit/test_architecture.py` y `tests/contract/test_import_order.py` en verde

## 2. Repositorio ampliado — spec patient-repository

- [x] 2.1 REFACTOR con red: tipos `PatientRecord`, `NewPatient`, `PatientChanges` en `app/domain/patients/types.py` y métodos nuevos en el puerto (D-2) sin cambiar `get`; la batería actual de `tests/contract/test_patient_repository.py` y la suite de C-08 siguen con los números de 1.1
- [x] 2.2 RED: ampliar la batería de contrato con "Leer la ficha completa" (3) y "Alta con documento único" (3, sin el simultáneo) con la fábrica `in_memory`, ajustando la fábrica para cargar fichas completas; ver que fallan
- [x] 2.3 GREEN → REFACTOR: `get_record` y `add` en memoria y PostgreSQL (traducción de `23505` a `DocumentTakenError` sin registrar el detalle, D-3); verificar la batería con `in_memory` y con `postgres` (`pytest -m integration`)
- [x] 2.4 RED → GREEN → TRIANGULATE: "Buscar pacientes" (5 escenarios: apellido parcial con acento y mayúsculas, inicio de documento con puntos, inactivos, comodines, máximo) con ambas fábricas dando el mismo resultado; verificar en verde
- [x] 2.5 RED → GREEN: "Editar un paciente" (4) y "Activar y desactivar" (3, incluido que la regla RN-PA-04 ve el cambio por `get`); verificar con ambas fábricas
- [x] 2.6 RED → GREEN: "Borrar un paciente sin turnos" (3; el de turno cancelado solo con `postgres`, `23503` → `PatientHasAppointmentsError`) y test de integración de dos altas simultáneas con el mismo documento en dos sesiones (una `DOCUMENT_TAKEN`); verificar con `pytest -m integration`

## 3. Casos de uso (memoria, reloj fijo) — spec patient-management

- [x] 3.1 RED: `tests/unit/application/test_patients.py` con los 4 escenarios de permisos, los 3 de buscar y los 2 de ver; ver que fallan
- [x] 3.2 GREEN → TRIANGULATE: `app/application/patients.py` con `PatientDeps`, `search_patients` (51 → 50 + `truncated`), `get_patient` y chequeo de rol en el caso de uso (D-4); verificar en verde
- [x] 3.3 RED → GREEN → TRIANGULATE: `create_patient` y `update_patient` con los 3 escenarios de alta y los 3 de edición (fecha futura con reloj fijo en Buenos Aires; cambiar el email no toca el turno ni su notificación `pending`); verificar que un rechazo no guarda nada
- [x] 3.4 RED: los 6 escenarios de "Desactivar sin tocar los turnos" (incluidos agendar con el caso de uso de C-08 → `PATIENT_INACTIVE`, cancelar con C-08 permitido, inicio justo ahora no se lista, ya iniciado no se lista); ver que fallan
- [x] 3.5 GREEN → TRIANGULATE: `deactivate_patient` y `reactivate_patient` (2 escenarios de reactivar, agendando con C-08 tras reactivar); verificar que ningún turno ni notificación cambió (snapshot del repositorio de turnos)
- [x] 3.6 RED → GREEN: `delete_patient` con los 3 escenarios de borrado restringido (verificación previa con `list_for_patient`, D-4); verificar en verde
- [x] 3.7 Regla dura 6 y REFACTOR: escenario "Reactivar no habilita superponer" (`SLOT_TAKEN`, un solo turno `scheduled`); helpers comunes sin duplicar el cargador de C-08; suites de casos de uso de C-07, C-08 y C-06 en verde y `mypy --strict app/`

## 4. API — specs patient-api y error-model

- [x] 4.1 RED: `tests/unit/api/test_error_handlers.py` para `DOCUMENT_TAKEN`, `PATIENT_HAS_APPOINTMENTS` (409) e `INVALID_PATIENT_DATA` (400) con mensaje sin datos del paciente; ver que falla
- [x] 4.2 GREEN: ampliar `STATUS_BY_CODE` en `app/api/errors.py`; verificar en verde junto con los escenarios archivados de `error-model`
- [x] 4.3 RED: `tests/unit/api/test_patients_permissions.py`: tabla de los 7 endpoints × administrador, recepción, odontóloga con ficha, odontólogo sin ficha y sin token (401 antes que 403; 403 antes que 422 con cuerpo vacío; "nada cambió" en cada 401/403), con el patrón de `test_professionals_permissions.py`; ver que falla
- [x] 4.4 RED: `tests/unit/api/test_patients.py`: 6 escenarios de "Endpoints de pacientes" y 5 de "Validación de entrada sin eco" (sin email, documento inválido sin eco, fecha `0` → 422, fecha futura → 400, email `null` en `PATCH` → 422) más campo desconocido y fecha imposible `2026-02-30` → 422; ver que fallan
- [x] 4.5 GREEN: `app/api/patients.py` (esquemas de D-6, `require_role` en escrituras), `get_patient_deps` sobreescribible en `app/api/dependencies.py` e inclusión en `app/api/router.py`; verificar 4.3, 4.4 y `tests/unit/api/test_route_inventory.py` en verde
- [x] 4.6 REFACTOR: mover `_check_email` y los tipos de texto compartidos a `app/api/validators.py` sin cambiar `users.py` (sus tests en verde); `/openapi.json` lista las 7 operaciones nuevas con `HTTPBearer`; `mypy --strict app/` y `ruff check` en verde

## 5. Integración contra PostgreSQL — specs patient-api y patient-repository

- [x] 5.1 RED → GREEN: `tests/integration/test_patients_api.py` con el seed: la recepcionista da de alta a Laura Ruiz, la busca por `ruiz` y por `40.222`, la edita (borra el teléfono) y una segunda alta con `40.222.333` responde 409 `DOCUMENT_TAKEN` sin el documento en el cuerpo; verificar con `pytest -m integration`
- [x] 5.2 RED → GREEN: desactivar a Juan Pérez con un turno agendado del seed o creado en el test: el turno se lista, sigue `scheduled` en la base, agendarle otro da 409 `PATIENT_INACTIVE`, reactivarlo lo permite; el administrador borra a Laura (sin turnos, 204) y no puede borrar a Juan (409 `PATIENT_HAS_APPOINTMENTS`); verificar con `pytest -m integration`
- [x] 5.3 RED → GREEN: permisos de punta a punta con el seed: la Dra. A lee (200) y recibe 403 en cada escritura sin cambios en la base; la recepcionista recibe 403 en `DELETE`; verificar con `pytest -m integration`

## 6. Checkpoint backend (punto de corte seguro, P-12)

- [x] 6.1 Suite completa en verde (por defecto, integración, `mypy --strict app/`, `ruff check`; frontend sin cambios: `npm test` igual que en 1.1); anotar números. Si P-12 lo pide o el tiempo no alcanza, aquí se puede archivar el backend y dejar la pantalla como C-06b

## 7. Pantalla `/pacientes` — spec frontend-patient-management (si P-11 = A)

- [x] 7.1 RED → GREEN: `frontend/src/api/patients.test.ts` y `frontend/src/api/patients.ts` sobre `client.ts`: cliente tipado de los 7 endpoints (búsqueda con `q` e `include_inactive`, 204 del borrado, `phone: null` al borrar, errores con `error.code`); verificar con `npm test` y `tsc`
- [x] 7.2 RED: tests de acceso (recepción con controles sin "Borrar", administración con "Borrar", odontóloga en lectura, sin sesión a `/login`); ver que fallan
- [x] 7.3 GREEN: ruta `/pacientes` en `App.tsx` dentro de `RequireAuth`, enlace "Pacientes" y `PatientsPage.tsx` con modo según rol (D-7); verificar en verde. Cargar antes la skill `frontend-design:frontend-design` y la parte de React de `vercel-react-best-practices`
- [x] 7.4 RED → GREEN → TRIANGULATE: búsqueda y tabla (una llamada por 300 ms con temporizador falso, incluir inactivos, truncado, sin resultados, "Cargando…", error de red); verificar en verde
- [x] 7.5 RED → GREEN: `PatientForm` de alta y edición (alta correcta, `DOCUMENT_TAKEN` junto al documento conservando lo escrito, obligatorio vacío sin llamar a la API, teléfono vaciado → `phone: null`, 422 e `INVALID_PATIENT_DATA` con sus mensajes); verificar en verde
- [x] 7.6 RED → GREEN: desactivar con diálogo de confirmación y aviso de turnos en hora local (`jue 05/11 10:00`), cancelar la confirmación sin llamar a la API, reactivar, borrar (solo administración) con `PATIENT_HAS_APPOINTMENTS`; verificar en verde
- [x] 7.7 RED → GREEN → REFACTOR: `PatientSearch` reutilizable (solo activos, `onSelect` con id y nombre, inactivos no aparecen); componentes en `frontend/src/patients/` y mensajes en `patients/messages.ts`; `npm test`, `tsc` y `eslint` en verde

## 8. Cierre

- [x] 8.1 Prueba manual con Docker y la usuaria: seed, entrar como recepción, buscar por apellido y por documento con puntos, dar de alta un paciente, intentar un documento repetido, desactivar a un paciente con turno agendado y ver el aviso, reactivarlo; entrar como la Dra. A y comprobar el modo lectura; entrar como administración y borrar un paciente sin turnos
- [x] 8.2 Suite completa en verde (backend por defecto e integración, mypy, ruff, frontend `npm test`, `tsc`, `eslint`); anotar números finales; actualizar `CHANGES.md` (estado de C-06; notas para C-10 sobre `PatientSearch`/`PatientForm`, para C-12 sobre P-8 y para C-13 sobre P-10) y la KB con las DD confirmadas; verificar `openspec validate patients-crud --strict`
