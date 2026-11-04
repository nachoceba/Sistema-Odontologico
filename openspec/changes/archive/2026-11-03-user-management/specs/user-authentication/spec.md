# Spec Delta: user-authentication

## ADDED Requirements

### Requirement: El login actualiza hashes con parámetros viejos (DD-55, P-12)

Cuando un inicio de sesión es exitoso y el hash guardado de la cuenta fue generado con parámetros de argon2 distintos de los vigentes, el sistema SHALL guardar un hash nuevo de la misma contraseña con los parámetros vigentes. Si guardar el hash nuevo falla, el login MUST igual responder 200 con el token. Un login fallido MUST NOT modificar el hash.

#### Scenario: Hash con parámetros viejos (esperado)
- **WHEN** una cuenta con un hash generado con parámetros más débiles inicia sesión con su contraseña correcta
- **THEN** el login responde 200 y el hash guardado pasa a tener los parámetros vigentes, y la misma contraseña sigue sirviendo

#### Scenario: Hash al día (borde)
- **WHEN** una cuenta con un hash generado con los parámetros vigentes inicia sesión
- **THEN** el hash guardado no cambia

#### Scenario: Contraseña incorrecta (error)
- **WHEN** una cuenta con un hash de parámetros viejos intenta iniciar sesión con una contraseña incorrecta
- **THEN** el login responde 401 y el hash guardado no cambia

#### Scenario: Falla al guardar el hash nuevo (borde)
- **WHEN** el login es correcto pero guardar el hash nuevo falla
- **THEN** el login responde 200 con el token y el hash anterior sigue sirviendo
