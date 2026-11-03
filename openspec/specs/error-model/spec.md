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

La API SHALL convertir cualquier error de dominio no capturado en una respuesta JSON con la forma `{"error": {"code": "<CODIGO>", "message": "<texto>"}}`. El estado HTTP SHALL salir de una tabla de códigos a estados; un código que no figura en la tabla MUST responder 400. `APPOINTMENT_NOT_FOUND` MUST responder 404 y `SLOT_TAKEN` MUST responder 409. La respuesta MUST NOT incluir trazas de pila.

#### Scenario: Código conocido
- **WHEN** un endpoint deja escapar un error `APPOINTMENT_NOT_FOUND`
- **THEN** la respuesta es 404 con `error.code = "APPOINTMENT_NOT_FOUND"` y un `error.message` no vacío

#### Scenario: Conflicto de horario
- **WHEN** un endpoint deja escapar un error `SLOT_TAKEN`
- **THEN** la respuesta es 409 con `error.code = "SLOT_TAKEN"`

#### Scenario: Código sin estado asignado (borde)
- **WHEN** un endpoint deja escapar un error de dominio con un código que no figura en la tabla
- **THEN** la respuesta es 400 con ese código en `error.code`

#### Scenario: Error inesperado (error)
- **WHEN** un endpoint lanza un error que no es de dominio
- **THEN** la respuesta es 500 y su cuerpo no contiene la traza ni el mensaje interno del error
