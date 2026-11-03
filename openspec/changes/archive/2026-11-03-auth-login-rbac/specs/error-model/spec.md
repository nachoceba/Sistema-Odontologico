# Spec Delta

## MODIFIED Requirements

### Requirement: Respuesta HTTP uniforme para errores de dominio

La API SHALL convertir cualquier error de dominio no capturado en una respuesta JSON con la forma `{"error": {"code": "<CODIGO>", "message": "<texto>"}}`. El estado HTTP SHALL salir de una tabla de códigos a estados; un código que no figura en la tabla MUST responder 400. `APPOINTMENT_NOT_FOUND` MUST responder 404, `SLOT_TAKEN` MUST responder 409, `INVALID_CREDENTIALS` y `NOT_AUTHENTICATED` MUST responder 401 y `FORBIDDEN` MUST responder 403. Toda respuesta 401 MUST incluir el encabezado `WWW-Authenticate: Bearer`. Los rechazos de autenticación y autorización MUST usar este mismo cuerpo uniforme y no el formato propio del framework. La respuesta MUST NOT incluir trazas de pila.

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

#### Scenario: Código sin estado asignado (borde)
- **WHEN** un endpoint deja escapar un error de dominio con un código que no figura en la tabla
- **THEN** la respuesta es 400 con ese código en `error.code`

#### Scenario: Error inesperado (error)
- **WHEN** un endpoint lanza un error que no es de dominio
- **THEN** la respuesta es 500 y su cuerpo no contiene la traza ni el mensaje interno del error
