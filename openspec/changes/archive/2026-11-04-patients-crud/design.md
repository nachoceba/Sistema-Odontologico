# Design: patients-crud (C-06)

> **Gobernanza BAJA** (ABM de pacientes), con datos personales ficticios (RN-PR-01). Las decisiones P-1 a P-12 están **RESUELTAS**: la usuaria confirmó la opción A (recomendada) de todas el 2026-11-04 y quedaron registradas como DD-73 a DD-78 en `knowledge-base/09_decisiones_y_supuestos.md`.

## Context

Motivación en `proposal.md`. Estado real del código (verificado el 2026-11-04):

- **Dominio** (`app/domain/patients/`): `Patient(id, first_name, last_name, email, active)` y `check_patient_can_book(active)` (RN-PA-04, C-05c). El puerto `PatientRepository` solo tiene `get(id)` (DD-34: C-06 lo amplía).
- **Repositorios**: `InMemoryPatientRepository` (solo lectura, estado inyectado) y `SqlAlchemyPatientRepository.get` (C-02). El modelo `PatientModel` ya tiene `document_number` UNIQUE, `email` NOT NULL, `phone` y `birth_date` NULL, `active` con default true e índice por `last_name`. **No hace falta migración** con las opciones recomendadas. La batería de contrato (`tests/contract/test_patient_repository.py`) corre con `in_memory` y `postgres`; la fábrica `PostgresFactory._add_patient` inventa un documento ficticio.
- **Consumidores**: C-08 (`app/application/appointments.py`) usa `patients.get` para RN-PA-04 al agendar y reprogramar (no al cancelar) y `appointments.list_for_patient(patient_id, start, end)` para DD-63. `PatientNotFoundError` (`PATIENT_NOT_FOUND`, 404) y `PatientInactiveError` ya existen en `app/domain/appointments/errors.py`.
- **API** (C-03/C-04/C-07): `current_user`, `require_role`, `STATUS_BY_CODE` (default 400), 422 sin `input` ni `ctx`, `strip_text`, `is_valid_email`/`normalize_email` en `app/domain/users/rules.py`, test de inventario de rutas, tablas de permisos con "nada cambió" (`tests/unit/api/test_users_permissions.py`, `test_professionals_permissions.py`), fábricas sobreescribibles y `get_clock` en `app/api/dependencies.py`. Patrón de desactivar/reactivar con `POST /{id}/deactivate|reactivate` (C-04).
- **Frontend**: `RequireAuth`, `RequireRole`, `apiFetch` y `ApiError` en `src/api/`, pantallas `UsersPage` y `ProfessionalsPage` (modo según rol), formato de fecha local con zona fija (D-7 de C-07).
- **Consultado con Context7** (`/websites/pydantic_dev_validation`, tabla de conversión y modo estricto, sin datos del proyecto): en modo laxo un campo `date` **acepta números** (segundos o milisegundos desde 1970) además de `AAAA-MM-DD`; el modo estricto sobre un objeto Python rechaza también el texto. Motiva D-6 (fecha como texto con patrón).
- La skill `revisor-escenarios-turnos` se aplicó a los escenarios que cruzan pacientes con turnos (resultado al final).

## Goals / Non-Goals

**Goals:**
- Ampliar el puerto existente (DD-34) sin cambiar `get(id)` ni a C-08.
- Una sola regla pura de normalización del documento, usada al guardar y al buscar, para que `30.111.222` y `30111222` sean el mismo documento.
- Documento único garantizado por la base también ante concurrencia (UNIQUE de C-02 traducido a `DOCUMENT_TAKEN`).
- Desactivar sin tocar turnos (DD-25) y devolviendo los turnos futuros para que recepción decida.
- Endpoints con JWT, `require_role` y test de permisos por rol en cada uno; pantalla `/pacientes` con piezas reutilizables por C-10.

**Non-Goals:**
- Historia clínica, odontograma, obras sociales, exportación (fuera de v1, `06_funcionalidades.md`).
- Cancelar o mover turnos al desactivar (DD-25); avisar al paciente por email (C-11).
- Decidir si los turnos de un paciente inactivo reciben recordatorio (P-8: queda como nota para C-12).
- Historial de turnos del paciente en pantalla (C-09/C-10), deduplicación de pacientes, búsqueda sin acentos (P-3 = B).
- Auditoría de quién creó o editó un paciente (no hay columnas para eso; sería migración).

## Decisiones de dominio (P-1 a P-12, todas RESUELTAS)

Cada pregunta en lenguaje simple, con opciones, la recomendada y por qué. **Todas RESUELTAS con la opción A.**

### P-1 — ¿Cómo se escribe el documento y cuándo dos son "el mismo"?
**RESUELTA — opción A (recomendada), confirmada por la usuaria el 2026-11-04** (DD-73).

RN-PA-01 dice que el documento es único, pero no dice su formato. Si una recepcionista escribe "30.111.222" y otra "30111222", ¿son la misma persona?
- **A (recomendada)**: se aceptan letras y números (sirve para DNI y pasaporte). El sistema saca puntos, espacios y guiones y pasa todo a mayúsculas antes de guardar o comparar. Tiene que quedar entre 6 y 20 caracteres. "30.111.222" y "30111222" son el mismo documento y la segunda alta se rechaza.
- B: solo números, de 7 u 8 dígitos (DNI argentino). Un paciente extranjero con pasaporte no se podría cargar.
- C: se guarda tal cual se escribe; "30.111.222" y "30111222" serían dos pacientes distintos.
**Por qué A**: evita duplicados por cómo se tipeó, y no deja afuera a nadie. El seed ya usa documentos solo con números, así que no cambia nada de lo cargado.

### P-2 — ¿Qué datos son obligatorios y con qué límites?
**RESUELTA — opción A (recomendada), confirmada por la usuaria el 2026-11-04** (DD-73).

US-003 pide nombre, apellido, documento y email obligatorios; el modelo deja teléfono y fecha de nacimiento opcionales. Faltan los límites.
- **A (recomendada)**: nombre y apellido de 1 a 100 letras (se recortan espacios); email con el mismo control que el de las cuentas del personal y guardado en minúsculas, **sin exigir que sea único** (una mamá puede usar su email para sus hijos); teléfono opcional, hasta 30 caracteres, solo números, espacios, `+`, `-` y paréntesis, con al menos 6 números; fecha de nacimiento opcional, no futura y no anterior a 1900.
- B: igual que A pero con email único (no se podrían cargar dos hermanos con el email de la mamá).
- C: sin límites, solo lo que exige la base.
**Por qué A**: el email es el canal del recordatorio (RN-PA-02), así que tiene que ser válido, pero en un consultorio es común que una familia comparta email. Los límites evitan textos absurdos sin molestar.

### P-3 — ¿Cómo funciona la búsqueda?
**RESUELTA — opción A (recomendada), confirmada por la usuaria el 2026-11-04** (DD-74).

US-003 pide "búsqueda por apellido y por documento".
- **A (recomendada)**: un solo cuadro de búsqueda. Encuentra a quien tenga ese texto en cualquier parte del apellido (sin importar mayúsculas: "PÉR" encuentra "Pérez"; "per" sin tilde no lo encuentra, ver B) **o** cuyo documento empiece con lo escrito ("30.111" encuentra 30111222).
- B: igual que A pero ignorando acentos ("perez" encuentra "Pérez"). Necesita activar una extensión de PostgreSQL (`unaccent`) con una migración.
- C: dos cuadros separados, apellido exacto y documento exacto.
**Por qué A**: un cuadro es lo más rápido para recepción y no requiere migración. Contra: con A, buscar "perez" sin tilde no encuentra a "Pérez". Si eso molesta mucho en la práctica, B es la mejora (es la única opción que agrega una migración).

### P-4 — ¿Qué puede hacer cada rol? ¿Qué pacientes ve el odontólogo?
**RESUELTA — opción A (recomendada), confirmada por la usuaria el 2026-11-04** (DD-75).

La matriz (`03_actores_y_roles.md`) dice: administración CRUD, recepción CRU, odontólogo R. A diferencia de turnos y horarios, para pacientes **no** dice "propio".
- **A (recomendada)**: administración hace todo; recepción da de alta, ve, edita, desactiva y reactiva (no borra); el odontólogo **ve y busca a todos los pacientes** pero no cambia nada.
- B: igual, pero el odontólogo solo ve a los pacientes que tienen o tuvieron turnos con él.
**Por qué A**: es lo que dice la matriz al pie de la letra. B protege más la privacidad (RN-PR-02, mínimo privilegio) pero agrega una consulta cruzada con turnos y deja al odontólogo sin poder ver la ficha de un paciente nuevo antes del primer turno. Los datos son ficticios (RN-PR-01). Si se elige B, cambian las specs de lectura.

### P-5 — ¿Cuántos resultados muestra la lista?
**RESUELTA — opción A (recomendada), confirmada por la usuaria el 2026-11-04** (DD-74).

- **A (recomendada)**: hasta 50 pacientes, ordenados por apellido y nombre. Si hay más, la pantalla dice "Hay más resultados: afiná la búsqueda". Por defecto muestra solo los activos; una casilla "Incluir inactivos" suma los demás.
- B: todos los pacientes de una vez, sin límite (como la lista de usuarios, DD-60).
- C: con páginas ("anterior / siguiente").
**Por qué A**: los usuarios del personal son pocos, pero los pacientes crecen con los años; 50 alcanza para encontrar a alguien escribiendo parte del apellido, sin el trabajo extra de las páginas. Mostrar primero solo activos evita elegir por error a alguien dado de baja.

### P-6 — ¿Se puede borrar un paciente para siempre?
**RESUELTA — opción A (recomendada), confirmada por la usuaria el 2026-11-04** (DD-75).

RN-PA-03 dice que un paciente **con turnos** no se borra, se desactiva. La matriz da "D" al administrador y aclara que "el borrado físico es solo para el administrador". C-04 decidió no tener borrado para usuarios (DD-59).
- **A (recomendada)**: sí, pero solo el administrador y solo si el paciente **no tiene ningún turno** (ni siquiera cancelado). Sirve para corregir un alta cargada por error. Si tiene turnos, el sistema responde "No se puede borrar: tiene turnos. Desactivalo en su lugar".
- B: no se borra nunca; solo se desactiva.
**Por qué A**: es lo que dicen la matriz y RN-PA-03, y la base ya lo protege (no deja borrar un paciente con turnos, DD-39). Un alta duplicada por error, sin turnos, ocupa un documento que otra alta necesita. Si se elige B, se quitan el endpoint `DELETE`, el error `PATIENT_HAS_APPOINTMENTS` y sus escenarios.

### P-7 — Al desactivar un paciente con turnos futuros, ¿qué se hace?
**RESUELTA — opción A (recomendada), confirmada por la usuaria el 2026-11-04** (DD-76).

DD-25 ya decidió que **no se cancelan** sus turnos: "se listan". Falta decidir cómo.
- **A (recomendada)**: la pantalla pregunta "¿Desactivar a ...? Sus turnos no se cancelan." Al confirmar, se desactiva y se muestra la lista de sus turnos agendados futuros, para que recepción los cancele desde la agenda (o lo reactive si hay que reprogramarlos, porque a un paciente inactivo no se le puede reprogramar, DD-25).
- B: no se deja desactivar mientras tenga turnos futuros; primero hay que cancelarlos.
- C: como A, y además una consulta permanente "turnos de pacientes inactivos" (como la de conflictos de C-07).
**Por qué A**: respeta DD-25 y es igual a lo que se hizo con los horarios (C-07: guardar y listar). B traba a recepción. C suma una consulta más; si se necesita, C-10 puede agregarla.

### P-8 — Los turnos futuros de un paciente inactivo, ¿siguen recibiendo recordatorio?
**RESUELTA — opción A (recomendada), confirmada por la usuaria el 2026-11-04** (DD-76).

RN-NO-02 dice que el recordatorio va a los turnos agendados; no dice nada del paciente inactivo. Esto lo implementa C-12, no este change.
- **A (recomendada)**: sí, mientras el turno siga agendado se le avisa (el turno sigue vigente hasta que recepción lo cancele). Se deja anotado para C-12; en C-06 no se programa nada.
- B: no; C-12 debe saltear los turnos de pacientes inactivos.
**Por qué A**: el turno no se canceló, así que el paciente puede venir; un recordatorio que no llega sería peor. Si recepción no quiere que venga, cancela el turno y el recordatorio no sale (RN-NO-05).

### P-9 — ¿Qué se puede editar de un paciente?
**RESUELTA — opción A (recomendada), confirmada por la usuaria el 2026-11-04** (DD-73).

- **A (recomendada)**: todos los datos, incluido el documento (por si se tipeó mal) y el email, aunque el paciente esté inactivo. Cambiar el email no toca turnos ni notificaciones ya anotadas: los próximos emails que mande C-11 usarán el email nuevo.
- B: el documento queda fijo después del alta.
**Por qué A**: un documento mal escrito tiene que poder corregirse; si quedara fijo habría que borrar y volver a cargar, lo que no se puede si ya tiene turnos.

### P-10 — Privacidad: búsquedas y registros del servidor
**RESUELTA — opción A (recomendada), confirmada por la usuaria el 2026-11-04** (DD-77).

La búsqueda viaja en la dirección (`/patients?q=perez`) y el servidor web anota las direcciones pedidas en su registro de accesos, así que el apellido o documento buscado puede quedar anotado.
- **A (recomendada)**: aceptar que la búsqueda quede en el registro de accesos (los datos son ficticios, RN-PR-01), asegurarse de que la aplicación misma nunca escriba datos de pacientes en sus mensajes de error ni en sus registros, y dejar anotado para C-13 (salida a producción) revisar el registro de accesos.
- B: hacer la búsqueda con `POST` (el texto va en el cuerpo y no en la dirección).
**Por qué A**: `GET` es lo normal para buscar y se puede guardar o compartir el enlace; con datos ficticios el riesgo es bajo y C-13 es el lugar para endurecer registros. B rompe la convención del resto de la API.

### P-11 — ¿La pantalla `/pacientes` entra en este change?
**RESUELTA — opción A (recomendada), confirmada por la usuaria el 2026-11-04** (DD-78).

`CHANGES.md` pone la pantalla en C-06 (US-003), como C-04 y C-07 hicieron con las suyas.
- **A (recomendada)**: sí: listado con búsqueda, alta, edición, desactivar/reactivar (y borrar para administración); el odontólogo la ve en modo lectura. El buscador y el formulario se arman como piezas reutilizables para que C-10 los use al agendar.
- B: solo backend; la pantalla pasa a C-10.
**Por qué A**: sin pantalla recepción no puede usar lo construido, y C-10 ya cuenta con "buscar o crear paciente con C-06".

### P-12 — ¿Un solo change o dos? (tamaño)
**RESUELTA — opción A (recomendada), confirmada por la usuaria el 2026-11-04** (DD-78).

Estimación con las opciones recomendadas: **40 tareas** (5 de confirmación, 3 de dominio, 6 de repositorio, 7 de casos de uso, 6 de API, 3 de integración, 1 de punto de corte, 7 de pantalla y 2 de cierre) y **101 escenarios nuevos** (más los 14 copiados de `error-model`). Es parecido a C-04 (45 tareas) y C-07 (42).
- **A (recomendada)**: un solo change ejecutado por grupos, con **punto de corte seguro al terminar el grupo 6** (backend completo y probado contra PostgreSQL, antes de la pantalla). Si no alcanza el tiempo, se archiva ahí y la pantalla queda como C-06b.
- B: partirlo ya en C-06a (backend) y C-06b (pantalla).
**Por qué A**: el contrato de la API y la pantalla se validan juntos, y el punto de corte da la misma seguridad que partir el change sin duplicar papeles.

## Decisions

Decisiones técnicas (no de dominio). Suponen las opciones recomendadas de P-1 a P-12.

### D-1 — Reglas puras en `app/domain/patients/rules.py`
`normalize_document(text) -> str` (quita `[\s.\-]`, mayúsculas, valida `^[A-Z0-9]{6,20}$`, `ValueError` si no), `clean_name`, `clean_phone(text) -> str | None` (blanco → `None`), `check_birth_date(value, *, today: date)` → `InvalidPatientDataError`. El email reusa `normalize_email` e `is_valid_email` de `app/domain/users/rules.py` (misma regla que las cuentas). "Hoy" lo calcula el caso de uso con `to_local(clock(), timezone).date()` y la zona de `clinic_settings`, para que el borde de la medianoche local sea el de RN-GL-01. Errores en `app/domain/patients/errors.py`: `DocumentTakenError` (`DOCUMENT_TAKEN`), `PatientHasAppointmentsError` (`PATIENT_HAS_APPOINTMENTS`), `InvalidPatientDataError` (`INVALID_PATIENT_DATA`); se reusa `PatientNotFoundError` de `appointments/errors.py`. Mensajes fijos, sin datos del paciente.

### D-2 — Tipos y puerto ampliado
Se mantiene `Patient` (lo usa C-08) y se agregan en `types.py`: `PatientRecord` (ficha completa), `NewPatient` y `PatientChanges` (con el centinela `UNSET` del estilo de `professionals/types.py` para distinguir "no cambiar" de "borrar" en teléfono y fecha). Métodos nuevos en el mismo `PatientRepository` (DD-34): `get_record`, `search(*, text, include_inactive, limit)`, `add`, `update`, `set_active`, `delete -> bool`. `get` no cambia.

### D-3 — Implementaciones
**Memoria**: diccionario de `PatientRecord`; `add`/`update` chequean el documento contra todos; `search` usa `casefold()` para el apellido y `startswith` para el documento normalizado; si el texto no se puede normalizar como documento, solo se busca por apellido. **PostgreSQL**: `ILIKE` con `%`, `_` y `\` escapados (`ESCAPE '\'`) para el apellido, `LIKE 'prefijo%'` para el documento, `ORDER BY last_name, first_name, id`, `LIMIT`. `IntegrityError` con `pgcode 23505` sobre la restricción única de `document_number` → `DocumentTakenError`; `23503` al borrar → `PatientHasAppointmentsError`; en ambos casos **sin** registrar el detalle de la excepción (lleva el valor). Riesgo conocido: `casefold` e `ILIKE` difieren en casos raros (por ejemplo `ß`); la batería de contrato fija los casos del seed y los acentos comunes (`É`/`é`).

### D-4 — Casos de uso en `app/application/patients.py`
Funciones que reciben un `PatientDeps` (`patients`, `appointments`, `settings`, `clock`) y el `Principal`. Orden de cada escritura: rol (defensa en profundidad, RN-PR-02) → existe → validar → guardar. `search_patients` pide `limit + 1` (51) y devuelve `(items[:50], truncated)`. `deactivate_patient` llama a `set_active(False)` y luego `appointments.list_for_patient(id, now)` filtrando `scheduled` y `starts_at > now` (DD-23). `delete_patient`: chequea antes `list_for_patient(id, datetime.min UTC)`; si hay alguno → `PatientHasAppointmentsError` (necesario en memoria, donde el repositorio de pacientes no conoce los turnos); en PostgreSQL la clave foránea es la última barrera (D-3).

### D-5 — Reuso de la regla de RN-PA-04
No se toca `check_patient_can_book` ni el caso de uso de C-08: el efecto de desactivar se prueba agendando con los casos de uso reales de C-08 sobre los mismos repositorios en memoria (y en integración contra PostgreSQL).

### D-6 — Formato HTTP y validación
Router `app/api/patients.py` (prefijo `/patients`). Esquemas Pydantic con `extra="forbid"`; textos con `strip_text`; `document_number` con `AfterValidator` que llama a `normalize_document` (422 si `ValueError`); email con `_check_email` como en `users.py` (conviene moverlo a `validators.py`). `birth_date` como `str` con patrón `^\d{4}-\d{2}-\d{2}$` y conversión a `date` (hallazgo de Context7: un `date` laxo aceptaría `0`); fecha imposible (`2026-02-30`) → 422. `PATCH` usa `model_fields_set` para distinguir ausente de `null`; `null` en obligatorios → 422. `q` con `max_length=100`. Escrituras con `require_role(Role.ADMIN, Role.RECEPTIONIST)` (y solo `ADMIN` en `DELETE`) a nivel de ruta, así 403 llega antes que 422; lecturas con `current_user`. Fábrica `get_patient_deps` sobreescribible en `app/api/dependencies.py`, con `get_clock`. Salida `PatientOut`, `PatientSearchOut`, `DeactivationOut` con `UpcomingAppointmentOut` (instantes UTC como `appointment-api`).

### D-7 — Pantalla
`/pacientes` dentro de `RequireAuth` (los tres roles); el modo se decide con `useAuth()`. Cliente `frontend/src/api/patients.ts` sobre `apiFetch`; componentes en `frontend/src/patients/`: `PatientSearch` (buscador con espera de 300 ms, prop `onlyActive` y `onSelect`, reutilizable por C-10), `PatientForm` (alta/edición, `onSaved`), `PatientTable`, `DeactivationNotice`; mensajes en `patients/messages.ts`. Fechas en la zona del consultorio con la constante compartida de C-07. `window.confirm` no: diálogo propio accesible (`role="dialog"`), como el borrado de licencias de C-07. TypeScript estricto, sin `any`.

### D-8 — Tests
Dominio puro (`patient-data-rules`), batería de contrato ampliada (memoria y `postgres`), casos de uso con repositorios en memoria y reloj fijo (incluye agendar/cancelar con los casos de uso de C-08 tras desactivar y reactivar, y el caso de regla dura 6), API con tabla de permisos (7 endpoints × administrador, recepción, odontóloga con ficha, odontólogo sin ficha, sin token; "nada cambió" en cada 401/403; 403 antes que 422), integración con el seed (alta, duplicado concurrente con dos sesiones, desactivar a un paciente con turno agendado, borrar con y sin turnos), Vitest para la pantalla.

## Risks / Trade-offs

- [Búsqueda con acentos (P-3 = A)] → "perez" no encuentra "Pérez". Mitigación: aviso en la pantalla ("probá con tildes") o P-3 = B más adelante con migración.
- [Documento normalizado] → si alguien carga datos directo en la base sin normalizar, la unicidad podría no detectar un duplicado escrito distinto. El único camino de escritura es el caso de uso; el seed ya usa solo números.
- [Memoria vs PostgreSQL en mayúsculas/acentos] → diferencias en letras raras; la batería fija los casos usados.
- [Borrado con verificación previa] → entre la verificación y el `DELETE` otro pedido podría agendar un turno; en PostgreSQL la clave foránea lo impide igual (`PATIENT_HAS_APPOINTMENTS`).
- [Odontólogo ve todos los pacientes (P-4 = A)] → menos privacidad que B; aceptado con datos ficticios.
- [Registros de acceso con `q` (P-10 = A)] → nota para C-13.
- [Tamaño (40 tareas)] → ejecución por grupos con punto de corte tras el grupo 6 (P-12).
- [Regla dura 6] → C-06 no toca el constraint ni las reglas de agenda; la suite de C-08 corre como red de seguridad y se agrega un test explícito (reactivar no habilita superponer).

## Migration Plan

Sin migraciones ni variables de entorno nuevas con las opciones recomendadas (P-3 = B exigiría `CREATE EXTENSION unaccent` en una migración nueva). Despliegue: reconstruir imágenes de backend y frontend. Reversión: quitar el router de `app/api/router.py` y la ruta del frontend; los pacientes cargados siguen siendo válidos para C-08.

## Open Questions

Ninguna: P-1 a P-12 están resueltas (arriba). Notas para otros changes: C-10 usa `PatientSearch` (solo activos) y `PatientForm`; C-12 aplica la respuesta de P-8; C-13 revisa el registro de accesos (P-10).

## Revisión de escenarios (skill `revisor-escenarios-turnos`, 2026-11-04)

Aplicada solo a lo que cruza pacientes con turnos: requirements "Desactivar sin tocar los turnos", "Reactivar" y "La gestión de pacientes no altera la agenda" de `patient-management`, "Desactivar con turnos futuros" de `patient-api` y "Desactivar, reactivar y borrar" de `frontend-patient-management`.

### Resumen
13 escenarios revisados, 5 hallazgos (1 ambigüedad, 2 bordes faltantes, 0 reglas solapadas, 0 preguntas abiertas, 1 sin respaldo, 0 contrato incompleto, 1 contradicción). La contradicción y los bordes ya se corrigieron en las specs; las decisiones de dominio quedaron como P-7 y P-8.

### Hallazgos
| # | Tipo | Escenario afectado | Qué pasa | Respaldo en la KB | Sugerencia (a confirmar) |
|---|------|--------------------|----------|-------------------|--------------------------|
| 1 | Contradicción | Desactivar con turnos (pantalla) | El aviso borrador decía "reprogramalos o cancelalos", pero a un paciente inactivo no se le puede reprogramar | DD-25 (`09_decisiones_y_supuestos.md`), RN-PA-04 | Corregido: "Para reprogramarlos, reactivalo primero; si no, cancelalos" |
| 2 | Borde faltante | Desactivar sin tocar los turnos | Faltaba el turno que empieza exactamente ahora | DD-23 ("iniciado" = `now >= starts_at`) | Agregado: no se lista |
| 3 | Borde faltante | Desactivar sin tocar los turnos | No estaba probado que cancelar siga permitido para un paciente inactivo | RN-TU-05, DD-25 (solo bloquea agendar y reprogramar) | Agregado escenario de cancelación |
| 4 | Ambigüedad | Paciente con turnos futuros | DD-25 dice "se listan" sin decir dónde ni si se confirma antes | DD-25 | Listar en la respuesta y confirmar en pantalla (P-7) |
| 5 | Sin respaldo | (falta) Recordatorio de un turno de paciente inactivo | RN-NO-02 solo habla de turnos `scheduled`; nada sobre el paciente | RN-NO-02 (`05_reglas_de_negocio.md`); sin respaldo en la KB para el caso | Sigue recibiendo; nota para C-12 (P-8) |

### Escenarios sin hallazgos
Desactivar con turnos futuros (solo `scheduled` no iniciados, DD-25, DD-68 como criterio análogo), después no se le agenda (RN-PA-04), turno ya iniciado, ya inactivo, reactivar y agendar, ya activo, reactivar no habilita superponer (RN-TU-01, regla dura 6). Hay escenarios esperados, de error de negocio y de borde. No se inventaron estados ni campos: `upcoming_appointments` es de la respuesta, no de la base.

### Decisiones que necesitaban a la usuaria
P-7 y P-8: resueltas con la opción A el 2026-11-04.
