# error-model Specification

## Purpose
Dar a todos los errores de dominio una base común con un código estable y traducirlos en la API a una respuesta JSON uniforme, para que los changes siguientes (C-03, C-08) solo agreguen códigos y estados sin rediseñar el formato.

## Requirements

### Requirement: Errores de dominio con código

Todo error de dominio SHALL pertenecer a una familia común y MUST exponer un código estable en mayúsculas (por ejemplo `SLOT_TAKEN`). Los errores de dominio existentes (`SLOT_TAKEN`, `APPOINTMENT_NOT_FOUND`) MUST pertenecer a esa familia y MUST conservar su código, su mensaje y sus datos (profesional e inicio pedidos; identificador del turno).

#### Scenario: Error existente dentro de la familia común
- **WHEN** el repositorio de turnos rechaza un turno superpuesto con `SLOT_TAKEN`
- **THEN** el error pertenece a la familia de errores de dominio y conserva el código `SLOT_TAKEN`, el profesional y el inicio pedidos

#### Scenario: Batería de contrato sin cambios (borde)
- **WHEN** se corre la batería de contrato del repositorio de turnos después del cambio
- **THEN** todos sus escenarios pasan sin modificar ninguno

#### Scenario: Errores de programación fuera de la familia
- **WHEN** una función de dominio recibe una entrada inválida del llamador (por ejemplo un instante sin zona)
- **THEN** lanza `ValueError`, que no pertenece a la familia de errores de dominio (DD-18)

### Requirement: Respuesta HTTP uniforme para errores de dominio

La API SHALL convertir cualquier error de dominio no capturado en una respuesta JSON con la forma `{"error": {"code": "<CODIGO>", "message": "<texto>"}}`. El estado HTTP SHALL salir de una tabla de códigos a estados; un código que no figura en la tabla MUST responder 400. `APPOINTMENT_NOT_FOUND`, `USER_NOT_FOUND`, `PATIENT_NOT_FOUND` y `PROFESSIONAL_NOT_FOUND` MUST responder 404; `SLOT_TAKEN`, `EMAIL_TAKEN`, `ROLE_CHANGE_NOT_ALLOWED`, `SELF_MODIFICATION_NOT_ALLOWED`, `PATIENT_DOUBLE_BOOKED`, `PATIENT_INACTIVE`, `PROFESSIONAL_INACTIVE`, `CANCELLED_IS_FINAL`, `ATTENDANCE_ALREADY_RECORDED`, `ALREADY_STARTED` y `NOT_STARTED_YET` MUST responder 409; `INVALID_CREDENTIALS` y `NOT_AUTHENTICATED` MUST responder 401 y `FORBIDDEN` MUST responder 403. Los rechazos de reglas de agenda `INSUFFICIENT_NOTICE`, `OFF_GRID`, `OUTSIDE_WORKING_HOURS`, `PROFESSIONAL_TIME_OFF` y `RESCHEDULE_SAME_TIME` MUST responder 400. Toda respuesta 401 MUST incluir el encabezado `WWW-Authenticate: Bearer`. Los rechazos de autenticación y autorización MUST usar este mismo cuerpo uniforme y no el formato propio del framework. La respuesta MUST NOT incluir trazas de pila.

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

#### Scenario: Conflictos de estado de la agenda
- **WHEN** un endpoint deja escapar `PATIENT_DOUBLE_BOOKED`, `PATIENT_INACTIVE`, `PROFESSIONAL_INACTIVE`, `CANCELLED_IS_FINAL`, `ATTENDANCE_ALREADY_RECORDED`, `ALREADY_STARTED` o `NOT_STARTED_YET`
- **THEN** la respuesta es 409 con ese código en `error.code` y un `error.message` no vacío

#### Scenario: Reglas de agenda incumplidas
- **WHEN** un endpoint deja escapar `INSUFFICIENT_NOTICE`, `OFF_GRID`, `OUTSIDE_WORKING_HOURS`, `PROFESSIONAL_TIME_OFF` o `RESCHEDULE_SAME_TIME`
- **THEN** la respuesta es 400 con ese código en `error.code`

#### Scenario: Código sin estado asignado (borde)
- **WHEN** un endpoint deja escapar un error de dominio con un código que no figura en la tabla
- **THEN** la respuesta es 400 con ese código en `error.code`

#### Scenario: Error inesperado (error)
- **WHEN** un endpoint lanza un error que no es de dominio
- **THEN** la respuesta es 500 y su cuerpo no contiene la traza ni el mensaje interno del error

### Requirement: Los errores de validación no repiten lo enviado (RN-PR-03)

Una respuesta 422 por datos de entrada inválidos SHALL conservar la lista de errores por campo del framework (ubicación, tipo y mensaje de cada error), pero MUST NOT incluir los valores que envió el cliente, para que nunca se devuelva una contraseña.

#### Scenario: Alta con email mal formado (esperado)
- **WHEN** se envía un alta de usuario con email inválido y una contraseña válida
- **THEN** la respuesta es 422, indica el campo `email` como inválido y no contiene el texto de la contraseña ni del email enviados

#### Scenario: Login con contraseña desmedida (borde)
- **WHEN** se envía al login una contraseña de 129 caracteres
- **THEN** la respuesta es 422 y no contiene la contraseña enviada
