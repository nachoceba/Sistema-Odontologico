# Spec Delta: user-account-repository

## ADDED Requirements

### Requirement: Listar todas las cuentas

El repositorio de cuentas SHALL devolver todas las cuentas, activas e inactivas, con los mismos datos que la búsqueda por id, ordenadas por nombre completo sin distinguir mayúsculas. Las implementaciones en memoria y PostgreSQL MUST pasar la misma batería de contrato.

#### Scenario: Listado completo (esperado)
- **WHEN** se listan las cuentas con un administrador, una recepcionista y dos odontólogos cargados
- **THEN** se obtienen las cuatro ordenadas por nombre, con el id de profesional en las de odontólogo

#### Scenario: Cuentas desactivadas incluidas (borde)
- **WHEN** una de las cuentas tiene `active = false`
- **THEN** aparece en el listado con `active = false`

#### Scenario: Repositorio vacío (borde)
- **WHEN** no hay ninguna cuenta
- **THEN** el listado es vacío, sin error

### Requirement: Crear una cuenta, con su ficha si es odontólogo, en una sola operación (DD-38)

El repositorio SHALL crear una cuenta activa con email, nombre, hash de contraseña y rol, y devolverla con su id. Si se piden datos de ficha, MUST crear también la ficha de profesional asociada en la misma transacción y devolver su id en la cuenta. Si el email ya existe sin distinguir mayúsculas MUST lanzar el error `EMAIL_TAKEN` y no crear nada. Si la creación de la ficha falla, MUST NOT quedar la cuenta.

#### Scenario: Crear recepcionista (esperado)
- **WHEN** se crea una cuenta `receptionist` sin datos de ficha
- **THEN** la búsqueda por su email la devuelve activa y sin profesional

#### Scenario: Crear odontólogo con ficha (esperado)
- **WHEN** se crea una cuenta `dentist` con nombre a mostrar y matrícula
- **THEN** la cuenta devuelta tiene id de profesional y la ficha existe activa con esos datos

#### Scenario: Email duplicado con otras mayúsculas (error)
- **WHEN** se crea una cuenta con el email de otra cuenta escrito en mayúsculas
- **THEN** se lanza `EMAIL_TAKEN` y la cantidad de cuentas no cambia

#### Scenario: Falla en la ficha deshace la cuenta (borde)
- **WHEN** la inserción de la ficha falla después de insertar la cuenta
- **THEN** no queda ni la cuenta ni la ficha

### Requirement: Actualizar los datos de una cuenta

El repositorio SHALL actualizar el nombre, el email, el rol, el hash de contraseña y el estado activo de una cuenta existente y devolver la cuenta actualizada. Al pasar a `dentist` una cuenta sin ficha, MUST crear su ficha en la misma transacción. Al cambiar el estado activo de una cuenta con ficha, MUST aplicar el mismo estado a su ficha en la misma transacción. Un email que ya usa otra cuenta MUST lanzar `EMAIL_TAKEN` sin cambiar nada. Un id inexistente o mal formado MUST lanzar `USER_NOT_FOUND`.

#### Scenario: Cambiar nombre y email (esperado)
- **WHEN** se cambian el nombre y el email de la recepcionista
- **THEN** la búsqueda por el email nuevo la devuelve con el nombre nuevo y la búsqueda por el email anterior no devuelve nada

#### Scenario: Email de otra cuenta (error)
- **WHEN** se cambia el email de una cuenta por el de otra
- **THEN** se lanza `EMAIL_TAKEN` y ninguna de las dos cambia

#### Scenario: Pasar a odontólogo crea la ficha (borde)
- **WHEN** se cambia a `dentist` el rol de una cuenta sin ficha, con nombre a mostrar
- **THEN** la cuenta devuelta tiene id de profesional y la ficha está activa

#### Scenario: Desactivar un odontólogo desactiva su ficha (esperado)
- **WHEN** se desactiva la cuenta de un odontólogo
- **THEN** la cuenta y su ficha quedan con `active = false`

#### Scenario: Cambiar el hash (esperado)
- **WHEN** se reemplaza el hash de contraseña de una cuenta
- **THEN** la búsqueda por id devuelve el hash nuevo

#### Scenario: Cuenta inexistente o id mal formado (error)
- **WHEN** se actualiza un UUID que no existe o un texto que no es un UUID
- **THEN** se lanza `USER_NOT_FOUND` sin error de base de datos
