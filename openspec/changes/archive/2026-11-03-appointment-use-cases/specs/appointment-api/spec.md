# Spec Delta: appointment-api

## Purpose

Definir el contrato HTTP de los turnos bajo `/api/v1` (agendar, consultar, cancelar, reprogramar, marcar atención y franjas de un día), su formato de fechas y respuestas, y la matriz de permisos por rol que cada endpoint prueba con su propio test.

## ADDED Requirements

### Requirement: Endpoints de turnos

La API SHALL ofrecer, todos bajo `/api/v1` y con JWT obligatorio:

| Método y ruta | Uso | Respuesta correcta |
|---|---|---|
| `POST /appointments` (paciente, profesional, inicio) | Agendar | 201 con el turno |
| `GET /appointments/{id}` | Detalle | 200 con el turno |
| `GET /appointments?professional_id=…&from=…&to=…` | Turnos de un profesional en `[from, to)` | 200 con la lista |
| `POST /appointments/{id}/cancel` (motivo) | Cancelar | 200 con el turno |
| `POST /appointments/{id}/reschedule` (nuevo inicio) | Reprogramar | 200 con el turno |
| `POST /appointments/{id}/attendance` (`completed` o `no_show`) | Marcar atención | 200 con el turno |
| `GET /professionals/{professional_id}/slots?date=AAAA-MM-DD` | Franjas de un día local | 200 con la lista |

Un turno en la respuesta MUST contener identificador, paciente, profesional, inicio, fin, estado, motivo de cancelación (o nulo) y creador. No existe endpoint de borrado de turnos (RN-TU-05, DD-39).

#### Scenario: Agendar devuelve el turno creado (esperado)
- **WHEN** recepción envía `POST /api/v1/appointments` con un paciente activo, la Dra. A y un inicio libre válido
- **THEN** la respuesta es 201 con el turno en estado `scheduled`, su identificador y su fin calculado

#### Scenario: Borrar no existe (borde)
- **WHEN** el administrador envía `DELETE /api/v1/appointments/{id}`
- **THEN** la respuesta es 405 y el turno no cambia

#### Scenario: Turno inexistente (error de negocio)
- **WHEN** se pide `GET /api/v1/appointments/{id}` con un identificador que no existe
- **THEN** la respuesta es 404 con `error.code = "APPOINTMENT_NOT_FOUND"`

### Requirement: Formato de fechas y validación de entrada

Los instantes de entrada (`starts_at`, `from`, `to`) SHALL ser fechas y horas ISO 8601 con zona horaria explícita; un instante sin zona MUST responder 422. Los instantes de salida MUST ser UTC con zona explícita (RN-GL-01); el frontend los muestra en la zona del consultorio. `date` de las franjas es una fecha local del consultorio (`AAAA-MM-DD`). Campos faltantes, identificadores vacíos, un motivo de cancelación fuera de 1 a 500 caracteres tras recortar, un estado de atención distinto de `completed` y `no_show`, un rango con `from >= to` o de más de 31 días MUST responder 422 sin repetir los valores enviados (spec `error-model`).

#### Scenario: Inicio con zona de otro país (esperado)
- **WHEN** se agenda con `starts_at = "2026-11-09T16:00:00+03:00"`, que equivale a las 10:00 del consultorio
- **THEN** el turno se guarda como las 13:00 UTC y la respuesta lo devuelve en UTC

#### Scenario: Inicio sin zona horaria (error)
- **WHEN** se agenda con `starts_at = "2026-11-09T10:00:00"`
- **THEN** la respuesta es 422 y no se escribe nada

#### Scenario: Rango de listado demasiado largo (borde)
- **WHEN** se listan turnos con `from` y `to` separados por 32 días
- **THEN** la respuesta es 422

#### Scenario: Motivo vacío (error)
- **WHEN** se cancela con el motivo `"   "`
- **THEN** la respuesta es 422 y el turno sigue `scheduled`

### Requirement: Rechazos de negocio con código y estado HTTP

Cada rechazo de los casos de uso SHALL responder con el cuerpo uniforme de `error-model` y el estado de su código: 404 para `APPOINTMENT_NOT_FOUND`, `PATIENT_NOT_FOUND` y `PROFESSIONAL_NOT_FOUND`; 409 para `SLOT_TAKEN`, `PATIENT_DOUBLE_BOOKED`, `PATIENT_INACTIVE`, `PROFESSIONAL_INACTIVE`, `CANCELLED_IS_FINAL`, `ATTENDANCE_ALREADY_RECORDED`, `ALREADY_STARTED` y `NOT_STARTED_YET`; 400 para `INSUFFICIENT_NOTICE`, `OFF_GRID`, `OUTSIDE_WORKING_HOURS`, `PROFESSIONAL_TIME_OFF` y `RESCHEDULE_SAME_TIME`. El mensaje MUST estar en castellano y no contener datos de otros pacientes.

#### Scenario: Choque de slot (error de negocio)
- **WHEN** se agenda en un horario ya ocupado del profesional
- **THEN** la respuesta es 409 con `error.code = "SLOT_TAKEN"`

#### Scenario: Fuera de horario (error de negocio)
- **WHEN** se agenda fuera del horario de trabajo del profesional
- **THEN** la respuesta es 400 con `error.code = "OUTSIDE_WORKING_HOURS"`

#### Scenario: Doble turno del paciente sin revelar el otro turno (borde)
- **WHEN** se agenda a un paciente que ya tiene otro turno a esa hora con otro profesional
- **THEN** la respuesta es 409 con `error.code = "PATIENT_DOUBLE_BOOKED"` y el mensaje no incluye datos de ningún otro paciente

### Requirement: Matriz de permisos por endpoint (RN-AU-02, RN-AU-04, DD-48, DD-53)

Cada endpoint SHALL aplicar esta matriz, derivada de `03_actores_y_roles.md` (P-4 define la fila de atención):

| Endpoint | Administrador | Recepción | Odontólogo/a |
|---|---|---|---|
| Agendar, cancelar, reprogramar | Sí | Sí | No (403) |
| Detalle, listado, franjas | Cualquier profesional | Cualquier profesional | Solo su profesional (403 en ajenos) |
| Marcar atención | Cualquier turno | Cualquier turno | Solo turnos de su profesional (403 en ajenos) |

Sin token, cualquier endpoint MUST responder 401 antes de evaluar el rol. Un odontólogo sin ficha MUST recibir 403 en todo endpoint que lea o modifique turnos o franjas. Un rechazo por permisos MUST NOT modificar nada. Cada endpoint MUST tener un test de permisos que pruebe los tres roles y la falta de token (regla dura 4).

#### Scenario: Recepción agenda (esperado)
- **WHEN** la recepcionista agenda un turno válido
- **THEN** la respuesta es 201

#### Scenario: Odontólogo intenta agendar o cancelar (error de negocio)
- **WHEN** la Dra. A intenta agendar un turno con su propio profesional, o cancelar uno propio
- **THEN** la respuesta es 403 con `error.code = "FORBIDDEN"` y no cambia nada

#### Scenario: Odontóloga ve su agenda y no la ajena (esperado)
- **WHEN** la Dra. A lista sus turnos y después los del Dr. B
- **THEN** el primer pedido responde 200 y el segundo 403 con `error.code = "FORBIDDEN"`

#### Scenario: Odontóloga marca un turno ajeno (error de negocio)
- **WHEN** la Dra. A marca `completed` un turno iniciado del Dr. B
- **THEN** la respuesta es 403 y el turno sigue `scheduled`

#### Scenario: Odontólogo sin ficha (borde)
- **WHEN** una cuenta `dentist` sin ficha pide las franjas o el detalle de cualquier turno
- **THEN** la respuesta es 403

#### Scenario: Sin token (borde)
- **WHEN** se llama a cualquiera de los siete endpoints sin token
- **THEN** la respuesta es 401 con `error.code = "NOT_AUTHENTICATED"` (no 403) y nada cambia
