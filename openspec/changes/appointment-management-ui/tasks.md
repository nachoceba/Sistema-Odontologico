# Tasks: appointment-management-ui (C-10)

> **Gobernanza MEDIA.** El grupo 0 (confirmaciones P-1 a P-9) está **CONFIRMADO** por la usuaria con la opción A en todas (DD-84 a DD-86). Implementar con checkpoints al final de cada grupo y mostrar las decisiones no obvias. Modo TDD estricto: en cada task de código, primero el test que falla (RED, se ejecuta y se ve fallar), después el mínimo código (GREEN), triangulación con un segundo caso (TRIANGULATE) y refactor con los tests en verde (REFACTOR). Antes de tocar un archivo existente, safety net con sus tests. Solo frontend: el backend, `domain/`, el constraint y las migraciones no se tocan (regla dura 6) y su suite corre como red. TypeScript estricto sin `any`. Nada de datos de pacientes en mensajes de error ni registros. Sin variables de entorno ni dependencias nuevas. No leer ni editar `.env` ni `.env.example`. Sin commits ni push sin pedido explícito, y sin `Co-Authored-By`.

## 0. Confirmaciones de la usuaria (CONFIRMADAS, opción A)

- [x] 0.1 Obtener respuesta a P-1 (qué franjas ofrecen "Agendar") y P-8 (indicador de conflictos) y marcarlas CONFIRMADAS en `design.md`; si P-1 = B o P-8 = B, sumar con `/opsx:update` un grupo de backend (endpoint o campo nuevo, tests de casos de uso, tabla de permisos por rol, integración) y la delta de `appointment-api` o `professional-schedule-api`; si P-8 = C, quitar el requirement "Turnos en conflicto con acceso a resolverlos" y el grupo 9
- [x] 0.2 Obtener respuesta a P-2 (motivo), P-3 (cómo se elige el horario nuevo), P-4 (confirmación al marcar) y P-5 (dónde están las acciones) y marcarlas CONFIRMADAS; si alguna difiere, ajustar los requirements de `frontend-appointment-management` y los grupos 5, 7 y 8
- [x] 0.3 Obtener respuesta a P-6 (aviso de tildes), P-7 (qué pasa tras un rechazo) y P-9 (uno o dos changes) y marcarlas CONFIRMADAS; si P-6 = C, sumar la delta de `frontend-patient-management`; si P-9 = B, partir el change con `/opsx:update`
- [x] 0.4 Preguntar a la usuaria si marca como RESUELTA en `10_preguntas_abiertas.md` la pregunta de urgencias cerrada por DD-65 (hallazgo 8); registrar las decisiones como DD-84 en adelante en `knowledge-base/09_decisiones_y_supuestos.md` y verificar `openspec validate appointment-management-ui --strict` en verde

## 1. Preparación y safety net

- [ ] 1.1 Safety net: correr en el contenedor `pytest`, `pytest -m integration`, `mypy --strict app/`, `ruff check`, y en el frontend `npm test`, `tsc` y `eslint`; anotar los números en verde (C-09 dejó 1349 por defecto, 279 de integración y 249 de frontend); si algo falla, frenar y reportarlo como falla previa

## 2. Cliente de escritura — spec frontend-appointment-management

- [x] 2.1 RED: en `frontend/src/api/appointments.test.ts`, con `fetch` simulado, casos de `bookAppointment` (`POST /appointments` con `patient_id`, `professional_id`, `starts_at` tal como vino de la franja), `cancelAppointment` (`POST /appointments/{id}/cancel` con `reason`), `rescheduleAppointment` (`POST .../reschedule` con `starts_at`), `recordAttendance` (`POST .../attendance` con `completed` o `no_show`) y `getAppointment` (`GET /appointments/{id}`); un 409 `SLOT_TAKEN` llega como `ApiError` con `code`; ver que fallan
- [x] 2.2 GREEN → TRIANGULATE → REFACTOR: funciones y tipo `AppointmentRecord` en `frontend/src/api/appointments.ts` (D-3), reusando `request`; verificar 2.1, los tests previos del archivo, `tsc` y `eslint` en verde

## 3. Reglas puras de acciones y mensajes — spec frontend-appointment-management

- [x] 3.1 RED: `frontend/src/appointments/actions.test.ts` con tablas de la spec "Qué acciones ve cada rol": recepción con franja libre futura y turno agendado futuro; odontóloga con turno iniciado (solo marcar) y sin "Agendar"; franja libre ya iniciada sin "Agendar"; turno en su inicio exacto (marcar sí, cancelar y reprogramar no, DD-23); profesional inactivo (sin agendar ni reprogramar, con cancelar); cancelado, atendido y ausente sin acciones; odontólogo con turno ajeno sin acciones; ver que fallan
- [x] 3.2 GREEN → TRIANGULATE → REFACTOR: `slotActions` y `appointmentActions` en `frontend/src/appointments/actions.ts` (D-1, `now` como dato); verificar 3.1 en verde con al menos dos casos por regla
- [x] 3.3 RED: `frontend/src/appointments/messages.test.ts`: cada código de la tabla da su texto exacto; 403 → "No tenés permiso para esta acción"; 422 → "Revisá los datos ingresados"; error de red y 500 → "No se pudo conectar con el servidor"; código desconocido → mensaje de la API; `shouldReloadAfter` verdadero para los códigos de la tabla y falso para red, 403 y 422; ver que fallan
- [x] 3.4 GREEN → REFACTOR: `messageForAppointmentError`, `shouldReloadAfter`, textos de éxito y etiquetas en `frontend/src/appointments/messages.ts` (D-2); verificar 3.3, `tsc` y `eslint` en verde

## 4. Grilla con acciones opcionales — specs frontend-agenda y frontend-appointment-management

- [x] 4.1 Safety net de `agenda/` (`day.test.tsx`, `week.test.tsx`, `access.test.tsx`, `grid.test.ts`) en verde; RED: en `frontend/src/agenda/day.test.tsx` casos nuevos: con `onBookSlot` y `canBook`, la franja libre futura muestra "Agendar" y al apretarlo avisa la franja; con `onSelectAppointment`, el turno es un botón que avisa su `id`; sin esas props no hay ningún botón (comportamiento de C-09); ver que fallan
- [x] 4.2 GREEN → REFACTOR: props opcionales en `DayColumn` y paso en `WeekView` (D-5), estilos del botón "Agendar" en `styles.css` (D-7); verificar 4.1 y toda la carpeta `agenda/` en verde sin cambiar los tests de C-09

## 5. Detalle del turno y cancelar — spec frontend-appointment-management

- [x] 5.1 RED: `frontend/src/appointments/detail.test.tsx`: detalle de un turno agendado con fecha y hora local, "Perez, Juan", "Agendado", "Cancelar" y "Reprogramar"; turno cancelado con "Motivo: …" sin acciones; turno en conflicto con su aviso; ningún email, teléfono ni documento; abrirlo no envía pedidos de escritura; ver que fallan
- [x] 5.2 GREEN → REFACTOR: `AppointmentDetail` y el panel lateral (D-4, D-7; foco y Escape como `ConfirmDialog`); verificar 5.1 en verde
- [x] 5.3 RED: `frontend/src/appointments/cancel.test.tsx`: cancelar con motivo envía un solo `POST .../cancel` y avisa "Turno cancelado"; motivo "   " muestra "Escribí el motivo de la cancelación" sin llamar a la API; campo limitado a 500 caracteres; `ALREADY_STARTED` y `CANCELLED_IS_FINAL` con su mensaje y pedido de recarga; "Volver" sin llamada; paciente inactivo cancelado con 200; doble clic envía uno; ver que fallan
- [x] 5.4 GREEN → REFACTOR: `CancelDialog` y hook `useAppointmentAction` (D-4: ref de "en vuelo", error traducido, éxito); verificar 5.3 y 5.1 en verde

## 6. Agendar desde una franja libre (punto de corte seguro 1, P-9)

- [x] 6.1 RED: `frontend/src/appointments/booking.test.tsx`: el panel muestra "Lun 09/11 10:00–10:30" y el profesional; "Agendar turno" deshabilitado sin paciente; elegir a Lucía Torres con el buscador muestra "Paciente: Torres, Lucía" y "Cambiar"; aviso de tildes visible y también con "No se encontraron pacientes" al buscar `perez`; inactivos no aparecen; "Nuevo paciente" con alta correcta deja a "Ruiz, Laura" elegida; `DOCUMENT_TAKEN` en el alta sin paciente elegido; "Cerrar" sin pedidos de escritura; ver que fallan
- [x] 6.2 GREEN → REFACTOR: `BookingPanel` reusando `PatientSearch` y `PatientForm` sin modificarlos (D-4, P-6); verificar 6.1 y los tests de `patients/` en verde
- [x] 6.3 RED: agendar en `booking.test.tsx`: un solo `POST /appointments` con el inicio de la franja, aviso "Turno agendado: Perez, Juan, Lun 09/11 10:00" sin mención de emails; `SLOT_TAKEN`, `INSUFFICIENT_NOTICE` y `PATIENT_DOUBLE_BOOKED` con su texto, panel abierto y paciente conservado; red caída con el panel abierto; paciente creado y turno rechazado sigue elegido; doble clic envía uno; ver que fallan
- [x] 6.4 GREEN → REFACTOR: envío del turno en `BookingPanel` y en `AgendaPage` el estado `panel` y el `notice` (D-6), con recarga tras éxito y tras rechazo con código (P-7); flujos en `frontend/src/appointments/flows.test.tsx`: "agendar" (la franja pasa a "Ocupado" con "10:00–10:30 Perez, Juan") y "choque de slot" (`SLOT_TAKEN` y la franja pasa a "Ocupado" al recargar), y "cancelar libera la franja" (vuelve "Libre" con "Agendar" y el turno tachado); checkpoint: `npm test`, `tsc`, `eslint` en verde y números anotados. Si P-9 lo pide o el tiempo no alcanza, aquí se puede cerrar el change con detalle, agendar y cancelar

## 7. Reprogramar — spec frontend-appointment-management

- [x] 7.1 RED: `frontend/src/appointments/reschedule.test.tsx`: al abrir, la fecha del turno y sus franjas libres no iniciadas (pide `GET .../slots?date=`); la franja del propio turno no se ofrece; cambiar a otro día vuelve a pedir; día sin franjas o de licencia → "No hay horarios libres este día"; elegir 11:00 muestra "Mover de Lun 09/11 10:00 a Mar 10/11 11:00"; "Volver" sin escritura; ver que fallan
- [x] 7.2 GREEN → REFACTOR: `RescheduleDialog` (D-4, P-3) con `getDaySlots` y `slotActions` para filtrar las franjas; verificar 7.1 en verde
- [x] 7.3 RED → GREEN → TRIANGULATE: envío y flujo: un solo `POST .../reschedule`, aviso "Turno reprogramado: Mar 10/11 11:00", la franja vieja vuelve a "Libre" (flujo "reprogramar" en `flows.test.tsx`); `SLOT_TAKEN` y `PATIENT_INACTIVE` con su texto y el turno sin cambios al recargar; profesional inactivo sin "Reprogramar"; verificar en verde

## 8. Marcar atención (punto de corte seguro 2, P-9)

- [x] 8.1 RED: `frontend/src/appointments/attendance.test.tsx` con hora fija: la Dra. A a las 10:10 marca "Atendido" con confirmación "¿Marcar a Perez, Juan como atendido?" y "Después no se puede cambiar", un solo `POST .../attendance` con `completed` y "Asistencia registrada"; recepción marca "Ausente" (`no_show`); `ATTENDANCE_ALREADY_RECORDED` y `NOT_STARTED_YET` con su texto; cancelar la confirmación no llama a la API; ver que fallan
- [x] 8.2 GREEN → REFACTOR: confirmación con `ConfirmDialog` de C-06 (P-4) conectada al detalle y a la página; verificar 8.1; checkpoint: `npm test`, `tsc`, `eslint` en verde y números anotados

## 9. Turnos en conflicto con acceso a resolverlos — spec frontend-appointment-management y frontend-agenda

- [x] 9.1 RED: `frontend/src/appointments/conflicts.test.tsx`: con dos conflictos del 12/11 en licencia y la semana del 02/11 a la vista, recepción ve "2 turnos en conflicto" con fecha, hora, nombre (pedido con `GET /appointments/{id}`), motivo y "Reprogramar", "Cancelar", "Ver en la agenda"; "1 turno en conflicto" en singular; sin conflictos no hay aviso; la odontóloga no ve el aviso; profesional inactivo solo con "Cancelar" y "Ver en la agenda"; "Ver en la agenda" abre la vista "Día" del 12/11; ver que fallan
- [x] 9.2 GREEN → REFACTOR: `ConflictsPanel` (D-4, P-8) con los conflictos que expone `useAgendaData` (D-5); verificar 9.1 y los tests de `agenda/` en verde
- [x] 9.3 RED → GREEN: flujos en `flows.test.tsx`: cancelar desde la lista deja "1 turno en conflicto"; reprogramar desde la lista al 16/11 lo saca de la lista y lo muestra sin marca; `PROFESSIONAL_TIME_OFF` deja el turno en la lista; recepción abre un turno en conflicto desde la grilla con "Reprogramar" y "Cancelar" y la odontóloga sin ellos (delta `frontend-agenda`); verificar en verde

## 10. Pedidos de la agenda — delta frontend-agenda

- [x] 10.1 RED → GREEN: en `frontend/src/agenda/access.test.tsx` reemplazar el caso "solo pedidos `GET`" de C-09 por los escenarios de "Pedidos y actualización de la agenda": recorrer la semana y abrir dos detalles solo hace `GET`; después de agendar se vuelve a pedir sin "Actualizar"; "Actualizar" trae lo nuevo; la odontóloga solo envía `POST .../attendance`; nunca `PUT`, `PATCH` ni `DELETE`; verificar `npm test`, `tsc` y `eslint` en verde

## 11. Verificación final y documentación

- [ ] 11.1 Suite completa en verde: `pytest`, `pytest -m integration`, `mypy --strict app/`, `ruff check` (backend sin cambios, regla dura 6), `npm test`, `tsc`, `eslint`; `openspec validate appointment-management-ui --strict`; anotar los números finales y compararlos con 1.1 (ningún test previo se perdió)
- [ ] 11.2 Recorrido en el navegador con el seed (lo confirma la usuaria): recepción agenda creando un paciente, ve el choque de slot con dos pestañas, cancela, reprograma y resuelve un conflicto de licencia; la Dra. A marca un turno iniciado; en el teléfono el panel ocupa el ancho completo
- [ ] 11.3 Documentación: entrada C-10 de `CHANGES.md` (estado, números, nota para C-11 sobre el aviso de éxito), propósito de `openspec/specs/frontend-agenda/spec.md` actualizado al archivar (deja de decir "solo lectura"), `CLAUDE.md`/`AGENTS.md` sincronizados; verificar que las rutas citadas existen
