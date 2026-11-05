# Spec Delta: error-model

## MODIFIED Requirements

### Requirement: Respuesta HTTP uniforme para errores de dominio

La API SHALL convertir cualquier error de dominio no capturado en una respuesta JSON con la forma `{"error": {"code": "<CODIGO>", "message": "<texto>"}}`. El estado HTTP SHALL salir de una tabla de códigos a estados; un código que no figura en la tabla MUST responder 400. `APPOINTMENT_NOT_FOUND`, `USER_NOT_FOUND`, `PATIENT_NOT_FOUND`, `PROFESSIONAL_NOT_FOUND` y `TIME_OFF_NOT_FOUND` MUST responder 404; `SLOT_TAKEN`, `EMAIL_TAKEN`, `DOCUMENT_TAKEN`, `PATIENT_HAS_APPOINTMENTS`, `ROLE_CHANGE_NOT_ALLOWED`, `SELF_MODIFICATION_NOT_ALLOWED`, `PATIENT_DOUBLE_BOOKED`, `PATIENT_INACTIVE`, `PROFESSIONAL_INACTIVE`, `CANCELLED_IS_FINAL`, `ATTENDANCE_ALREADY_RECORDED`, `ALREADY_STARTED` y `NOT_STARTED_YET` MUST responder 409; `INVALID_CREDENTIALS` y `NOT_AUTHENTICATED` MUST responder 401 y `FORBIDDEN` MUST responder 403. Los rechazos de reglas de agenda `INSUFFICIENT_NOTICE`, `OFF_GRID`, `OUTSIDE_WORKING_HOURS`, `PROFESSIONAL_TIME_OFF` y `RESCHEDULE_SAME_TIME`, los rechazos de reglas de horarios `INVALID_WORKING_HOURS` e `INVALID_TIME_OFF`, y el rechazo de datos de paciente `INVALID_PATIENT_DATA`, MUST responder 400. Toda respuesta 401 MUST incluir el encabezado `WWW-Authenticate: Bearer`. Los rechazos de autenticación y autorización MUST usar este mismo cuerpo uniforme y no el formato propio del framework. La respuesta MUST NOT incluir trazas de pila.

#### Scenario: Código conocido
- **WHEN** un endpoint deja escapar un error `APPOINTMENT_NOT_FOUND`
- **THEN** la respuesta es 404 con `error.code = "APPOINTMENT_NOT_FOUND"` y un `error.message` no vacío

#### Scenario: Conflicto de horario
- **WHEN** un endpoint deja escapar un error `SLOT_TAKEN`
- **THEN** la respuesta es 409 con `error.code = "SLOT_TAKEN"`

#### Scenario: Sin sesión con encabezado de desafío
- **WHEN** un endpoint deja escapar un error `NOT_AUTHENTICATED`
- **THEN** la respuesta es 401 con `error.code = "NOT_AUTHENTICATED"` y el encabezado `WWW-Authenticate: Bearer`

#### Scenario: Credenciales inválidas
- **WHEN** el login deja escapar un error `INVALID_CREDENTIALS`
- **THEN** la respuesta es 401 con `error.code = "INVALID_CREDENTIALS"` y el encabezado `WWW-Authenticate: Bearer`

#### Scenario: Sin permiso
- **WHEN** un endpoint deja escapar un error `FORBIDDEN`
- **THEN** la respuesta es 403 con `error.code = "FORBIDDEN"` y sin encabezado `WWW-Authenticate`

#### Scenario: Usuario inexistente
- **WHEN** un endpoint deja escapar un error `USER_NOT_FOUND`
- **THEN** la respuesta es 404 con `error.code = "USER_NOT_FOUND"`

#### Scenario: Conflictos de la gestión de usuarios
- **WHEN** un endpoint deja escapar un error `EMAIL_TAKEN`, `ROLE_CHANGE_NOT_ALLOWED` o `SELF_MODIFICATION_NOT_ALLOWED`
- **THEN** la respuesta es 409 con ese código en `error.code`, un `error.message` no vacío y sin encabezado `WWW-Authenticate`

#### Scenario: Paciente o profesional inexistente
- **WHEN** un endpoint deja escapar un error `PATIENT_NOT_FOUND` o `PROFESSIONAL_NOT_FOUND`
- **THEN** la respuesta es 404 con ese código en `error.code`

#### Scenario: Licencia inexistente
- **WHEN** un endpoint deja escapar un error `TIME_OFF_NOT_FOUND`
- **THEN** la respuesta es 404 con `error.code = "TIME_OFF_NOT_FOUND"`

#### Scenario: Conflictos de estado de la agenda
- **WHEN** un endpoint deja escapar `PATIENT_DOUBLE_BOOKED`, `PATIENT_INACTIVE`, `PROFESSIONAL_INACTIVE`, `CANCELLED_IS_FINAL`, `ATTENDANCE_ALREADY_RECORDED`, `ALREADY_STARTED` o `NOT_STARTED_YET`
- **THEN** la respuesta es 409 con ese código en `error.code` y un `error.message` no vacío

#### Scenario: Reglas de agenda incumplidas
- **WHEN** un endpoint deja escapar `INSUFFICIENT_NOTICE`, `OFF_GRID`, `OUTSIDE_WORKING_HOURS`, `PROFESSIONAL_TIME_OFF` o `RESCHEDULE_SAME_TIME`
- **THEN** la respuesta es 400 con ese código en `error.code`

#### Scenario: Reglas de horarios incumplidas
- **WHEN** un endpoint deja escapar `INVALID_WORKING_HOURS` o `INVALID_TIME_OFF`
- **THEN** la respuesta es 400 con ese código en `error.code` y un `error.message` no vacío que no repite los datos enviados

#### Scenario: Conflictos de la gestión de pacientes
- **WHEN** un endpoint deja escapar un error `DOCUMENT_TAKEN` o `PATIENT_HAS_APPOINTMENTS`
- **THEN** la respuesta es 409 con ese código en `error.code` y un `error.message` no vacío que no incluye datos del paciente

#### Scenario: Datos de paciente inválidos
- **WHEN** un endpoint deja escapar un error `INVALID_PATIENT_DATA`
- **THEN** la respuesta es 400 con `error.code = "INVALID_PATIENT_DATA"` y un `error.message` no vacío que no repite los datos enviados

#### Scenario: Código sin estado asignado (borde)
- **WHEN** un endpoint deja escapar un error de dominio con un código que no figura en la tabla
- **THEN** la respuesta es 400 con ese código en `error.code`

#### Scenario: Error inesperado (error)
- **WHEN** un endpoint lanza un error que no es de dominio
- **THEN** la respuesta es 500 y su cuerpo no contiene la traza ni el mensaje interno del error
