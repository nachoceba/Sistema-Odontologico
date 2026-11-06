# Design: appointment-management-ui (C-10)

> **Gobernanza MEDIA.** Las decisiones P-1 a P-9 están **CONFIRMADAS** por la usuaria, todas con la opción recomendada (A), y registradas como DD-84 a DD-86 en `knowledge-base/09_decisiones_y_supuestos.md`.

## Context

Ver `proposal.md` (Why). Estado actual que define el enfoque:

- **Backend ya hecho (C-08, C-07)**: `POST /appointments` (`patient_id`, `professional_id`, `starts_at` con zona), `POST /appointments/{id}/cancel` (`reason`, 1 a 500 caracteres tras recortar), `POST /appointments/{id}/reschedule` (`starts_at`), `POST /appointments/{id}/attendance` (`status`: `completed` o `no_show`) devuelven el turno sin nombre del paciente; `GET /appointments/{id}` y el listado lo traen con `patient_first_name`/`patient_last_name` (DD-79). Rechazos con `error.code` y el estado de `STATUS_BY_CODE` (`appointment-api`). Matriz: agendar, cancelar y reprogramar solo administración y recepción; marcar, también el odontólogo con sus turnos (DD-64). `GET /professionals/{id}/conflicts` devuelve turnos `scheduled` no iniciados en conflicto con solo `patient_id` (sin nombre) y el motivo. **No hay endpoint de configuración del consultorio**: el frontend no conoce `min_notice_hours` ni `slot_minutes` (P-1).
- **Frontend ya hecho (C-09, C-06)**: `AgendaPage` con estado en la dirección, `useAgendaData` (franjas, licencias, conflictos y turnos; descarta respuestas viejas; `reloadKey`), `buildDayColumn` puro con filas `free`/`busy`/`outside`/`appointment` y `AppointmentItem` con `id`; `DayColumn` y `WeekView` de solo lectura; mensajes en `agenda/messages.ts`; fechas en `agenda/dates.ts` con `CLINIC_TIMEZONE`. De C-06: `PatientSearch` (`onSelect({id, name})`, solo activos), `PatientForm` (`onSaved(patient)`, `onCancel`), `ConfirmDialog` (foco en "Cancelar", Escape cierra), `ApiError` con `status` y `code`.
- **Sin backend nuevo**: todo lo que pide C-10 se resuelve con los endpoints existentes, siempre que P-1 y P-8 queden con la opción A.

## Goals / Non-Goals

**Goals:**
- Las acciones de `frontend-appointment-management` sobre la grilla de C-09, sin reescribir sus piezas y manteniendo verdes sus tests.
- Toda la lógica de "qué acción corresponde" y "qué mensaje mostrar" en funciones puras probadas con tablas.

**Non-Goals:**
- Cambios de backend, endpoint de configuración del consultorio (salvo P-1 = B), nombres en `/conflicts` (salvo P-8 = B).
- Cambiar de profesional al reprogramar (DD-64), turnos urgentes sin anticipación (DD-65), sobreturnos (RN-TU-11), turnos consecutivos para tratamientos largos en un paso (RN-TU-10).
- Emails de confirmación (C-11) y listado de todos los profesionales (C-12, DD-66). Edición o desactivación de pacientes desde la agenda (sigue en `/pacientes`).

## Decisiones de la usuaria (P-1 a P-9, CONFIRMADAS: opción A en todas)

Cada pregunta en lenguaje simple, con opciones, la recomendada y por qué.

### P-1 — ¿En qué horarios libres aparece el botón "Agendar"? — CONFIRMADA (A)
La pantalla no sabe cuántas horas de anticipación pide el consultorio (6 por defecto): ese dato está solo en el servidor.
- **A (recomendada)**: en toda franja "Libre" que todavía no empezó, para administración y recepción y solo si el profesional está activo. Si falta menos que la anticipación mínima, al confirmar el sistema avisa "Ese horario ya pasó o no respeta la anticipación mínima del consultorio".
- B: agregar al servidor un pedido que informe la anticipación y la duración del turno, y ocultar también "Agendar" en las franjas demasiado cercanas. Es más prolijo pero suma trabajo en el servidor con sus tests de permisos.
- C: mostrar "Agendar" en todas las franjas libres, aunque ya hayan pasado.
**Por qué A**: no toca el servidor, nunca ofrece algo imposible (un horario pasado) y el caso de "falta poco" es raro y tiene un mensaje claro.

### P-2 — ¿Cómo se escribe el motivo de una cancelación? — CONFIRMADA (A)
- **A (recomendada)**: un cuadro de texto libre obligatorio (hasta 500 letras), como ya acordado (DD-65).
- B: una lista de motivos frecuentes ("Avisó el paciente", "Licencia del profesional", "Otro") más el texto.
**Por qué A**: es lo que ya acepta el servidor; una lista fija se puede sumar después si recepción repite siempre los mismos motivos.

### P-3 — ¿Cómo se elige el horario nuevo al reprogramar? — CONFIRMADA (A)
- **A (recomendada)**: una ventanita con una fecha (al abrir, la del turno) y la lista de horarios libres de ese día del mismo profesional; se elige uno y se confirma viendo "Mover de … a …".
- B: un "modo reprogramar" sobre la agenda: se navega por días y semanas y se toca una franja libre.
- C: escribir la fecha y la hora a mano.
**Por qué A**: es simple de usar y de probar, no cambia la grilla y solo ofrece horarios libres; B es más visual pero complica la pantalla y C invita a errores de grilla.

### P-4 — ¿Marcar atendido o ausente pide confirmación? — CONFIRMADA (A)
- **A (recomendada)**: sí, "¿Marcar a Perez, Juan como atendido? Después no se puede cambiar".
- B: no, un solo clic.
**Por qué A**: una vez marcado no se puede corregir (DD-22); un clic equivocado quedaría para siempre.

### P-5 — ¿Dónde aparecen las acciones? — CONFIRMADA (A)
- **A (recomendada)**: "Agendar" directo en cada franja libre; los turnos se tocan y abren un panel de detalle con sus acciones. Funciona igual en la vista "Día" y en la "Semana". Las acciones que no corresponden no se muestran.
- B: botones "Cancelar", "Reprogramar", etc. pegados a cada turno en la grilla.
- C: acciones solo en la vista "Día"; la "Semana" sigue siendo solo para mirar.
**Por qué A**: la grilla queda limpia (sobre todo la semana, con columnas angostas), el detalle muestra el motivo y el conflicto antes de decidir y es el mismo lugar para todos los roles.

### P-6 — ¿Cómo se avisa que la búsqueda distingue tildes (DD-74)? — CONFIRMADA (A)
- **A (recomendada)**: un texto fijo debajo del buscador del panel de agendar: "La búsqueda distingue tildes: si el apellido lleva tilde, escribilo con tilde (por ejemplo, Pérez)". La pantalla `/pacientes` no cambia.
- B: mostrarlo solo cuando no hay resultados.
- C: agregarlo también en `/pacientes` (cambia la spec de C-06).
**Por qué A**: recepción lo ve antes de equivocarse y no se toca lo ya cerrado en C-06; la solución de fondo (`unaccent`) sigue anotada en DD-74.

### P-7 — ¿Qué pasa en pantalla cuando el sistema rechaza una acción? — CONFIRMADA (A)
- **A (recomendada)**: se muestra el mensaje claro del motivo, la ventanita queda abierta con lo elegido y la agenda se vuelve a pedir detrás, para que se vea por qué (por ejemplo, el horario ahora "Ocupado").
- B: solo el mensaje; la agenda se actualiza con "Actualizar".
**Por qué A**: el rechazo más común (otra recepcionista ocupó el horario) se entiende al instante y no se vuelve a intentar sobre datos viejos.

### P-8 — ¿Cómo se ven y se resuelven los turnos en conflicto? — CONFIRMADA (A)
- **A (recomendada)**: para administración y recepción, arriba de la agenda un aviso "N turnos en conflicto" con la lista de todos (también los de otras semanas): fecha, hora, paciente, motivo y botones "Reprogramar", "Cancelar" y "Ver en la agenda". El nombre del paciente se pide turno por turno al servidor (normalmente son pocos). El odontólogo sigue viendo solo la marca en cada turno.
- B: igual que A, pero agregando el nombre del paciente en la respuesta de conflictos del servidor (cambio de backend con sus tests de permisos).
- C: sin lista: solo la marca en la grilla (ya existe) y las acciones desde el detalle del turno.
**Por qué A**: con C un conflicto de dentro de tres semanas pasa inadvertido; A no toca el servidor y alcanza para el volumen de un consultorio.

### P-9 — ¿Un solo change o dos? (tamaño) — CONFIRMADA (A)
El change tiene unas 33 tareas, todas en el frontend.
- **A (recomendada)**: un solo change por grupos, con **punto de corte seguro tras el grupo 6** (detalle, agendar y cancelar funcionando) y un segundo tras el grupo 8 (reprogramar y marcar). Si el tiempo no alcanza, el indicador de conflictos (grupo 9) quedaría como C-10b.
- B: partirlo ya en C-10a (detalle, agendar, cancelar y mensajes) y C-10b (reprogramar, marcar y conflictos).
**Por qué A**: las acciones comparten las mismas piezas (reglas, mensajes, panel) y se prueban juntas, como en C-07 y C-09; los puntos de corte dan la misma seguridad que partirlo.

## Decisions

### D-1 — Reglas puras de acciones en `frontend/src/appointments/actions.ts`
`slotActions({ role, professionalActive, now, slot })` → `{ book: boolean }` y `appointmentActions({ role, ownProfessionalId, professionalActive, now, appointment })` → `{ cancel, reschedule, markAttendance }` según la tabla de la spec (P-1, P-5). `now` llega como dato (como `schedule-conflicts`, DD-23: iniciado es `now >= starts_at`), así se prueba con tablas sin reloj. El odontólogo con un turno ajeno da todo en falso aunque nunca debería verlo (defensa). Alternativa descartada: decidir en cada componente (repartiría la matriz y no se podría probar con tablas).

### D-2 — Mensajes y recarga en `frontend/src/appointments/messages.ts`
`messageForAppointmentError(error: unknown): string` con la tabla de la spec, 403 → `FORBIDDEN_MESSAGE` de `api/client.ts`, 422 → "Revisá los datos ingresados", red/5xx → `NETWORK_MESSAGE`; código desconocido con `ApiError` 4xx → `error.message` (el servidor ya garantiza castellano y sin datos de otros pacientes, `error-model`). `shouldReloadAfter(error): boolean` verdadero para todo `ApiError` con código de la tabla (P-7). Textos de éxito y etiquetas de acciones en el mismo archivo para que una acción conserve su nombre en todo el flujo ("Agendar" → "Agendar turno" → "Turno agendado"). Alternativa: reutilizar `users/messages.ts` (no conoce estos códigos).

### D-3 — Cliente de escritura en `frontend/src/api/appointments.ts`
Suma `bookAppointment({ patientId, professionalId, startsAt })`, `cancelAppointment(id, reason)`, `rescheduleAppointment(id, startsAt)`, `recordAttendance(id, status: 'completed' | 'no_show')` y `getAppointment(id)`. Los `POST` devuelven `AppointmentRecord` (la forma sin nombres de `appointment-api`); `Appointment` (con nombres) sigue para listado y detalle. `startsAt` se envía tal como vino en la franja (UTC con `Z`), así no hay conversión de zona en el navegador. Reusa `request` (errores como `ApiError`).

### D-4 — Paneles y diálogos en `frontend/src/appointments/`
- `BookingPanel` (franja, profesional; usa `PatientSearch`, `PatientForm` y el aviso de tildes de P-6; paciente elegido con "Cambiar").
- `AppointmentDetail` (datos del turno y botones de D-1).
- `CancelDialog` (motivo obligatorio, `maxLength` 500, validación local de vacío), `RescheduleDialog` (fecha + franjas libres no iniciadas de `getDaySlots`, paso de confirmación "Mover de … a …"), confirmación de atención con `ConfirmDialog` de C-06 (P-4).
- `ConflictsPanel` (P-8): recibe los conflictos que ya trae `useAgendaData`, pide `getAppointment` de cada uno en paralelo para el nombre y ofrece los mismos diálogos.
- Hook `useAppointmentAction`: envía una vez (ref de "en vuelo" como `PatientForm`), guarda el error traducido, avisa el éxito. Diálogos accesibles como `ConfirmDialog` (`role="dialog"`, `aria-modal`, foco inicial en la opción segura, Escape cierra).
Alternativa descartada: un único diálogo genérico con modos (mezcla validaciones distintas y complica los tests).

### D-5 — Integración con la grilla sin romper C-09
`DayColumn` y `WeekView` suman props opcionales `onBookSlot?(slot)`, `canBook?(slot)` y `onSelectAppointment?(id)`. Sin esas props se comportan exactamente como en C-09 (sus tests siguen verdes). Con `onSelectAppointment`, cada turno se dibuja como botón que abre el detalle; con `onBookSlot` y `canBook`, la franja libre muestra "Agendar". `buildDayColumn` no cambia (ya da `id` de turno y límites de franja). `useAgendaData` expone además `conflicts` y la lista de turnos para que la página arme el detalle sin otro pedido.

### D-6 — Estado de la página
`AgendaPage` guarda un único estado `panel` (unión discriminada: ninguno, agendar con franja, detalle con id, cancelar, reprogramar, marcar con estado) y un `notice` de éxito (`role="status"`). Éxito o rechazo con código → `reloadKey + 1` (D-2, P-7) y en éxito se cierra el panel. "Ahora" se lee con `new Date()` al dibujar; los tests fijan la hora con los temporizadores falsos de Vitest. Reglas de React aplicadas (`vercel-react-best-practices`, solo React): estado derivado calculado al dibujar y no copiado con efectos, actualizaciones funcionales de estado, componentes definidos fuera del render, claves estables (`id` del turno, inicio de la franja), sin `any`.

### D-7 — Diseño visual (`frontend-design`)
Se sigue la identidad ya establecida en `styles.css` (no se rediseña la agenda). Una sola pieza nueva con peso visual: el panel lateral de acciones (a la derecha en pantallas anchas, a ancho completo en el teléfono), con la fecha y la hora del turno como título grande, que es lo que recepción confirma por teléfono. "Agendar" en la franja libre es un botón de texto discreto; "Cancelar turno" usa el estilo de acción destructiva; los estados siguen distinguiéndose por texto y no solo por color; foco visible y movimiento mínimo (solo la apertura del panel, respetando `prefers-reduced-motion`). Textos en voz activa y sin disculpas: los mensajes de error dicen qué pasó y qué hacer.

### D-8 — Tests
Vitest: tablas para `actions.ts` y `messages.ts`; cliente con `fetch` simulado (método, ruta, cuerpo); cada panel y diálogo; flujos de página con `fetch` simulado y hora fija: agendar, choque de slot (`SLOT_TAKEN` y recarga), cancelar libera la franja, reprogramar, marcar atención, conflictos resueltos desde la lista; "mirar no escribe" y "el odontólogo solo envía atención" contando métodos de los pedidos. El backend no cambia: su suite (incluida la de C-08) corre como red de seguridad (regla dura 6).

## Risks / Trade-offs

- [Anticipación desconocida en la pantalla (P-1 = A, confirmada)] → "Agendar" aparece en franjas a menos de `min_notice_hours`; el servidor rechaza con `INSUFFICIENT_NOTICE` y el mensaje lo explica. Mejora posterior: P-1 = B.
- [Reloj del navegador distinto al del servidor] → los botones se calculan con la hora del navegador; el servidor decide y responde `ALREADY_STARTED` o `NOT_STARTED_YET` con su mensaje y la agenda se vuelve a pedir.
- [Reprogramar solapando el propio horario anterior] → el servidor lo permite (`appointment-use-cases`, DD-67), pero la pantalla solo ofrece franjas "Libre" y la del propio turno sale "Ocupado"; solo ocurre si cambió `slot_minutes`. Alternativa para ese caso: cancelar y agendar.
- [Paciente inactivo al reprogramar] → la grilla no sabe si el paciente está activo; el servidor rechaza con `PATIENT_INACTIVE` y el mensaje indica reactivarlo (DD-25, DD-76).
- [Nombres de conflictos turno por turno (P-8 = A)] → N pedidos `GET` por profesional; aceptable con pocos conflictos. Mitigación posterior: P-8 = B.
- [Paciente creado y turno rechazado] → el alta de paciente queda hecha aunque el turno falle (escenario explícito); no hay borrado automático (DD-75).
- [US-007 pide el email de confirmación] → lo envía C-11; hasta entonces C-08 deja la notificación `pending` (DD-62) y el aviso de éxito no menciona emails.
- [Doble turno del paciente en carrera (DD-63)] → la regla la garantiza la aplicación; la pantalla solo muestra `PATIENT_DOUBLE_BOOKED`.
- [Zona fija en el frontend (SU-01)] → igual que C-09; los instantes que se envían son los del servidor, así que no se corre ningún turno.
- [Tamaño (~33 tareas)] → grupos con puntos de corte (P-9).
- [Regla dura 6] → la pantalla no evalúa superposiciones: confía en el dominio y el constraint; los tests de flujo cubren el choque de slot.

## Migration Plan

Sin migraciones, variables de entorno ni dependencias nuevas. Despliegue: reconstruir la imagen del frontend. Reversión: quitar las props de acciones en `AgendaPage` (la grilla vuelve a ser de solo lectura como en C-09).

## Open Questions

Ninguna fuera de P-1 a P-9 (que cambian specs o tasks y por eso están arriba como pendientes). Notas para otros changes: C-11 puede sumar "Se envió la confirmación por email" al aviso de éxito; C-12 sigue con el listado de todos los profesionales (DD-66).

## Revisión de escenarios (skill `revisor-escenarios-turnos`, 2026-11-06)

Aplicada a las dos specs del change (61 escenarios), leyendo en el momento `05_reglas_de_negocio.md`, `09_decisiones_y_supuestos.md`, `10_preguntas_abiertas.md`, `04_modelo_de_datos.md` y la entrada C-10 de `CHANGES.md`.

### Resumen
61 escenarios revisados, 11 hallazgos (1 ambigüedad, 3 bordes faltantes, 2 reglas solapadas, 1 pregunta abierta, 2 sin respaldo, 2 contrato incompleto, 0 contradicciones). Los bordes ya se agregaron a las specs; lo que no tiene respaldo quedó como P-n.

### Hallazgos
| # | Tipo | Escenario afectado | Qué pasa | Respaldo en la KB | Sugerencia (a confirmar) |
|---|------|--------------------|----------|-------------------|--------------------------|
| 1 | Contrato incompleto | Agendar; franja sin anticipación | La pantalla no conoce `min_notice_hours` (solo en `clinic_settings`, sin endpoint) y las franjas no aplican la anticipación | RN-TU-12, DD-17, `04_modelo_de_datos.md` (`clinic_settings`) | P-1: ofrecer solo franjas no iniciadas y mostrar `INSUFFICIENT_NOTICE` |
| 2 | Contrato incompleto | Lista de conflictos | `GET /conflicts` trae solo `patient_id`; la lista necesita el nombre | `professional-schedule-api` (spec), DD-68 | P-8: leer el detalle de cada turno |
| 3 | Ambigüedad | Acciones por hora | "Iniciado" se evalúa con el reloj del navegador y el servidor usa el suyo | DD-23 | Agregado "Reloj del navegador adelantado" y "El turno empezó mientras el diálogo estaba abierto" |
| 4 | Borde faltante | Reprogramar | El servidor permite mover solapando el propio horario anterior, la pantalla no lo ofrece | DD-67, spec `appointment-use-cases` | Agregado "El horario actual no se ofrece"; riesgo anotado (cancelar y agendar) |
| 5 | Borde faltante | Cancelar | Faltaba cancelar el turno de un paciente inactivo | DD-25, DD-76 | Agregado "Paciente inactivo se puede cancelar" |
| 6 | Borde faltante | Buscar o crear paciente | Faltaba el paciente creado con el turno rechazado | DD-75, RN-PA-03 | Agregado "Paciente creado y turno rechazado" |
| 7 | Reglas solapadas | Marcar atención | US-010 dice "solo el odontólogo, turnos propios"; DD-64 amplía a recepción y administración | US-010 (`06_funcionalidades.md`), DD-64 | Se sigue DD-64 (más reciente y confirmada) |
| 8 | Reglas solapadas | Franja sin anticipación | `10_preguntas_abiertas.md` sigue mostrando como abierta (Media) la excepción de urgencias, que DD-65 ya cerró ("sin excepción") | DD-65, `10_preguntas_abiertas.md` | Marcarla RESUELTA en `10_preguntas_abiertas.md` (a confirmar por la usuaria) |
| 9 | Pregunta abierta | Agendar (éxito) | US-007 exige el email de confirmación; el envío depende de C-11 y del SMTP gratuito (prioridad Alta) | US-007, RN-NO-01, SU-02 | No bloquea C-10: el aviso de éxito no menciona emails |
| 10 | Sin respaldo | Cancelar, marcar, reprogramar | Forma del motivo, confirmación al marcar, cómo se elige el nuevo horario y dónde están las acciones | DD-65 (motivo obligatorio), DD-22; **sin respaldo en la KB** para la forma en pantalla | P-2, P-3, P-4, P-5 |
| 11 | Sin respaldo | Mensajes y recarga; aviso de tildes | Textos de error, recargar tras un rechazo y dónde va el aviso de tildes | DD-74, DD-83 (sin refresco automático); **sin respaldo en la KB** para los textos y la recarga tras rechazo | P-6, P-7 |

### Escenarios sin hallazgos
Choque de slot por concurrencia (RN-TU-01, Flujo 2: "el slot acaba de ocuparse"), cancelar libera la franja (RN-TU-05), reprogramar sin ejecución parcial (RN-TU-06), paciente desactivado al reprogramar (DD-25), profesional inactivo sin agendar ni reprogramar pero con cancelar (DD-59, DD-64), doble turno del paciente sin revelar el otro (DD-63), inactivos fuera del buscador (RN-PA-04), turno en su inicio exacto (DD-23), turnos terminados sin acciones (DD-22, RN-TU-07), día sin horarios o de licencia al reprogramar (RN-HO-03), conflictos solo de turnos no iniciados (DD-68), odontólogo sin acciones de recepción (RN-AU-04, DD-48), sin datos de contacto (DD-79). Hay escenarios esperados, de error de negocio y de borde en cada requirement. No se inventaron estados ni campos: `scheduled`/`cancelled`/`completed`/`no_show` y `cancel_reason` están en `04_modelo_de_datos.md`.

### Decisiones de la usuaria
P-1 a P-9 confirmadas (opción A) y el hallazgo 8 resuelto: la pregunta de urgencias quedó marcada RESUELTA en `10_preguntas_abiertas.md`.
