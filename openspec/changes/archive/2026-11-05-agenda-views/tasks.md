# Tasks: agenda-views (C-09)

> **Gobernanza BAJA.** El grupo 0 (confirmaciones P-1 a P-11) fue **CONFIRMADO** por la usuaria el 2026-11-04 (todas la opción A). Las tasks están escritas con la opción recomendada (A) de cada pregunta. Modo TDD estricto: en cada task de código, primero el test que falla (RED, se ejecuta y se ve fallar), después el mínimo código (GREEN), triangulación con un segundo caso (TRIANGULATE) y refactor con los tests en verde (REFACTOR). Antes de tocar un archivo existente, safety net con sus tests. Los tests de integración corren en el contenedor (`pytest -m integration`). No leer ni editar `.env` ni `.env.example`. `domain/` no se toca (y nunca importa FastAPI, SQLAlchemy, Celery ni Redis); type hints en todo; TypeScript estricto sin `any`. Regla dura 6: la vista es de solo lectura, no se toca el constraint ni las reglas de agenda, y la suite de C-08 corre como red. Nada de datos de pacientes en mensajes de error ni registros. Sin migraciones ni variables de entorno nuevas. Sin commits ni push sin pedido explícito, y sin `Co-Authored-By`.

## 0. Confirmaciones de la usuaria (CONFIRMADAS el 2026-11-04, todas la opción A)

- [x] 0.1 Obtener respuesta a P-1 (nombre del paciente en el listado) y P-7 (qué datos del paciente se ven) y marcarlas CONFIRMADAS en `design.md`; si P-1 = B, quitar los grupos 1 a 3 y las deltas `appointment-use-cases`/`appointment-api` y pedir los pacientes desde el frontend; si P-1 = C, rehacer el design con un endpoint de agenda nuevo y sus tests de permisos; si P-1 = D o P-7 = C, quitar los nombres de las specs
- [x] 0.2 Obtener respuesta a P-2 (vistas día y semana), P-3 (qué horas se muestran) y P-4 (cancelados, atendidos y ausentes) y marcarlas CONFIRMADAS; si alguna difiere, ajustar los requirements de `frontend-agenda` con `/opsx:update`
- [x] 0.3 Obtener respuesta a P-5 (licencias y conflictos), P-6 (uno o varios profesionales) y P-8 (inicio por rol y profesionales inactivos) y marcarlas CONFIRMADAS; si P-6 = B, dejarlo como pregunta para C-12 (necesita el listado global, DD-66)
- [x] 0.4 Obtener respuesta a P-9 (solo lectura), P-10 (actualización) y P-11 (uno o dos changes) y marcarlas CONFIRMADAS
- [x] 0.5 Registrar las decisiones como DD-79 en adelante en `knowledge-base/09_decisiones_y_supuestos.md` (actualizando el texto de DD-51 sobre la página provisoria), ajustar specs/design/tasks si alguna respuesta difiere de la recomendada y verificar `openspec validate agenda-views --strict` en verde

## 1. Preparación y safety net

- [x] 1.1 Safety net: correr en el contenedor `pytest`, `pytest -m integration`, `mypy --strict app/`, `ruff check`, `npm test`, `tsc` y `eslint`; anotar los números en verde (C-06 dejó 1320 por defecto, 277 de integración con 1 omitido y 160 de frontend); si algo falla, frenar y reportarlo como falla previa

## 2. Consulta con nombre del paciente — specs appointment-use-cases y appointment-api

- [x] 2.1 RED: en `backend/tests/unit/application/test_query_appointments.py` agregar los escenarios de "Consultar turnos" con nombres (semana con nombres, paciente inactivo sigue nombrado, nombre vigente tras editar, solo nombre y apellido, turno ajeno → `FORBIDDEN` sin leer pacientes, consultar no cambia nada con snapshot de turnos y notificaciones) usando `agenda_helpers.py`; ver que fallan
- [x] 2.2 GREEN → TRIANGULATE → REFACTOR: `AppointmentView`, `list_appointment_views` y `get_appointment_view` en `app/application/appointments.py` (D-1: reusan `list_appointments`/`get_appointment`, una lectura por paciente distinto con un repositorio espía que cuenta llamadas); verificar los tests de 2.1, `test_query_appointments.py` completo y `mypy --strict app/` en verde
- [x] 2.3 RED: en `backend/tests/unit/api/test_appointments.py` los escenarios "Listado con nombre del paciente", "Detalle con nombre del paciente" (claves exactas: sin `email`, `phone`, `document_number`, `birth_date`) y "Agendar no cambia de forma"; en `test_appointments_permissions.py` repetir la tabla de listado y detalle (administración, recepción, odontóloga propia, odontóloga ajena con cuerpo sin nombres, odontólogo sin ficha, sin token con 401 antes que 403); ver que fallan
- [x] 2.4 GREEN → REFACTOR: `AppointmentViewOut` en `app/api/appointments.py` solo para `GET /appointments` y `GET /appointments/{id}` (D-2); verificar 2.3, `test_route_inventory.py`, `test_openapi_auth.py` y toda `tests/unit/api/` en verde

## 3. Integración contra PostgreSQL (punto de corte seguro 1, P-11)

- [x] 3.1 RED → GREEN: en `backend/tests/integration/test_appointments_api.py`, con el seed: recepción agenda a Juan Perez con la Dra. A, lista la semana y ve `patient_first_name = "Juan"` y `patient_last_name = "Perez"`; se desactiva a Juan y sigue apareciendo nombrado y `scheduled`; la Dra. A recibe 403 sin nombres al pedir el listado del Dr. B; verificar con `pytest -m integration`
- [x] 3.2 Checkpoint backend: suite completa en verde (por defecto, integración, `mypy --strict app/`, `ruff check`), suite de C-08 sin cambios en sus resultados (regla dura 6); anotar números. Si P-11 lo pide o el tiempo no alcanza, aquí se puede archivar el backend y dejar la pantalla como C-09b

## 4. Cliente y fechas del frontend — spec frontend-agenda

- [x] 4.1 RED → GREEN: `frontend/src/api/appointments.test.ts` y `frontend/src/api/appointments.ts` (D-3): `listAppointments` (parámetros `professional_id`, `from`, `to` codificados) y `getDaySlots` (`date`), tipos con uniones de literales para estados, errores con `error.code`; verificar con `npm test` y `tsc`
- [x] 4.2 RED: `frontend/src/agenda/dates.test.ts` con tablas: hoy en el consultorio a las 01:00 UTC del martes → lunes, `addDays` cruzando fin de mes y de año, `weekDays` de un jueves → lunes a domingo, `parseIsoDate("2026-02-30")` inválida, `formatLocalTime("2026-11-09T12:00:00Z")` → `09:00`, `formatDayLabel` → `Lun 09/11`; ver que fallan
- [x] 4.3 GREEN → TRIANGULATE → REFACTOR: `frontend/src/agenda/dates.ts` con `Date.UTC` e `Intl.DateTimeFormat#formatToParts` y `CLINIC_TIMEZONE` (D-4); verificar en verde con un segundo caso por función

## 5. Armado de la columna de un día (funciones puras) — spec frontend-agenda

- [x] 5.1 RED: `frontend/src/agenda/grid.test.ts` con los escenarios de "Vista del día": día de la Dra. A con turno y banda 13:00–14:00, día sin atención, resto de tramo que no alcanza, turno desalineado, turno fuera de horario que estira el rango, turno que cruza la medianoche en los dos días; ver que fallan
- [x] 5.2 GREEN → TRIANGULATE: `buildDayColumn` en `frontend/src/agenda/grid.ts` (D-3: filas `free`, `busy`, `outside`, `appointment`); verificar en verde
- [x] 5.3 RED → GREEN: escenarios de "Turnos y sus estados" (cancelado deja la franja libre, atendido y ausente, cancelado y nuevo turno en la misma hora) y de "Licencias y conflictos" (día de licencia con y sin motivo, turno agendado en licencia con "En conflicto: en licencia", turno fuera del horario nuevo, turno pasado en licencia sin aviso); verificar en verde
- [x] 5.4 REFACTOR: nombres y tipos de las filas pensados para C-10 (identificador del turno y de la franja en cada fila), sin cambiar comportamiento; `npm test`, `tsc` y `eslint` en verde

## 6. Vista del día y página `/agenda` (punto de corte seguro 2, P-11)

- [x] 6.1 RED: tests de componentes con `fetch` simulado (`frontend/src/agenda/day.test.tsx`): `DayColumn` muestra "Libre", "Ocupado" con "10:00–10:30 Perez, Juan" y "Fuera de horario 13:00–14:00" como texto, "Sin atención este día", "Licencia: Congreso", ningún email/teléfono/documento, y ningún botón de agendar/cancelar/reprogramar/marcar; ver que fallan
- [x] 6.2 GREEN → REFACTOR: `DayColumn` y estilos en `styles.css` (estados por texto y clase, no solo color); verificar 6.1
- [x] 6.3 RED: tests de acceso y carga (`frontend/src/agenda/access.test.tsx`): recepción elige al Dr. B y la dirección cambia; primer profesional activo por defecto con inactivo marcado; profesional inactivo con su aviso; Dra. A sin selector y sin pedidos de otros; Dra. A con `?profesional={Dr. B}` ve la suya y no se pide la del Dr. B; odontólogo sin ficha sin pedidos de turnos ni franjas; sin profesionales; sin sesión → `/login`; "Cargando…", red caída con "Reintentar", 403 sin cerrar sesión; enlaces según rol (recepción sin "Usuarios"); solo pedidos `GET`; ver que fallan
- [x] 6.4 GREEN: `ProfessionalPicker`, `AppNav` (extraída de la página provisoria), `frontend/src/pages/AgendaPage.tsx` con vista "Día", estado en la dirección con `useSearchParams` (D-5), descarte de respuestas viejas (D-4) y botón "Actualizar"; `App.tsx` usa `AgendaPage` y se borra `AgendaPlaceholderPage.tsx`; verificar 6.3 y los tests existentes de `App.test.tsx`
- [x] 6.5 RED → GREEN: actualizar el escenario "Con sesión en la agenda" de `frontend-auth` en `App.test.tsx` (la odontóloga ve su agenda de hoy con nombre y rol en la barra) y "Actualizar trae lo nuevo"; verificar `npm test`, `tsc` y `eslint` en verde

## 7. Vista de la semana y navegación — spec frontend-agenda

- [x] 7.1 RED: `frontend/src/agenda/week.test.tsx`: semana con sábado y domingo "Sin atención este día", fecha jueves → lunes a domingo, hoy destacado, elegir el miércoles abre la vista "Día" del 11/11, licencia del jueves y viernes; ver que fallan
- [x] 7.2 GREEN → REFACTOR: `WeekView` (siete `DayColumn`, siete pedidos de franjas en paralelo y un solo pedido de turnos con el rango de las franjas, D-4); verificar 7.1
- [x] 7.3 RED → GREEN → TRIANGULATE: `DateNavigator` y la página: "Siguiente" en semana → 16/11, "Anterior"/"Siguiente" en día mueven un día, "Hoy" según el consultorio, fecha inválida en la dirección → hoy y "Día" sin error, recargar mantiene profesional, fecha y vista; verificar en verde

## 8. Verificación final

- [x] 8.1 Suite completa en verde: `pytest`, `pytest -m integration`, `mypy --strict app/`, `ruff check`, `npm test`, `tsc`, `eslint`; `openspec validate agenda-views --strict`; anotar los números finales y compararlos con 1.1 (ningún test previo se perdió)
- [ ] 8.2 Prueba manual con navegador y el seed (la confirma la usuaria): recepción mira el día y la semana de la Dra. A y del Dr. B, ve libres/ocupados/fuera de horario, un turno cancelado tachado y una licencia; la Dra. A ve solo la suya; el administrador ve "Usuarios" en la barra
- [x] 8.3 Documentación: entrada C-09 de `CHANGES.md` (estado, números, nota para C-10 sobre `DayColumn`, `api/appointments.ts` y los campos `patient_first_name`/`patient_last_name`), `CLAUDE.md`/`AGENTS.md` sincronizados; verificar que las rutas citadas existen
