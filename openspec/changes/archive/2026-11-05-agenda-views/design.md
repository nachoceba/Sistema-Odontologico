# Design: agenda-views (C-09)

> **Gobernanza BAJA.** Las decisiones de dominio P-1 a P-11 fueron **CONFIRMADAS por la usuaria el 2026-11-04**, todas con la opción recomendada (A); quedaron registradas como DD-79 a DD-83 en `knowledge-base/09_decisiones_y_supuestos.md`.

## Context

Ver `proposal.md` (Why). Estado actual que define el enfoque:

- **Backend ya hecho (C-08, C-07)**: `GET /appointments?professional_id&from&to` (rango `[from, to)` con zona, hasta 31 días, todos los estados ordenados por inicio, DD-35) y `GET /appointments/{id}` devuelven `AppointmentOut` con `patient_id` **solo** (sin nombre). `GET /professionals/{id}/slots?date=` devuelve las franjas del **día local completo** 00:00 a 24:00 (DD-15) con `FREE`/`BUSY`/`OUTSIDE_HOURS`, sin anticipación mínima (DD-17), y responde también para fichas inactivas. `GET /professionals` (el odontólogo ve solo la suya; sin ficha, lista vacía), `GET /professionals/{id}/time-off` (fechas locales inclusivas) y `GET /professionals/{id}/conflicts` (turnos `scheduled` no iniciados fuera de horario o en licencia, DD-68). Alcance del odontólogo en el caso de uso (`_require_access`, `can_access_professional`, DD-53); `AgendaDeps` ya tiene `patients: PatientRepository` con `get(id)` que devuelve `Patient(id, first_name, last_name, email, active)`.
- **Frontend ya hecho**: `RequireAuth`/`RequireRole`, `useAuth()` con `role` y `professional_id` (DD-51), `apiFetch`/`ApiError` y `request` (en `api/users.ts`), clientes `api/professionals.ts` y `api/patients.ts`, `CLINIC_TIMEZONE` y `formatLocalMoment` en `professionals/format.ts` (zona fija, D-7 de C-07), páginas con "Volver a la agenda". `AgendaPlaceholderPage` tiene la navegación (Pacientes, Profesionales, Usuarios, Salir).
- **Lo que falta para la grilla**: el nombre del paciente de cada turno (P-1), la pantalla y las funciones de armado de la grilla.
- **Consultado con Context7** (`/mdn/content`, `Intl.DateTimeFormat`, sin datos ni código del proyecto): `formatToParts` con la opción `timeZone` devuelve las partes de fecha y hora en la zona pedida (sirve para "hoy en el consultorio" y para `HH:MM` locales); `timeZoneName: "longOffset"` da `GMT-03:00`. Influyó en D-4: no hace falta ninguna librería de fechas, y para pedir el rango de turnos se usan los límites del día que ya devuelven las franjas, sin calcular desplazamientos en el navegador.

## Goals / Non-Goals

**Goals:**
- Pantalla `/agenda` de solo lectura (día y semana) según `frontend-agenda`, con las piezas de grilla reutilizables por C-10.
- El cambio mínimo de backend para mostrar el nombre del paciente, con su test de permisos por rol.

**Non-Goals:**
- Agendar, cancelar, reprogramar o marcar atención desde la pantalla, panel de detalle del turno e indicador de conflictos con acciones (C-10).
- Listado de turnos de **todos** los profesionales por rango (C-12, DD-66) y vista con varios profesionales a la vez (P-6).
- Vista mensual (P-2), actualización automática (P-10), endpoint de configuración del consultorio (se sigue con `CLINIC_TIMEZONE`, P-3/D-4).
- Migraciones, variables de entorno o dependencias nuevas.

## Decisiones de dominio (P-1 a P-11, RESUELTAS por la usuaria el 2026-11-04: todas la opción A)

Cada pregunta en lenguaje simple, con opciones, la recomendada y por qué.

### P-1 — ¿Cómo sabe la agenda el nombre del paciente de cada turno? — RESUELTA (opción A, confirmada por la usuaria el 2026-11-04)
Hoy el sistema, cuando pide los turnos de un profesional, recibe solo un "número de paciente", no el nombre.
- **A (recomendada)**: que la lista de turnos (y el detalle de un turno) venga ya con nombre y apellido del paciente. Es un cambio chico en el servidor, sin pantallas ni permisos nuevos. Nunca se agregan email, teléfono ni documento.
- B: no tocar el servidor; la pantalla pide los datos de cada paciente uno por uno. Funciona, pero con una semana llena serían decenas de pedidos y la agenda tardaría más en aparecer.
- C: crear un pedido nuevo "agenda" que traiga todo junto (franjas, turnos, nombres, licencias). Es lo más rápido para la pantalla, pero es bastante más trabajo y duplica cosas que ya existen.
- D: no mostrar el nombre, solo "Ocupado". Recepción no sabría de quién es cada turno.
**Por qué A**: con muy poco trabajo la grilla muestra a quién corresponde cada turno, y se respeta lo acordado en C-08 de reusar sus consultas (DD-66).

### P-2 — ¿Qué vistas tiene la agenda? — RESUELTA (opción A, confirmada por la usuaria el 2026-11-04)
- **A (recomendada)**: "Día" y "Semana". La semana va de lunes a domingo (como el editor de horarios). Sábado y domingo se muestran aunque no haya atención, con "Sin atención este día".
- B: además, una vista "Mes".
- C: semana de lunes a sábado (sin domingo).
**Por qué A**: es lo que pide US-006; el mes no se pidió y con turnos de 30 minutos no entra en pantalla.

### P-3 — ¿Qué horas del día se muestran? — RESUELTA (opción A, confirmada por la usuaria el 2026-11-04)
El sistema calcula el día entero (de 00:00 a 24:00), casi todo "fuera de horario".
- **A (recomendada)**: mostrar solo desde la primera franja de atención hasta la última; si hay un corte en el medio (por ejemplo el almuerzo de 13 a 14), se ve una sola banda "Fuera de horario 13:00–14:00". Si hay un turno fuera de ese rango, el rango se estira para mostrarlo.
- B: mostrar las 24 horas, con todas las franjas fuera de horario.
- C: un horario fijo para todos (por ejemplo de 8 a 20).
**Por qué A**: se ve lo que importa sin desplazarse, y ningún turno queda escondido. Las horas se muestran siempre en la hora del consultorio (Buenos Aires, SU-01), sin importar la hora de la computadora.

### P-4 — ¿Cómo se ven los turnos cancelados, atendidos y ausentes? — RESUELTA (opción A, confirmada por la usuaria el 2026-11-04)
- **A (recomendada)**: se ven todos con su etiqueta ("Agendado", "Atendido", "Ausente", "Cancelado"). Los cancelados se ven tachados y en gris al lado de la franja, que sigue diciendo "Libre" (cancelar libera el lugar, RN-TU-05).
- B: los cancelados no se muestran.
- C: casilla "Mostrar cancelados", apagada al entrar.
**Por qué A**: recepción ve qué pasó con cada horario (por ejemplo, quién canceló hoy) sin confundir: la franja dice claramente "Libre".

### P-5 — ¿Cómo se ven las licencias y los turnos en conflicto? — RESUELTA (opción A, confirmada por la usuaria el 2026-11-04)
Hoy el cálculo de franjas marca un día de licencia igual que un día sin atención (DD-15).
- **A (recomendada)**: el día de licencia dice "Licencia" (y el motivo si lo tiene, por ejemplo "Licencia: Congreso"). Un turno agendado que quedó fuera del horario o en una licencia se ve con el aviso "En conflicto", sin botones: resolverlo (reprogramar o cancelar) es de C-10.
- B: no distinguir la licencia y no mostrar avisos de conflicto hasta C-10.
**Por qué A**: usa datos que ya existen (C-07) y evita que alguien piense que el profesional "no atiende" ese día cuando en realidad está de licencia, o que no vea un turno con problema.

### P-6 — ¿Recepción ve un profesional por vez o varios juntos? — RESUELTA (opción A, confirmada por la usuaria el 2026-11-04)
- **A (recomendada)**: uno por vez, con un selector para cambiar de profesional.
- B: en la vista "Día", una columna por profesional, todos juntos.
**Por qué A**: es lo que pide US-006 ("la agenda de un profesional"); B necesitaría la consulta de todos los profesionales, que se acordó dejar para C-12 (DD-66), y en pantallas chicas no entra.

### P-7 — ¿Qué datos del paciente se ven en la grilla? — RESUELTA (opción A, confirmada por la usuaria el 2026-11-04)
- **A (recomendada)**: solo apellido y nombre ("Perez, Juan").
- B: también el teléfono, para llamarlo desde la agenda.
- C: para el odontólogo, ningún nombre (solo "Ocupado").
**Por qué A**: alcanza para saber quién viene; el teléfono está en la ficha del paciente (`/pacientes`). El odontólogo ya puede ver a los pacientes (DD-75), así que C no protege nada y le complica el día.

### P-8 — ¿Qué ve cada uno al entrar, y qué pasa con los profesionales desactivados? — RESUELTA (opción A, confirmada por la usuaria el 2026-11-04)
- **A (recomendada)**: los tres roles entran a `/agenda` (como ya se decidió, DD-51), en la vista "Día" de hoy. Administración y recepción ven el primer profesional activo de la lista y pueden cambiarlo; en la lista también aparecen los desactivados, marcados "(inactivo)", y al elegirlos se ve su agenda con el aviso "Profesional inactivo: no se le pueden dar turnos nuevos" (sus turnos viejos siguen ahí, DD-59, DD-64). El odontólogo ve directamente la suya; si en la dirección figura otro profesional, igual se le muestra la suya. Sin ficha: "No tenés una ficha de profesional asociada". La pantalla provisoria desaparece y su barra de enlaces pasa a la agenda.
- B: el administrador entra a `/usuarios` en lugar de a la agenda.
- C: no mostrar profesionales desactivados en la agenda.
**Por qué A**: no cambia lo ya acordado; con C, los turnos pendientes de un profesional dado de baja quedarían invisibles.

### P-9 — ¿Se puede hacer algo desde la agenda? — RESUELTA (opción A, confirmada por la usuaria el 2026-11-04)
- **A (recomendada)**: en C-09 solo se mira. No hay botones ni clic sobre los turnos. C-10 agrega: agendar desde una franja libre, el detalle del turno y cancelar, reprogramar y marcar.
- B: en C-09 ya se puede hacer clic en un turno y ver un panel de detalle (sin botones).
**Por qué A**: mantiene C-09 chico y deja todo lo que se hace con el turno junto en C-10; así la agenda no puede tocar nada (regla dura 6).

### P-10 — ¿La agenda se actualiza sola? — RESUELTA (opción A, confirmada por la usuaria el 2026-11-04)
Si otra recepcionista agenda un turno, la pantalla abierta no se entera sola.
- **A (recomendada)**: se actualiza al cambiar de profesional, de fecha o de vista, y con un botón "Actualizar".
- B: además, se actualiza sola cada 1 minuto.
**Por qué A**: es simple y predecible. Igual, si alguien intenta agendar un horario que se ocupó recién, el sistema lo rechaza con un mensaje claro (C-08, `SLOT_TAKEN`), así que no hay riesgo de turnos superpuestos.

### P-11 — ¿Un solo change o dos? (tamaño) — RESUELTA (opción A, confirmada por la usuaria el 2026-11-04)
El change tiene unas 30 tareas: el cambio del servidor es chico (grupos 1 a 3) y la mayor parte es la pantalla.
- **A (recomendada)**: un solo change hecho por grupos, con **punto de corte seguro al terminar el grupo 3** (servidor listo y probado contra PostgreSQL). Un segundo punto de corte posible es tras el grupo 6 (vista "Día" completa); si el tiempo no alcanza, la vista "Semana" quedaría como C-09b.
- B: partirlo ya en C-09a (servidor + vista día) y C-09b (vista semana).
**Por qué A**: el contrato de la API y la pantalla se prueban juntos, como en C-06 y C-07, y los puntos de corte dan la misma seguridad que partirlo.

## Decisions

### D-1 — Consulta con datos del paciente en `app/application/appointments.py`
Tipo nuevo de lectura `AppointmentView(appointment: Appointment, patient_first_name: str, patient_last_name: str)` (dataclass congelada en `app/application/appointments.py`, no en `domain/`: es una forma de lectura, no una regla). `list_appointments` y `get_appointment` siguen igual (los usan otros casos de uso y tests); se agregan `list_appointment_views` y `get_appointment_view`, que llaman a las existentes (mismo `_require_access`, misma validación de rango) y completan nombres con `deps.patients.get(id)` **una vez por paciente distinto** (diccionario local). Un paciente que no aparece (no debería: hay clave foránea) produce un error interno, no un nombre vacío. Alternativas: agregar los nombres en el repositorio con un `JOIN` (cambia puerto y batería de contrato en memoria y PostgreSQL; descartado por tamaño) o devolver tuplas (menos legible).

### D-2 — Esquema HTTP
`AppointmentViewOut(AppointmentOut)` suma `patient_first_name` y `patient_last_name`; lo usan solo `GET /appointments` y `GET /appointments/{id}`. Los `POST` siguen con `AppointmentOut` (spec: "Agendar no cambia de forma"). Sin cambios en `require_role`, rutas, códigos de error ni `STATUS_BY_CODE`. El 403 se lanza antes de leer pacientes, así que no se filtra ningún nombre.

### D-3 — Cliente y piezas puras del frontend
- `frontend/src/api/appointments.ts`: `listAppointments(professionalId, fromIso, toIso)`, `getDaySlots(professionalId, date)` (tipos `Appointment`, `Slot`, `AppointmentStatus`, `SlotStatus` como uniones de literales, sin `any`). Reusa `request` como los demás clientes. C-10 lo amplía con las escrituras.
- `frontend/src/agenda/dates.ts` (puro): `todayInClinic(now: Date)`, `addDays(isoDate, n)`, `weekDays(isoDate)` (lunes a domingo), `parseIsoDate` (rechaza `2026-02-30`), `formatLocalTime(utc)` (`HH:MM` 24 h), `formatDayLabel(isoDate)` (`Lun 09/11`). La aritmética de fechas se hace con `Date.UTC` sobre `AAAA-MM-DD`, nunca con la zona del navegador.
- `frontend/src/agenda/grid.ts` (puro): `buildDayColumn({ slots, appointments, timeOff, conflicts, date })` devuelve una lista ordenada de filas: `free`, `busy` (con los turnos `scheduled` que se solapan con la franja), `outside` (bandas juntas, recortadas al principio y al final según P-3), `appointment` sueltas para turnos fuera de horario o desalineados y los no `scheduled` (cancelados/atendidos/ausentes al lado de su franja, P-4), y un encabezado de día `time_off` (con motivo) o `no_hours`. La pertenencia de un turno a un día es por solapamiento con `[primera franja.starts_at, última franja.ends_at)` (DD-19). Toda la lógica visible de la grilla vive acá para probarla sin React.
- Componentes en `frontend/src/agenda/`: `DayColumn` (dibuja una columna; props tipadas pensadas para que C-10 agregue `onSelectFreeSlot`/`onSelectAppointment` sin reescribirlo), `WeekView`, `DateNavigator`, `ProfessionalPicker`, `AppNav` (barra extraída de la página provisoria), mensajes en `agenda/messages.ts`. Estados distinguidos por texto y clase CSS (no solo color).

### D-4 — Fechas, zona y pedidos
"Hoy" y la semana se calculan con `CLINIC_TIMEZONE` (constante de C-07) y `Intl.DateTimeFormat#formatToParts` (Context7). Para cada día visible se pide `GET .../slots?date=` (1 en "Día", 7 en paralelo en "Semana"); el rango de turnos se toma de los límites de esas franjas (primer inicio, último fin), que el servidor ya calcula en la zona real del consultorio, y después se pide `GET /appointments` una vez. Licencias (`GET .../time-off`) y conflictos (`GET .../conflicts`) se piden en paralelo con las franjas. "Semana" = 10 pedidos, "Día" = 4. Un pedido viejo que llega tarde se descarta (contador de pedido o `AbortController`) para que cambiar rápido de fecha no muestre datos mezclados.

### D-5 — Página y estado en la dirección
`frontend/src/pages/AgendaPage.tsx` reemplaza a `AgendaPlaceholderPage.tsx` (se borra) en `App.tsx`. Lee y escribe `profesional`, `fecha`, `vista` con `useSearchParams` de `react-router` (ya en uso, DD-54); valores inválidos se reemplazan por hoy y `dia` con `replace`. El odontólogo usa siempre `user.professional_id` e ignora el parámetro; sin ficha no pide nada. Errores: `ApiError` 403 → `FORBIDDEN_MESSAGE`; red/5xx → "No se pudo conectar con el servidor" + "Reintentar"; 401 lo maneja `client.ts`. Solo `GET` (spec "Solo lectura").

### D-6 — Tests
Backend: casos de uso en memoria (nombres, paciente inactivo, nombre vigente, una lectura por paciente, 403 sin leer pacientes, nada cambia), API con tabla de permisos de los dos endpoints tocados (administración, recepción, odontóloga propia, odontóloga ajena, odontólogo sin ficha, sin token; 401 antes que 403) y forma de respuesta (sin email/teléfono/documento), integración con el seed contra PostgreSQL, y la suite de C-08 completa como red (regla dura 6). Frontend con Vitest: `dates.ts` y `grid.ts` con tablas de casos (los escenarios de `frontend-agenda`), componentes con `fetch` simulado, filtro por rol, cambio de día y de semana, dirección, errores y "solo `GET`".

## Risks / Trade-offs

- [Lecturas de pacientes por pedido (D-1)] → una semana llena son hasta ~100 lecturas por clave primaria; aceptable para un consultorio chico. Mitigación posterior: `get_many` o `JOIN` en el repositorio si se nota lento.
- [Zona fija en el frontend (D-4)] → si cambia `clinic_settings.timezone`, "hoy" y las horas mostradas no acompañan (SU-01 sigue abierta, prioridad Media). Las franjas y el rango de turnos sí siguen al servidor. Aceptado como en C-07.
- [Datos desactualizados (P-10 = A)] → la pantalla puede mostrar "Libre" algo que ya se ocupó; agendar lo rechaza con `SLOT_TAKEN` (C-08). Botón "Actualizar".
- [Franja "Libre" con poca anticipación o pasada (DD-17)] → la vista la muestra libre; C-10 debe mostrar `INSUFFICIENT_NOTICE` al intentar agendar.
- [Conflictos solo de turnos futuros (DD-68)] → un turno pasado en licencia se ve sin aviso (escenario explícito).
- [Grilla de semana no alineada (DD-15)] → cada día con sus propias franjas; se acepta, las filas no coinciden si los tramos tienen anclas distintas.
- [Tamaño (~30 tareas)] → ejecución por grupos con puntos de corte (P-11).
- [Regla dura 6] → C-09 no escribe nada ni toca `domain/`, el constraint ni los casos de uso de escritura; se corre la suite de C-08 y un test explícito de "consultar no cambia nada".

## Migration Plan

Sin migraciones, variables de entorno ni dependencias nuevas. Despliegue: reconstruir imágenes de backend y frontend. Los dos campos nuevos del listado y del detalle son adicionales (un cliente viejo los ignora). Reversión: volver `App.tsx` a la página provisoria y los endpoints a `AppointmentOut`.

## Open Questions

Ninguna (P-1 a P-11 resueltas). Notas para otros changes: C-10 agrega acciones sobre `DayColumn` y el cliente `api/appointments.ts`, y muestra `INSUFFICIENT_NOTICE`/`SLOT_TAKEN`; C-12 define el listado de todos los profesionales (DD-66); el texto de DD-51 ya se actualizó en la KB.

## Revisión de escenarios (skill `revisor-escenarios-turnos`, 2026-11-04)

Aplicada a las cuatro specs del change (52 escenarios), leyendo en el momento `05_reglas_de_negocio.md`, `09_decisiones_y_supuestos.md`, `10_preguntas_abiertas.md`, `04_modelo_de_datos.md` y la entrada C-09 de `CHANGES.md`.

### Resumen
52 escenarios revisados, 10 hallazgos (1 ambigüedad, 3 bordes faltantes, 1 reglas solapadas, 1 pregunta abierta, 3 sin respaldo, 1 contrato incompleto, 0 contradicciones). Los bordes y el contrato incompleto ya se corrigieron en `frontend-agenda`; las decisiones sin respaldo quedaron como P-n.

### Hallazgos
| # | Tipo | Escenario afectado | Qué pasa | Respaldo en la KB | Sugerencia (a confirmar) |
|---|------|--------------------|----------|-------------------|--------------------------|
| 1 | Contrato incompleto | Vista del día | El borrador recortaba "desde el primer tramo", pero la pantalla solo recibe franjas, no tramos; un tramo más corto que un slot sale `OUTSIDE_HOURS` | DD-15, DD-30 (`09_decisiones_y_supuestos.md`) | Corregido: recorte desde la primera franja libre/ocupada (o turno) hasta la última |
| 2 | Borde faltante | Vista del día | Faltaba el resto de tramo que no alcanza para un slot | DD-15, RN-TU-02 | Agregado "Resto de tramo que no alcanza para un slot" |
| 3 | Borde faltante | Vista del día | Faltaba un turno desalineado con la grilla (existe en `slot-availability`) | RN-TU-02, spec `slot-availability` | Agregado "Turno desalineado con la grilla" |
| 4 | Borde faltante | Licencias y conflictos | Un turno pasado en licencia no está en `/conflicts` (solo no iniciados) | DD-68, DD-23 | Agregado "Turno pasado en un día de licencia": sin aviso |
| 5 | Ambigüedad | Profesional inactivo | Sus franjas salen "Libre" pero no se le pueden agendar turnos | DD-59, DD-64 | Aviso "Profesional inactivo…" (P-8) |
| 6 | Sin respaldo | Licencias y conflictos | Distinguir licencia de día sin atención; DD-15 aceptó que la pantalla no lo distinga | DD-15 (trade-off), RN-HO-03; **sin respaldo en la KB** para mostrarla | P-5 |
| 7 | Sin respaldo | Vista de la semana | Semana de lunes a domingo y recorte de horas | **sin respaldo en la KB** (solo `weekday` 0 = lunes en `04_modelo_de_datos.md`) | P-2, P-3 |
| 8 | Sin respaldo | Turnos y estados; listado con nombre | Cómo se ven los cancelados y qué datos del paciente se muestran (nombre vigente, sin contacto) | RN-TU-05, DD-35, DD-75, RN-PR-02; **sin respaldo en la KB** para el formato | P-1, P-4, P-7 |
| 9 | Reglas solapadas | Con sesión en la agenda (`frontend-auth`) | DD-51 dice "página provisoria hasta C-10", pero `CHANGES.md` pone la pantalla de inicio en C-09 | DD-51, entrada C-09 de `CHANGES.md` | C-09 reemplaza la provisoria (P-8); actualizar el texto de DD-51 al confirmar |
| 10 | Pregunta abierta | Hoy según el consultorio; Hora local | La zona del consultorio es un supuesto no confirmado (prioridad Media) | SU-01, `10_preguntas_abiertas.md`; RN-GL-01 | No bloquea: se sigue con la constante de C-07 (riesgo anotado) |

### Escenarios sin hallazgos
Acceso por rol y odontólogo sin ficha (RN-AU-04, DD-53), odontóloga con la dirección ajena (DD-53, 403 evitado sin pedir), turno cancelado y nuevo turno en la misma hora (RN-TU-05, RN-TU-01: el constraint solo mira `scheduled`), atendido y ausente (DD-16), turno que cruza la medianoche (DD-19; con RN-TU-03 no se crea por la agenda, queda como defensa), franja libre pasada (DD-17), hoy según el consultorio (RN-GL-01), solo lectura (regla dura 6), errores 403/red, permisos del listado y detalle (DD-53), consultar no cambia nada. Hay escenarios esperados, de error de negocio (licencia con turno, horario acortado, agenda ajena) y de borde. No se inventaron estados ni campos: `patient_first_name`/`patient_last_name` salen de `patients.first_name`/`last_name` (`04_modelo_de_datos.md`).

### Decisiones de la usuaria
P-1 a P-11 resueltas con la opción A (arriba).
