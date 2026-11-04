# Design: professional-schedules (C-07)

> **Gobernanza MEDIA.** Las decisiones P-1 a P-11 fueron **RESUELTAS**: la usuaria confirmó todas las opciones recomendadas (P-1 A, P-2 A, P-3 A, P-4 B, P-5 A, P-6 A, P-7 A, P-8 A, P-9 A, P-10 A, P-11 A). Quedaron registradas como DD-68 a DD-72 en `knowledge-base/09_decisiones_y_supuestos.md`.

## Context

Motivación en `proposal.md`. Estado real del código (verificado el 2026-11-03):

- **Dominio puro** (`app/domain/schedules/`): `validate_working_hours` (códigos `INVALID_WEEKDAY`, `SUB_MINUTE_PRECISION`, `START_NOT_BEFORE_END`, `OVERLAPPING_BLOCKS`, con posiciones de tramo 0-based y orden determinista), `validate_time_off` (`END_BEFORE_START`), `is_date_in_time_off` (fecha local, inclusiva), `TimeOffEntry.to_time_off()`. El dominio de turnos tiene `validate_appointment` y su helper privado `_fits_in_working_hours` (inicio y fin dentro de un mismo tramo del día local, fin el mismo día local), `compute_slots`, `rules.ranges_overlap`, y `app/core/timezone.py` (`to_local`, `local_day_bounds`). `validate_working_hours` dice explícitamente "No detecta turnos en conflicto con el horario (RN-HO-04, eso es de C-07)".
- **Puertos y repositorios**: `WorkingHoursRepository` (`list_for_professional`, `replace_for_professional` atómico: DELETE + INSERT en una transacción en PostgreSQL), `TimeOffRepository` (`add`, `list_for_professional`; **sin borrar**), `ProfessionalRepository` (`list(only_active)`, `get_by_id`; **solo lectura**). En memoria, `InMemoryProfessionalRepository` lee las fichas del almacén de `InMemoryUserAccountRepository`. **Los adaptadores SQLAlchemy de horarios y licencias ya existen desde C-02** (`app/infrastructure/db/repositories/schedules.py`), aunque la entrada C-07 de `CHANGES.md` decía que los agregaba C-07: hay que corregir esa línea al archivar.
- **Consumo actual (C-08)**: `load_context` lee tramos y licencias de los repositorios en cada pedido de agendar, reprogramar y franjas (`GET /professionals/{id}/slots`). Por eso un cambio de horario rige de inmediato sin tocar C-08 (US-004). `AgendaDeps` ya agrupa todos los puertos y el reloj inyectable (`get_clock`).
- **API** (C-03/C-04/C-08): `current_user`, `require_role`, `can_access_professional` (DD-53), fábricas sobreescribibles en `app/api/dependencies.py`, `STATUS_BY_CODE` (default 400), 422 sin eco, `strip_text`, test de inventario de rutas, patrón de tests de permisos por rol (`tests/unit/api/test_users_permissions.py`, `test_appointments_permissions.py`: tabla endpoint × llamador con "nada cambió" en cada 403). `professionals_router` (prefijo `/professionals`) vive hoy en `app/api/appointments.py` con la ruta de franjas.
- **Esquema** (C-02): `professionals.display_name` NOT NULL, `license_number` NULL; `working_hours` con CHECK de día, inicio < fin y sin segundos (la superposición la valida el dominio, DD-42); `time_off` con `starts_on <= ends_on` y `reason` NULL, **sin tablas que dependan de ella** (se puede borrar sin chocar con `ON DELETE RESTRICT`, DD-39). **No hay columna para marcar un turno "en conflicto"**. **No hace falta migración** con las opciones recomendadas.
- **Frontend** (C-03/C-04): `react-router`, `RequireAuth`, `RequireRole`, cliente de API en `frontend/src/api/client.ts`, patrón de pantalla de C-04 (`UsersPage`, formularios, mensajes en `users/messages.ts`).
- **Consultado con Context7** (`/websites/pydantic_dev_validation`, sin datos del proyecto): Pydantic v2 valida `datetime.time` con RFC 3339 y **acepta una zona (`Z` o desplazamiento) y números como segundos**; una hora con zona daría un `time` con zona que no se puede comparar con los tramos sin zona. Esto motiva D-6.
- La skill `revisor-escenarios-turnos` se aplicó a las specs borrador (resultado al final).

## Goals / Non-Goals

**Goals:**
- Una sola regla pura de conflictos (RN-HO-04) que use exactamente el mismo criterio de "entra en un tramo" que `validate_appointment`, para que "en conflicto" y "no se podría agendar ahí" nunca diverjan.
- Casos de uso finos en `app/application/professionals.py` que validan con el dominio existente, guardan por los puertos y devuelven conflictos sin tocar turnos.
- Endpoints con JWT, `require_role` y test de permisos por rol en cada uno.
- Reusar la batería de contrato para las dos escrituras nuevas (ficha y borrar licencia), en memoria y PostgreSQL.
- Pantalla `/profesionales` (si P-9 = A).

**Non-Goals:**
- Cancelar, mover o avisar automáticamente a pacientes de turnos en conflicto (RN-HO-04; P-2). Los resuelve recepción con los endpoints de C-08.
- Indicador de conflictos en la agenda y acceso directo a reprogramar desde ahí (C-10).
- Vistas de agenda diaria/semanal (C-09).
- Editar una licencia existente (se borra y se vuelve a cargar, P-4), bloqueos de horas sueltas dentro de un día (DD-08), horarios por fecha puntual o excepciones de un solo día.
- Cambiar el estado activo de la ficha (sigue a la cuenta, DD-59, C-04), crear o borrar fichas (C-04).
- Tope de horario o de duración de licencia (DD-26, P-10).

## Decisiones pendientes (P-1 a P-11)

Cada pregunta en lenguaje simple, con opciones, la recomendada y por qué. **Todas RESUELTAS con la opción recomendada.**

### P-1 — ¿Cómo "marca" el sistema los turnos en conflicto? — RESUELTA (opción A, confirmada por la usuaria)
RN-HO-04 dice que modificar horarios o cargar una licencia no cancela turnos y que "el sistema los marca como conflicto para que recepción los resuelva". La base no tiene ningún campo para guardar esa marca.
- **A (recomendada)**: no se guarda nada: el sistema **calcula** en el momento qué turnos están en conflicto. Se muestran al guardar el horario o la licencia y además hay una consulta "turnos en conflicto de este profesional" que recepción puede abrir cuando quiera (y que C-10 usará para su aviso).
- B: agregar un campo "en conflicto" a los turnos (cambio en la base) que se prende al guardar el horario y se apaga al resolver.
- C: mostrarlos solo una vez, al guardar; después no hay forma de volver a verlos.
**Por qué A**: la lista siempre está al día (si recepción cancela o mueve el turno, desaparece sola; si el administrador corrige el horario, también), no hace falta tocar la base y no hay riesgo de que la marca quede desactualizada. B obliga a mantener la marca sincronizada en cada cambio. C pierde la información si alguien cierra la pantalla.

### P-2 — Si un cambio afecta turnos, ¿se avisa al paciente? — RESUELTA (opción A, confirmada por la usuaria)
Es una pregunta abierta de prioridad media en `10_preguntas_abiertas.md` ("¿se avisa al paciente o solo a recepción?").
- **A (recomendada)**: solo se avisa a recepción (en pantalla). Recepción llama al paciente y, al reprogramar o cancelar, el paciente recibe el email que corresponda cuando exista C-11.
- B: mandar un email automático al paciente avisando que su turno quedó en conflicto.
**Por qué A**: el paciente recibe un solo mensaje claro (el del nuevo horario o la cancelación) en lugar de un "su turno tiene un problema" sin solución; los emails todavía no existen (C-11) y B agregaría un tipo de email nuevo y una migración del tipo de notificación.

### P-3 — ¿Qué turnos cuentan como "en conflicto"? — RESUELTA (opción A, confirmada por la usuaria)
- **A (recomendada)**: solo los turnos "agendados" (`scheduled`) que **todavía no empezaron** y que ya no entran completos dentro de un tramo del horario o caen en un día de licencia. Un turno que sigue dentro del horario pero que ya no coincide con la "grilla" nueva (por ejemplo el horario pasó a empezar 09:15 y el turno es a las 10:00) **no** cuenta.
- B: lo mismo, pero además cuentan los que quedaron fuera de la grilla.
- C: cuentan también los turnos de hoy que ya empezaron.
**Por qué A**: Flujo 5 habla de "turnos que quedan fuera del nuevo horario"; un turno fuera de grilla igual se puede atender (el profesional está trabajando) y marcarlo confundiría a recepción. Un turno que ya empezó no se puede reprogramar ni cancelar (DD-21, DD-24), así que listarlo no sirve. "Empezó" usa la misma definición que C-05c (DD-23).

### P-4 — ¿Se pueden borrar licencias? — RESUELTA (opción B, confirmada por la usuaria)
US-005 solo pide "cargar" licencias; `CHANGES.md` dejó borrarlas o editarlas "sin respaldo en la KB".
- A: solo cargar. Una licencia cargada por error queda para siempre (o hay que tocar la base a mano).
- **B (recomendada)**: cargar y **borrar** (para corregir un error se borra y se carga de nuevo). Solo el administrador.
- C: cargar, editar y borrar.
**Por qué B**: sin borrar, un error de tipeo bloquea días de agenda sin forma de arreglarlo desde la app. Borrar es simple y seguro: la licencia no tiene nada colgado en la base. Editar (C) agrega pantalla y casos sin necesidad: borrar y volver a cargar logra lo mismo. Costo: un endpoint y un método de repositorio más.

### P-5 — Cuando un cambio deja turnos en conflicto, ¿se guarda igual? — RESUELTA (opción A, confirmada por la usuaria)
- **A (recomendada)**: sí, se guarda y se muestra la lista de turnos afectados (lo que dicen RN-HO-04, US-004 y el Flujo 5).
- B: no se deja guardar mientras haya turnos afectados; primero hay que moverlos.
- C: en dos pasos: el sistema primero muestra "esto afecta a N turnos, ¿confirmás?" y recién guarda si el administrador confirma.
**Por qué A**: es lo que pide la KB y es lo práctico: si la profesional se enferma, la licencia tiene que cargarse ya, aunque haya turnos. B traba al administrador. C es más prolijo pero agrega un paso y una segunda llamada; si se quiere, la pantalla puede mostrar un aviso antes sin cambiar la API (mejora posterior).

### P-6 — ¿Se puede editar el horario, las licencias y la ficha de un profesional desactivado? — RESUELTA (opción A, confirmada por la usuaria)
La KB solo dice que desactivar no toca sus turnos (DD-59) y que no recibe turnos nuevos (DD-64).
- **A (recomendada)**: sí, el administrador puede editarlos igual.
- B: no; responde "profesional inactivo".
**Por qué A**: permite dejar preparado el horario antes de reactivarlo, corregir la matrícula o cargar la licencia que explica la baja; no habilita turnos nuevos porque eso ya lo bloquea C-08.

### P-7 — ¿Qué muestra el listado de profesionales? — RESUELTA (opción A, confirmada por la usuaria)
- **A (recomendada)**: todos los profesionales, activos e inactivos, con su estado, ordenados por nombre. El odontólogo ve solo el suyo (lista de uno); si no tiene ficha, la lista sale vacía.
- B: solo los activos.
- C: el odontólogo recibe "sin permiso" al pedir el listado.
**Por qué A**: el administrador necesita ver a los inactivos para editarlos (P-6) y recepción para resolver sus turnos pendientes (DD-59). La matriz dice que el odontólogo lee "lo propio", así que filtrar es más amable que dar error.

### P-8 — Editar la ficha: ¿qué datos y con qué límites? — RESUELTA (opción A, confirmada por la usuaria)
C-04 dejó la edición para C-07 (DD-60).
- **A (recomendada)**: solo el administrador edita "nombre a mostrar" (obligatorio, 1 a 200 caracteres) y "matrícula" (opcional, 1 a 50, y se puede borrar). Mismos límites que el alta de C-04.
- B: el odontólogo también puede editar su propia ficha.
**Por qué A**: la matriz confirmada (DD-48) da "Profesionales" solo al administrador; mantener los límites del alta evita que un dato válido en el alta sea inválido al editar.

### P-9 — ¿La pantalla `/profesionales` entra en este change? — RESUELTA (opción A, confirmada por la usuaria)
`CHANGES.md` pone la pantalla en C-07 (US-004 y US-005: "`/profesionales` con listado, edición de horarios y carga de licencias"), como C-04 hizo con `/usuarios`.
- **A (recomendada)**: sí, backend y pantalla en C-07: listado, edición de ficha, editor de la semana, licencias y aviso de conflictos. Recepción y odontólogo la ven en modo lectura.
- B: solo backend; la pantalla pasa a C-09 o C-10.
**Por qué A**: sin pantalla el administrador no puede usar lo construido y C-09 (que solo muestra la agenda) no la cubre. Costo: el change crece (ver P-11).

### P-10 — Bordes de las licencias — RESUELTA (opción A, confirmada por la usuaria)
- **A (recomendada)**: (a) el motivo es opcional, de hasta 500 caracteres; si se deja en blanco se guarda "sin motivo"; (b) no hay tope de duración (una licencia larga, de meses, es válida); (c) se siguen aceptando licencias superpuestas o en fechas pasadas, como ya decidió DD-28.
- B: poner un tope de duración (por ejemplo 1 año) o rechazar licencias en el pasado.
**Por qué A**: coincide con lo ya decidido para el dominio (DD-28) y con el largo del motivo de cancelación (DD-65); un tope agrega una regla sin un caso real que la pida.

### P-11 — ¿Un solo change o dos? (tamaño) — RESUELTA (opción A, confirmada por la usuaria)
Estimación con las opciones recomendadas: 42 tareas (5 de confirmación, 4 de dominio, 4 de repositorios, 8 de casos de uso, 6 de API, 3 de integración, 1 de checkpoint, 8 de pantalla y 3 de cierre) y 87 escenarios nuevos, parecido a C-08 (46 tareas) y C-04 (45).
- **A (recomendada)**: un solo change ejecutado por grupos, con **punto de corte seguro al terminar el grupo 6** (backend completo y probado contra PostgreSQL, antes del frontend). Si el tiempo no alcanza, se archiva ahí y la pantalla se hace como C-07b.
- B: partirlo ya en C-07a (backend) y C-07b (pantalla).
**Por qué A**: el contrato de la API y la pantalla se validan juntos (como en C-04) y el punto de corte da la misma seguridad que partirlo sin duplicar proposal, design y archivo.

## Decisions

Decisiones técnicas (no de dominio). Suponen las opciones confirmadas de P-1 a P-11.

### D-1 — Regla de conflictos en `app/domain/schedules/conflicts.py`
`find_schedule_conflicts(*, professional_id, working_hours, time_off, appointments, now, timezone) -> list[ScheduleConflict]` con `ScheduleConflict(appointment: Appointment, reason: ConflictReason)` y `ConflictReason` = `OUTSIDE_WORKING_HOURS` | `TIME_OFF`. Filtra profesional, `scheduled` y `now < starts_at`; `ValueError` si `now` no tiene zona (DD-18). Para "entra en un tramo" se **extrae** `_fits_in_working_hours` de `validation.py` a una función pública compartida (por ejemplo `fits_in_working_hours` en `appointments/rules.py`), con los tests archivados de C-05a a C-05c como red de seguridad: así agendar y conflictos usan el mismo criterio (Goal 1). Licencia: `is_date_in_time_off(to_local(starts_at).date(), ...)`. Orden por inicio y luego id. Para evitar el ciclo de imports `schedules` ↔ `appointments` se respeta el patrón de C-05d (tipos solo para anotar o import tardío; `tests/contract/test_import_order.py` lo vigila).
**Alternativa descartada**: reutilizar `validate_appointment` con anticipación 0 y sin otros turnos: mezclaría grilla (que P-3 excluye) y depende del orden fijo de motivos.

### D-2 — Errores de dominio
En `app/domain/schedules/errors.py`: `InvalidWorkingHoursError` (`INVALID_WORKING_HOURS`, lleva los `ScheduleProblem`), `InvalidTimeOffError` (`INVALID_TIME_OFF`) y `TimeOffNotFoundError` (`TIME_OFF_NOT_FOUND`), todos `DomainError`. El mensaje nombra problema y posición **1-based** para personas ("Los tramos 1 y 2 se superponen", "El tramo 3 tiene el inicio después del fin"), sin horas ni textos enviados. Se reusa `ProfessionalNotFoundError` de `appointments/errors.py`. `STATUS_BY_CODE`: 400 explícito para los dos `INVALID_*`, 404 para `TIME_OFF_NOT_FOUND`.

### D-3 — Casos de uso en `app/application/professionals.py`
Funciones que reciben un `ScheduleDeps` (dataclass con `professionals`, `professional_writer` si hace falta, `working_hours`, `time_off`, `appointments`, `settings`, `clock`) y el `Principal`: `list_professionals`, `get_professional`, `update_professional`, `get_working_hours`, `replace_working_hours`, `list_time_off`, `add_time_off`, `delete_time_off`, `list_conflicts`. Orden de cada escritura: permiso (rol admin) → profesional existe → validar con el dominio → guardar → calcular conflictos con lo guardado y los turnos desde `now` sin fin (`appointments.list_for_professional(id, now)`) y la zona de `clinic_settings`. El alcance de lectura usa `can_access_professional` (mismo helper que C-08). El rol se chequea también en el caso de uso (defensa en profundidad, RN-PR-02), no solo en la ruta. Los conflictos se calculan **después** de guardar y fuera de la transacción: es una lectura; si fallara, el guardado ya ocurrió y el cliente puede pedir `GET .../conflicts`.

### D-4 — Escritura de la ficha
Nuevo método en el puerto `ProfessionalRepository`: `update(professional_id, *, display_name: str | None = None, license_number: str | None | Unset = UNSET) -> Professional`, que distingue "no cambiar" de "borrar la matrícula" (un centinela o un dataclass `ProfessionalChanges` con banderas, siguiendo el estilo de `AccountChanges`). En memoria modifica el mismo almacén de fichas que usa `InMemoryUserAccountRepository` (coherencia que la spec exige); en PostgreSQL, `UPDATE` en una transacción. Inexistente o mal formado → `ProfessionalNotFoundError`. En la API, `PATCH` con `model_fields_set` para saber si `license_number` vino como `null` (borrar) o no vino (no cambiar).

### D-5 — Borrar licencia
`TimeOffRepository.delete(professional_id, time_off_id) -> bool`: `True` si borró. En PostgreSQL `DELETE ... WHERE id = :id AND professional_id = :pid` (id mal formado → `False` con `parse_uuid`). El caso de uso traduce `False` a `TimeOffNotFoundError`.

### D-6 — Formato HTTP y validación
Router nuevo en `app/api/professionals.py` con el mismo prefijo `/professionals` (la ruta de franjas queda en `appointments.py`, sin cambios). Horas como `str` con patrón `^([01]\d|2[0-3]):[0-5]\d$` convertidas a `time` sin zona: rechaza en 422 segundos, zonas, números y `24:00` (hallazgo de Context7). `weekday: int` sin rango en Pydantic, para que el día 7 llegue al dominio y responda `INVALID_WORKING_HOURS` (una sola fuente de la regla, RN-HO-01). Fechas `date` (`AAAA-MM-DD`). Textos con `strip_text`. Salidas: `ProfessionalOut`, `WorkingHoursOut` (`HH:MM`), `TimeOffOut`, `ConflictOut` (instantes en UTC como C-08). `PUT .../working-hours` → `{"blocks": [...], "conflicts": [...]}`; `POST .../time-off` → 201 `{"time_off": {...}, "conflicts": [...]}`; `DELETE` → 204. Las escrituras dependen de `require_role(Role.ADMIN)` en la ruta (403 antes que 422: FastAPI resuelve las dependencias antes de lanzar los errores del cuerpo; se prueba). Las lecturas, de `current_user` + alcance en el caso de uso. Fábrica `get_schedule_deps` sobreescribible en `app/api/dependencies.py`, con el mismo `get_clock`.

### D-7 — Pantalla
`/profesionales` dentro de `RequireAuth` (sin `RequireRole`, los tres roles entran); el modo edición se decide con el rol de `useAuth()`. Cliente en `frontend/src/api/professionals.ts`, componentes en `frontend/src/professionals/` (lista, ficha, editor semanal, licencias, aviso de conflictos), mensajes en `professionals/messages.ts`. Fechas mostradas en la zona del consultorio con `Intl.DateTimeFormat` y `timeZone` fijo (`America/Argentina/Buenos_Aires`, SU-01; el frontend no tiene hoy un endpoint de configuración, así que se usa una constante compartida y se anota). TypeScript estricto, sin `any`.

### D-8 — Tests
Dominio puro (escenarios de `schedule-conflicts`), casos de uso con repositorios en memoria y reloj fijo (escenarios de `professional-schedule-use-cases`, incluido el de regla dura 6: cambiar horario + agendar encima → `SLOT_TAKEN`), batería de contrato ampliada (memoria y `postgres`), API con tabla de permisos (9 endpoints × 6 llamadores, snapshot "nada cambió"), integración con el seed (PUT de horario real, licencia que bloquea franjas, conflicto listado, borrar licencia), Vitest para la pantalla.

## Risks / Trade-offs

- [Conflictos calculados (P-1 = A)] → cada consulta lee todos los turnos futuros del profesional; con datos de un consultorio es poco. Si creciera, se limita el horizonte (por ejemplo 1 año) sin cambiar el contrato.
- [Carrera horario ↔ agendar] → C-08 lee el horario fuera de la transacción: un turno agendado en el mismo instante en que se acorta el horario puede quedar afuera. Ya aceptado en C-08 (Riesgos); con P-1 = A aparece en la consulta de conflictos, así que no se pierde.
- [La superposición de tramos solo la valida la aplicación (DD-42)] → un caller que escriba sin validar podría dejar tramos superpuestos. Mitigación: el único camino de escritura es el caso de uso, con test de "tramos superpuestos rechazados, nada cambia".
- [Mover `_fits_in_working_hours` a una función pública] → riesgo de romper la validación de turnos. Mitigación: safety net con los tests archivados de C-05a a C-05c y C-08 antes y después; el comportamiento no cambia.
- [Zona fija en el frontend (D-7)] → si cambia `clinic_settings.timezone`, la pantalla mostraría otra hora. Aceptado bajo SU-01; un endpoint de configuración queda para quien lo necesite.
- [Tamaño (42 tareas)] → ejecución por grupos con punto de corte tras el grupo 6 (P-11).
- [Regla dura 6] → C-07 no toca el constraint ni `overlaps_scheduled`; la suite de C-08 (concurrencia incluida) corre como red de seguridad y se agrega un test explícito.

## Migration Plan

Sin migraciones ni variables de entorno nuevas (con las opciones recomendadas; P-1 = B o P-2 = B sí la exigirían). Despliegue: reconstruir imágenes de backend y frontend. Reversión: quitar el router de `app/api/router.py` y la ruta del frontend; los datos cargados (tramos, licencias) son ficticios y siguen siendo válidos para C-08.

## Open Questions

P-1 a P-11 (arriba), todas resueltas. Ninguna pregunta técnica diferible.

## Revisión de escenarios (skill `revisor-escenarios-turnos`, 2026-11-03)

### Resumen
99 escenarios revisados (87 nuevos; los 12 restantes son copia de `error-model`), 16 hallazgos (3 ambigüedades, 3 bordes faltantes, 0 reglas solapadas, 1 pregunta abierta, 7 sin respaldo, 2 contrato incompleto, 0 contradicciones). Los bordes faltantes ya se agregaron a las specs; las decisiones de dominio quedaron como P-n.

### Hallazgos
| # | Tipo | Escenario afectado | Qué pasa | Respaldo en la KB | Sugerencia (a confirmar) |
|---|------|--------------------|----------|-------------------|--------------------------|
| 1 | Ambigüedad | Consultar los turnos en conflicto | "el sistema los marca como conflicto" no dice si la marca se guarda; no hay campo en `appointments` | RN-HO-04 (`05_reglas_de_negocio.md`); `04_modelo_de_datos.md` §appointments | Calcular en el momento (P-1) |
| 2 | Pregunta abierta | Acortar el horario con turnos afectados | ¿Se avisa al paciente o solo a recepción? | `10_preguntas_abiertas.md` (prioridad Media, RN-HO-04) | Solo recepción (P-2) |
| 3 | Sin respaldo | Turno ya iniciado / fuera de grilla | La KB no define qué turnos cuentan como conflicto | Flujo 5 paso 3 (`07_flujos_principales.md`), DD-23, DD-21, DD-24 | `scheduled`, no iniciado, fuera de tramo o en licencia; grilla no (P-3) |
| 4 | Sin respaldo | Borrar una licencia | US-005 solo pide cargar | US-005 (`06_funcionalidades.md`); entrada C-07 de `CHANGES.md` ("sin respaldo en la KB") | Permitir borrar, solo admin (P-4) |
| 5 | Ambigüedad | Guardar con conflictos | ¿Se bloquea, se confirma o se guarda? | RN-HO-04, US-004 ("se listan para revisión"), Flujo 5 | Guardar y listar (P-5) |
| 6 | Sin respaldo | Editar una ficha inactiva | Solo se sabe que sus turnos quedan intactos y no recibe turnos nuevos | DD-59, DD-64 (`09_decisiones_y_supuestos.md`) | Permitir (P-6) |
| 7 | Sin respaldo | Listado con inactivas / odontólogo | La matriz dice "R (propio)" pero no si se filtra o se rechaza | Matriz de `03_actores_y_roles.md`, DD-53 | Todas con estado; odontólogo filtrado (P-7) |
| 8 | Sin respaldo | Borrar la matrícula, límites | DD-60 solo dice que la edición es de C-07 | DD-60; `04_modelo_de_datos.md` §professionals (`license_number` NULL) | Límites del alta de C-04 (P-8) |
| 9 | Contrato incompleto | Pantalla `/profesionales` | `CHANGES.md` pone la pantalla en C-07; el pedido de propuesta dudaba | Entrada C-07 de `CHANGES.md`, US-004, US-005 | Incluirla con punto de corte (P-9, P-11) |
| 10 | Sin respaldo | Motivo vacío / largo / duración | Sin límites definidos para `reason` | `04_modelo_de_datos.md` §time_off; DD-28 | Opcional, hasta 500, sin tope de duración (P-10) |
| 11 | Contrato incompleto | Todos los de repositorios | `CHANGES.md` dice que C-07 agrega el adaptador SQLAlchemy, pero ya existe desde C-02 | Entradas C-02 y C-07 de `CHANGES.md` | Técnico: reusar y corregir `CHANGES.md` al archivar |
| 12 | Ambigüedad | Tramo con `weekday` | La KB dice 0-6 sin decir qué día es 0 | `04_modelo_de_datos.md` §working_hours | Técnico: 0 = lunes, como `weekday()` de Python que ya usa C-05 (fijado en la spec de API) |
| 13 | Borde faltante | Licencia de un día y día siguiente | Faltaba el borde inclusivo en conflictos | RN-HO-03 | Agregado a `schedule-conflicts` |
| 14 | Borde faltante | Turno a medianoche local en licencia | Faltaba el cambio de día por zona en licencias | RN-GL-01, RN-HO-03, SU-01 | Agregado a `schedule-conflicts` |
| 15 | Borde faltante | Cambiar horario y agendar encima | Faltaba el test de no superposición tras cambiar horario | RN-TU-01, regla dura 6 (`CLAUDE.md`) | Agregado a `professional-schedule-use-cases` |
| 16 | Sin respaldo | Hora con zona o con segundos en la API | La API podría aceptar `09:00Z` | DD-29 (minutos exactos), DD-42 | Técnico: 422 por formato `HH:MM` (D-6) |

### Escenarios sin hallazgos
Tramos superpuestos, inicio posterior al fin, día 7, tramos contiguos y a caballo entre tramos (DD-27, RN-TU-03), vaciar la semana, cambio inmediato (US-004), licencias superpuestas y pasadas (DD-28), fin anterior al inicio, turnos cancelados/atendidos/ausentes que no cuentan, permisos (DD-48, DD-53), error-model. Un turno que cruce la medianoche no puede existir porque los tramos no la cruzan (DD-26) y la regla de "entra en un tramo" lo daría igual fuera de horario.

Hay escenarios esperados, de error de negocio y de borde en cada requirement. No se inventaron estados ni campos: los motivos `OUTSIDE_WORKING_HOURS`/`TIME_OFF` del conflicto son de la respuesta, no de la base.

### Decisiones que necesitaban a la usuaria
P-1 a P-11, resueltas (arriba).
