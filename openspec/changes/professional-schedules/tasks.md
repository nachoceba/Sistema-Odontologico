# Tasks: professional-schedules (C-07)

> **Gobernanza MEDIA.** El grupo 0 (confirmaciones P-1 a P-11) está **HECHO**: la usuaria confirmó todas las recomendadas. Modo TDD estricto: en cada task de código, primero el test que falla (RED, se ejecuta y se ve fallar), después el mínimo código (GREEN), triangulación con un segundo caso (TRIANGULATE) y refactor con los tests en verde (REFACTOR). Antes de tocar un archivo existente, safety net con sus tests. Los tests de integración corren en el contenedor (`pytest -m integration`). No leer ni editar `.env` ni `.env.example`. `domain/` sin imports de FastAPI, SQLAlchemy, Celery ni Redis; type hints en todo; TypeScript estricto sin `any`. Todo cambio en la agenda lleva su test de no superposición (regla dura 6). Sin commits ni push sin pedido explícito, y sin `Co-Authored-By`.

## 0. Confirmaciones de la usuaria (HECHAS)

- [x] 0.1 Obtener respuesta a P-1 (cómo se marcan los conflictos), P-2 (aviso al paciente), P-3 (qué turnos cuentan) y P-5 (guardar igual con conflictos) y marcarlas CONFIRMADAS en `design.md`; si P-1 = B o P-2 = B, rehacer design y tasks con `/opsx:update` (requieren migración)
- [x] 0.2 Obtener respuesta a P-4 (borrar licencias) y P-10 (bordes de licencias) y marcarlas CONFIRMADAS; si P-4 = A, quitar el requirement de borrado de `schedule-repository`, el endpoint `DELETE` y las tasks 2.3, 2.4 y 3.6
- [x] 0.3 Obtener respuesta a P-6 (profesional inactivo), P-7 (listado) y P-8 (edición de la ficha) y marcarlas CONFIRMADAS
- [x] 0.4 Obtener respuesta a P-9 (pantalla en C-07) y P-11 (uno o dos changes) y marcarlas CONFIRMADAS; si P-9 = B, quitar la spec `frontend-professional-schedules` y el grupo 7; si P-11 = B, partir con `/opsx:update` después del grupo 6
- [x] 0.5 Si alguna respuesta difiere de la recomendación, ajustar specs, design y tasks; registrar las decisiones como DD-68 en adelante en `knowledge-base/09_decisiones_y_supuestos.md` y cerrar en `10_preguntas_abiertas.md` la pregunta "¿se avisa al paciente o solo a recepción?" (P-2); verificar `openspec validate professional-schedules --strict` en verde

## 1. Preparación y regla pura de conflictos — spec schedule-conflicts

- [x] 1.1 Safety net: correr en el contenedor `pytest`, `pytest -m integration`, `mypy --strict app/`, `ruff check` y `npm test`; anotar los números en verde (C-08 dejó 876 por defecto y 221 de integración); si algo falla, frenar y reportarlo como falla previa
- [x] 1.2 REFACTOR con red: extraer `_fits_in_working_hours` de `app/domain/appointments/validation.py` a una función pública compartida (D-1) sin cambiar comportamiento; verificar los tests archivados de C-05a a C-05c y los de C-08 con el mismo número que en 1.1
- [x] 1.3 RED: `tests/unit/domain/schedules/test_conflicts.py` con los 15 escenarios de `schedule-conflicts` (acortar horario, licencia, estados que no cuentan, inicio igual a `now`, fin justo en el tramo, a caballo entre tramos, fuera de grilla no cuenta, semana vacía, doble motivo, día local por zona, licencia inclusiva, medianoche local, otro profesional, `now` sin zona); ver que fallan
- [x] 1.4 GREEN → TRIANGULATE → REFACTOR: `app/domain/schedules/conflicts.py` (`find_schedule_conflicts`, `ScheduleConflict`, `ConflictReason`) y `app/domain/schedules/errors.py` (D-2) con test de códigos; verificar en verde, `tests/unit/test_architecture.py` y `tests/contract/test_import_order.py` en verde

## 2. Repositorios: editar ficha y borrar licencia — specs professional-repository y schedule-repository

- [x] 2.1 RED: ampliar `tests/contract/test_professional_repository.py` con los 4 escenarios de "Editar nombre a mostrar y matrícula" (incluido que en memoria el repositorio de cuentas ve el cambio) con la fábrica `in_memory`; ver que fallan
- [x] 2.2 GREEN → REFACTOR: método `update` en el puerto (D-4), `InMemoryProfessionalRepository` y `SqlAlchemyProfessionalRepository`; verificar la batería en verde con `in_memory` y con `postgres` (`pytest -m integration`)
- [x] 2.3 RED: ampliar `tests/contract/test_schedule_repository.py` con los 4 escenarios de "Borrar una licencia" (incluido "borrar devuelve la disponibilidad" con `compute_slots`); ver que fallan
- [x] 2.4 GREEN → REFACTOR: `delete` en `TimeOffRepository`, en memoria y PostgreSQL (D-5); verificar la batería de horarios completa en verde con ambas fábricas

## 3. Casos de uso (memoria, reloj fijo) — spec professional-schedule-use-cases

- [x] 3.1 RED: `tests/unit/application/test_professionals.py`: los 5 escenarios de "Listar y ver fichas" y los 4 de "Editar la ficha"; ver que fallan
- [x] 3.2 GREEN → TRIANGULATE: `app/application/professionals.py` con `ScheduleDeps`, `list_professionals`, `get_professional`, `update_professional` (alcance con `can_access_professional`, rol admin para escribir, D-3); verificar en verde
- [x] 3.3 RED: `tests/unit/application/test_working_hours.py`: los 8 escenarios de "Leer y reemplazar el horario semanal", incluido "cambiar el horario no habilita superponer turnos" (agendar encima con el caso de uso de C-08 → `SLOT_TAKEN`, regla dura 6) y "el cambio rige de inmediato" (agendar y franjas de C-08 con los mismos repositorios); ver que fallan
- [x] 3.4 GREEN → TRIANGULATE → REFACTOR: `get_working_hours` y `replace_working_hours` (validar, guardar, calcular conflictos desde `now`); segundo caso con otra zona de entrada y otro profesional; verificar que un rechazo no escribe nada
- [x] 3.5 RED: `tests/unit/application/test_time_off.py`: los 7 escenarios de "Listar, cargar y borrar licencias"; ver que fallan
- [x] 3.6 GREEN → TRIANGULATE: `list_time_off`, `add_time_off` (motivo recortado, vacío = sin motivo) y `delete_time_off` (`TIME_OFF_NOT_FOUND`); verificar en verde
- [x] 3.7 RED → GREEN: `list_conflicts` con los 4 escenarios de "Consultar los turnos en conflicto" (resolver cancelando o reprogramando con los casos de uso de C-08 lo saca de la lista) y los 3 de "Solo el administrador escribe" (nada cambia en cada `FORBIDDEN`); verificar en verde
- [x] 3.8 REFACTOR: helpers comunes (cargar profesional, calcular conflictos) sin duplicar el cargador de C-08; suite de casos de uso de C-08 y C-07 en verde, `mypy --strict app/`

## 4. API — specs professional-schedule-api y error-model

- [x] 4.1 RED: `tests/unit/api/test_error_handlers.py` para `INVALID_WORKING_HOURS`, `INVALID_TIME_OFF` (400) y `TIME_OFF_NOT_FOUND` (404); ver que falla
- [x] 4.2 GREEN: ampliar `STATUS_BY_CODE` en `app/api/errors.py`; verificar en verde junto con los escenarios archivados de error-model
- [x] 4.3 RED: `tests/unit/api/test_professionals_permissions.py`: tabla de los nueve endpoints × administrador, recepción, odontóloga propia, odontóloga ajena, odontólogo sin ficha y sin token (401 antes que 403; 403 antes que 422 con cuerpo inválido; "nada cambió" en cada 401/403), con el patrón de `test_appointments_permissions.py`; ver que falla
- [x] 4.4 RED: `tests/unit/api/test_professionals.py`: escenarios de "Endpoints de profesionales, horarios y licencias" y de "Validación de entrada" (horas con segundos, con zona y `24:00` → 422 sin eco; día 7 → 400; licencia invertida → 400; motivo de 501 → 422; nombre vacío → 422; `license_number: null` borra y campo ausente no cambia; la ficha no expone la cuenta; franjas sin cambios); ver que fallan
- [x] 4.5 GREEN: `app/api/professionals.py` (esquemas de D-6, `require_role(Role.ADMIN)` en escrituras), `get_schedule_deps` sobreescribible en `app/api/dependencies.py` e inclusión en `app/api/router.py`; verificar 4.3, 4.4 y `tests/unit/api/test_route_inventory.py` en verde
- [x] 4.6 REFACTOR: validadores compartidos (hora `HH:MM`, textos) y conversiones de salida; todo en verde; `/openapi.json` lista las nueve operaciones nuevas con `HTTPBearer`; `mypy --strict app/` y `ruff check` en verde

## 5. Integración contra PostgreSQL — specs professional-schedule-api y schedule-repository

- [x] 5.1 RED → GREEN: `tests/integration/test_professionals_api.py` con el seed: el administrador reemplaza el horario de la Dra. A y las franjas reales cambian; carga una licencia sobre un turno agendado y el turno se lista en conflicto y sigue `scheduled` en la base; borra la licencia y las franjas vuelven; edita nombre a mostrar y matrícula; verificar con `pytest -m integration`
- [x] 5.2 RED → GREEN: punta a punta de DD-53 con el seed: la Dra. A recibe 403 en horario, licencias y conflictos del Dr. B y en cualquier escritura propia; recepción recibe 403 en el `PUT` de horario y el horario en la base no cambia; verificar con `pytest -m integration`
- [x] 5.3 Regla dura 6 contra PostgreSQL: tras cambiar el horario de la Dra. A, agendar encima de un turno existente responde 409 `SLOT_TAKEN` y en la base sigue habiendo un solo turno `scheduled` en ese horario; verificar con `pytest -m integration`

## 6. Checkpoint backend (punto de corte seguro, P-11)

- [x] 6.1 Suite completa en verde (por defecto, integración, `mypy --strict app/`, `ruff check`; frontend sin cambios: `npm test` igual que en 1.1); anotar números. Si P-11 lo pide o el tiempo no alcanza, aquí se puede archivar el backend y dejar la pantalla como C-07b

## 7. Pantalla `/profesionales` — spec frontend-professional-schedules (si P-9 = A)

- [x] 7.1 RED: `frontend/src/api/professionals.test.ts`: cliente tipado de los nueve endpoints (cuerpos, 204 del borrado, errores con `error.code`); ver que falla
- [x] 7.2 GREEN: `frontend/src/api/professionals.ts` sobre `client.ts`; verificar con `npm test` y `tsc`
- [x] 7.3 RED: tests de acceso (4 escenarios: admin con controles, recepción en lectura, odontóloga solo lo suyo, sin sesión a `/login`; odontólogo sin ficha ve el aviso); ver que fallan
- [x] 7.4 GREEN: ruta `/profesionales` en `App.tsx` dentro de `RequireAuth`, enlace "Profesionales" y `ProfessionalsPage.tsx` con modo según rol (D-7); verificar en verde
- [x] 7.5 RED → GREEN: listado y edición de ficha (ficha inactiva marcada, nombre vacío sin llamar a la API, "Cargando…", error de red); verificar en verde
- [x] 7.6 RED → GREEN → TRIANGULATE: editor semanal (dos tramos el lunes, superposición 400 mostrada junto al día sin perder lo escrito, aviso de conflictos con hora local `lun 05/10 16:00`); verificar en verde
- [x] 7.7 RED → GREEN: licencias (agregar, fechas invertidas sin llamar a la API, confirmar y cancelar el borrado, conflictos tras agregar); verificar en verde
- [x] 7.8 REFACTOR: componentes en `frontend/src/professionals/` y mensajes en `professionals/messages.ts`; `npm test`, `tsc` y `eslint` en verde; cargar la skill `frontend-design:frontend-design` y la parte de React de `vercel-react-best-practices` antes de 7.4

## 8. Cierre

- [ ] 8.1 Prueba manual con Docker: seed, entrar como administrador, cambiar el horario de la Dra. A dejando un turno afuera y ver el aviso; cargar y borrar una licencia; entrar como recepción y ver la pantalla en lectura y la consulta de conflictos; entrar como la Dra. A y comprobar que solo ve lo suyo
- [x] 8.2 Suite completa en verde (backend por defecto e integración, mypy, ruff, frontend `npm test`, `tsc`, `eslint`); anotar números finales
- [x] 8.3 Actualizar `CHANGES.md` (estado de C-07; corregir "C-07 agrega el adaptador SQLAlchemy", ya existía desde C-02; nota para C-09 y C-10 sobre `GET /professionals/{id}/conflicts`) y la KB con las DD confirmadas; verificar `openspec validate professional-schedules --strict`
