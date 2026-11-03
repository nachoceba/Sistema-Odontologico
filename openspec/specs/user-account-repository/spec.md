# user-account-repository Specification

## Purpose
Dar al login y al chequeo de sesión una forma de leer cuentas de usuario (por email o por identificador, junto con el profesional asociado si es odontólogo) que se comporte igual en memoria y en PostgreSQL, verificada por una batería de contrato común.

## Requirements

### Requirement: Buscar una cuenta por email sin distinguir mayúsculas (DD-38)

El repositorio de cuentas SHALL devolver la cuenta cuyo email coincide con el pedido sin distinguir mayúsculas, con su id, email, nombre, hash de contraseña, rol, estado activo y el id de su profesional (vacío si no tiene). Si ninguna cuenta coincide MUST devolver "sin resultado", sin lanzar error. Las implementaciones en memoria y PostgreSQL MUST pasar la misma batería de contrato.

#### Scenario: Email exacto (esperado)
- **WHEN** se busca el email de la recepcionista tal como se guardó
- **THEN** se obtiene su cuenta con rol `receptionist`, activa y sin profesional

#### Scenario: Email con otras mayúsculas (borde)
- **WHEN** se busca el email de un odontólogo escrito todo en mayúsculas
- **THEN** se obtiene su cuenta con rol `dentist` y el id de su profesional

#### Scenario: Email inexistente (error)
- **WHEN** se busca un email que no pertenece a ninguna cuenta
- **THEN** el resultado es "sin resultado"

#### Scenario: Cuenta desactivada se devuelve igual (borde)
- **WHEN** se busca el email de una cuenta con `active = false`
- **THEN** se obtiene la cuenta con `active = false`; decidir si puede entrar no es tarea del repositorio

### Requirement: Buscar una cuenta por identificador

El repositorio de cuentas SHALL devolver la cuenta con el identificador pedido con los mismos datos que la búsqueda por email. Un identificador inexistente o mal formado MUST devolver "sin resultado" sin lanzar error.

#### Scenario: Identificador existente (esperado)
- **WHEN** se busca por el id de la cuenta del administrador
- **THEN** se obtiene su cuenta con rol `admin`

#### Scenario: Identificador inexistente (error)
- **WHEN** se busca por un UUID válido que no corresponde a ninguna cuenta
- **THEN** el resultado es "sin resultado"

#### Scenario: Identificador mal formado (borde)
- **WHEN** se busca por un texto que no es un UUID
- **THEN** el resultado es "sin resultado" sin error de base de datos
