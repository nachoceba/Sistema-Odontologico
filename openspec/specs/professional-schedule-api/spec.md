# professional-schedule-api Specification

## Purpose
Definir el contrato HTTP bajo `/api/v1/professionals` para ver y editar fichas, horarios semanales y licencias y para consultar turnos en conflicto, con su formato de entrada y salida y la matriz de permisos por rol que cada endpoint prueba con su propio test.

## Requirements

### Requirement: Endpoints de profesionales, horarios y licencias

La API SHALL ofrecer, todos bajo `/api/v1` y con JWT obligatorio:

| Método y ruta | Uso | Quién | Respuesta correcta |
|---|---|---|---|
| `GET /professionals` | Listar fichas | admin, recepción, odontólogo (solo la propia) | 200 con la lista |
| `GET /professionals/{id}` | Ver una ficha | admin, recepción, odontólogo propio | 200 con la ficha |
| `PATCH /professionals/{id}` (nombre a mostrar, matrícula) | Editar ficha | admin | 200 con la ficha |
| `GET /professionals/{id}/working-hours` | Leer horario | admin, recepción, odontólogo propio | 200 con los tramos |
| `PUT /professionals/{id}/working-hours` (semana completa) | Reemplazar horario | admin | 200 con tramos y conflictos |
| `GET /professionals/{id}/time-off` | Listar licencias | admin, recepción, odontólogo propio | 200 con la lista |
| `POST /professionals/{id}/time-off` (inicio, fin, motivo) | Cargar licencia | admin | 201 con licencia y conflictos |
| `DELETE /professionals/{id}/time-off/{time_off_id}` | Borrar licencia (P-4) | admin | 204 sin cuerpo |
| `GET /professionals/{id}/conflicts` | Turnos en conflicto | admin, recepción, odontólogo propio | 200 con la lista |

Una ficha en la respuesta MUST contener identificador, nombre a mostrar, matrícula (o nulo) y estado activo; MUST NOT contener datos de la cuenta (email, hash). Un tramo MUST contener día de la semana (0 = lunes a 6 = domingo), hora de inicio y hora de fin como texto `HH:MM`. Una licencia MUST contener identificador, fecha de inicio, fecha de fin (`AAAA-MM-DD`, fechas locales inclusivas) y motivo (o nulo). Un conflicto MUST contener el identificador del turno, el paciente (solo su identificador), el profesional, inicio y fin en UTC y el motivo (`OUTSIDE_WORKING_HOURS` o `TIME_OFF`). El endpoint existente `GET /professionals/{id}/slots` de `appointment-api` MUST seguir igual.

#### Scenario: Reemplazar el horario devuelve tramos y conflictos (esperado)
- **WHEN** el administrador envía `PUT /api/v1/professionals/{Dra. A}/working-hours` con `{"blocks": [{"weekday": 0, "start_time": "09:00", "end_time": "13:00"}]}`
- **THEN** la respuesta es 200 con `blocks` igual al tramo enviado y `conflicts` con los turnos afectados (o vacío)

#### Scenario: Cargar una licencia devuelve 201 (esperado)
- **WHEN** el administrador envía `POST /api/v1/professionals/{Dra. A}/time-off` con `{"starts_on": "2026-10-12", "ends_on": "2026-10-16", "reason": "Congreso"}`
- **THEN** la respuesta es 201 con la licencia guardada (con identificador) y la lista `conflicts`

#### Scenario: Borrar una licencia devuelve 204 (esperado)
- **WHEN** el administrador envía `DELETE` sobre una licencia existente de la Dra. A
- **THEN** la respuesta es 204 y la licencia ya no aparece en `GET .../time-off`

#### Scenario: La ficha no expone la cuenta (borde)
- **WHEN** recepción pide `GET /api/v1/professionals/{Dra. A}`
- **THEN** la respuesta no contiene email, contraseña ni hash

#### Scenario: Las franjas siguen igual (borde)
- **WHEN** se pide `GET /api/v1/professionals/{Dra. A}/slots?date=2026-10-05` después de este change
- **THEN** responde con el mismo formato y las mismas reglas que define `appointment-api`

### Requirement: Validación de entrada de horarios, licencias y fichas

Las horas de un tramo SHALL llegar como texto `HH:MM` de 24 horas (de `00:00` a `23:59`), sin segundos ni zona horaria; cualquier otro formato (con segundos, con zona, número, `24:00`) MUST responder 422. El día de la semana MUST ser un entero; fuera de 0 a 6 MUST rechazarse. Un pedido de horario sin la lista `blocks` MUST responder 422; una lista vacía es válida. Las fechas de licencia MUST ser `AAAA-MM-DD`. El motivo de licencia MUST tener como máximo 500 caracteres tras recortar; el nombre a mostrar, de 1 a 200; la matrícula, de 1 a 50, o `null` para borrarla. Toda respuesta 422 MUST NOT repetir los valores enviados (`error-model`). Las reglas de dominio (superposición, inicio no anterior al fin, día fuera de rango, fin de licencia anterior al inicio) MUST responder 400 con `INVALID_WORKING_HOURS` o `INVALID_TIME_OFF` y un mensaje que nombre el problema y la posición del tramo, sin repetir los datos enviados.

#### Scenario: Hora con segundos (error)
- **WHEN** el administrador envía un tramo con `"start_time": "09:00:30"`
- **THEN** la respuesta es 422 y no contiene el valor enviado

#### Scenario: Hora con zona horaria (borde)
- **WHEN** el administrador envía un tramo con `"start_time": "09:00Z"`
- **THEN** la respuesta es 422

#### Scenario: Superposición informa los tramos (error de negocio)
- **WHEN** el administrador envía lunes 09:00–13:00 y lunes 12:00–15:00
- **THEN** la respuesta es 400 con `error.code = "INVALID_WORKING_HOURS"` y un mensaje que indica que los tramos 1 y 2 se superponen

#### Scenario: Día de la semana 7 (error de negocio)
- **WHEN** el administrador envía un tramo con `"weekday": 7`
- **THEN** la respuesta es 400 con `error.code = "INVALID_WORKING_HOURS"` y el horario no cambia

#### Scenario: Licencia con fin anterior al inicio (error de negocio)
- **WHEN** el administrador envía `{"starts_on": "2026-10-16", "ends_on": "2026-10-12"}`
- **THEN** la respuesta es 400 con `error.code = "INVALID_TIME_OFF"`

#### Scenario: Motivo demasiado largo (borde)
- **WHEN** el administrador envía un motivo de 501 caracteres
- **THEN** la respuesta es 422 sin repetir el motivo

#### Scenario: Nombre a mostrar vacío (borde)
- **WHEN** el administrador envía `PATCH` con `"display_name": "   "`
- **THEN** la respuesta es 422 y la ficha no cambia

### Requirement: Permisos por rol de cada endpoint (regla dura 4)

Cada endpoint de esta spec SHALL tener su test de permisos con: administrador, recepción, odontólogo sobre lo propio, odontólogo sobre lo ajeno, odontólogo sin ficha y sin token. Sin token MUST responder 401 antes que cualquier chequeo de rol. Los endpoints de escritura MUST responder 403 `FORBIDDEN` a recepción y a cualquier odontólogo, y el test MUST comprobar que nada cambió. Los endpoints de lectura MUST responder 403 al odontólogo con un profesional ajeno, con un identificador mal formado o sin ficha (DD-53). Un identificador inexistente MUST responder 404 `PROFESSIONAL_NOT_FOUND` a administración y recepción. El 403 por rol MUST ocurrir antes que el 422 por datos inválidos.

#### Scenario: Matriz completa (esperado)
- **WHEN** se ejecuta la tabla de permisos sobre los nueve endpoints con los seis tipos de llamador
- **THEN** cada combinación responde según la matriz de esta spec y ningún 401 o 403 deja cambios

#### Scenario: Odontóloga lee su horario (esperado)
- **WHEN** la Dra. A pide `GET /api/v1/professionals/{Dra. A}/working-hours`
- **THEN** la respuesta es 200 con sus tramos

#### Scenario: Odontóloga lee el horario ajeno (error de negocio)
- **WHEN** la Dra. A pide `GET /api/v1/professionals/{Dr. B}/time-off`
- **THEN** la respuesta es 403 `FORBIDDEN`

#### Scenario: Recepción con cuerpo inválido sigue recibiendo 403 (borde)
- **WHEN** recepción envía `PUT .../working-hours` con un cuerpo mal formado
- **THEN** la respuesta es 403, no 422

#### Scenario: Listado del odontólogo sin ficha (borde)
- **WHEN** un odontólogo sin ficha pide `GET /api/v1/professionals`
- **THEN** la respuesta es 200 con una lista vacía

#### Scenario: Sin token (error)
- **WHEN** se pide cualquiera de los nueve endpoints sin encabezado de autorización
- **THEN** la respuesta es 401 `NOT_AUTHENTICATED` con `WWW-Authenticate: Bearer`

#### Scenario: Las rutas nuevas están protegidas (borde)
- **WHEN** corre el test de inventario de rutas
- **THEN** todas las rutas nuevas dependen de la sesión y el inventario pasa
