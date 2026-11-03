# user-authentication Specification

## Purpose
Permitir que el personal del consultorio (administración, recepción y odontólogos) inicie sesión con email y contraseña y obtenga un token de acceso de vida corta que identifica su cuenta y su rol, sin exponer nunca contraseñas, hashes ni secretos.

## Requirements

### Requirement: Inicio de sesión con email y contraseña (US-001, RN-AU-03, Flujo 1)

La API SHALL exponer `POST /api/v1/auth/login` como ruta pública que recibe un email y una contraseña. Si existe una cuenta con ese email (sin distinguir mayúsculas y sin espacios al inicio o al final, P-6), la contraseña coincide con su hash y la cuenta está activa, la respuesta MUST ser 200 con un token de acceso, su tipo (`bearer`), su vida en segundos y los datos públicos de la cuenta (id, nombre, rol y, si es odontólogo, el id de su profesional). En cualquier otro caso (email inexistente, contraseña incorrecta o cuenta con `active = false`) la respuesta MUST ser 401 con `error.code = "INVALID_CREDENTIALS"` y el mismo mensaje genérico, sin indicar qué dato falló ni si la cuenta existe (P-5, CONFIRMADA (2026-11-03)). La respuesta MUST NOT incluir el hash de la contraseña ni la contraseña recibida.

#### Scenario: Login válido (esperado)
- **WHEN** la recepcionista del seed envía su email y la contraseña correcta
- **THEN** la respuesta es 200 con un token de acceso, tipo `bearer`, vida de 1800 segundos (30 minutos, P-1 CONFIRMADA (2026-11-03)) y rol `receptionist`, y el cuerpo no contiene `password_hash` ni la contraseña

#### Scenario: Odontólogo recibe su profesional (esperado)
- **WHEN** un odontólogo del seed inicia sesión con sus credenciales correctas
- **THEN** la respuesta es 200, el rol es `dentist` y el id de profesional es el de su ficha en `professionals`

#### Scenario: Contraseña incorrecta (error de negocio)
- **WHEN** se envía el email del administrador con una contraseña equivocada
- **THEN** la respuesta es 401 con `error.code = "INVALID_CREDENTIALS"` y el mensaje genérico, y no se emite token

#### Scenario: Email inexistente con el mismo mensaje (error de negocio)
- **WHEN** se envía un email que no pertenece a ninguna cuenta
- **THEN** la respuesta es 401 con el mismo código y exactamente el mismo mensaje que con una contraseña incorrecta

#### Scenario: Cuenta desactivada (error de negocio, RN-AU-03)
- **WHEN** una cuenta con `active = false` envía su email y su contraseña correcta
- **THEN** la respuesta es 401 con `error.code = "INVALID_CREDENTIALS"` y el mismo mensaje genérico, y no se emite token

#### Scenario: Email con otras mayúsculas y espacios (borde, DD-38)
- **WHEN** el administrador escribe su email con mayúsculas distintas y un espacio al final, con la contraseña correcta
- **THEN** la respuesta es 200 y el token corresponde a la cuenta del administrador

#### Scenario: Campos vacíos o faltantes (borde)
- **WHEN** se envía el login sin contraseña o con el email vacío
- **THEN** la respuesta es 422 y no se consulta ninguna cuenta ni se emite token

#### Scenario: Contraseña desmedida (borde)
- **WHEN** se envía una contraseña de más de 128 caracteres
- **THEN** la respuesta es 422 sin intentar verificar el hash

### Requirement: Token de acceso firmado y de vida corta (DD-11)

El token de acceso SHALL estar firmado con `JWT_SECRET_KEY` y el algoritmo `JWT_ALGORITHM` y MUST contener solo el identificador de la cuenta, su rol, el instante de emisión y el vencimiento (`ACCESS_TOKEN_EXPIRE_MINUTES` después de la emisión). MUST NOT contener el email, el nombre, la contraseña ni el hash. Un token SHALL considerarse inválido si su firma no verifica con la clave del servidor, si usa otro algoritmo (incluido `none`), si le falta el vencimiento o el identificador, o si ya venció.

#### Scenario: Contenido mínimo del token (esperado)
- **WHEN** se decodifica el token emitido a la recepcionista
- **THEN** contiene el id de su cuenta, el rol `receptionist`, la emisión y un vencimiento 30 minutos posterior, y no contiene su email ni su nombre

#### Scenario: Token vencido (error de negocio)
- **WHEN** se presenta un token cuyo vencimiento ya pasó
- **THEN** el token se rechaza como no autenticado

#### Scenario: Token firmado con otra clave (error)
- **WHEN** se presenta un token con el mismo contenido pero firmado con una clave distinta de `JWT_SECRET_KEY`
- **THEN** el token se rechaza como no autenticado

#### Scenario: Token sin firma con algoritmo none (borde)
- **WHEN** se presenta un token con algoritmo `none` y sin firma
- **THEN** el token se rechaza como no autenticado

#### Scenario: Token sin vencimiento (borde)
- **WHEN** se presenta un token bien firmado pero sin vencimiento
- **THEN** el token se rechaza como no autenticado

### Requirement: Datos de la sesión actual

La API SHALL exponer `GET /api/v1/auth/me`, accesible para los tres roles con un token válido, que devuelve los datos públicos de la cuenta autenticada leídos de la base en ese momento: id, email, nombre, rol y el id de profesional (vacío si no es odontólogo) (P-9, CONFIRMADA (2026-11-03)). La respuesta MUST NOT incluir el hash de la contraseña, el token ni datos de pacientes.

#### Scenario: Cada rol ve sus propios datos (esperado)
- **WHEN** el administrador, la recepcionista y un odontólogo piden `GET /api/v1/auth/me` con su token
- **THEN** cada uno recibe 200 con sus propios datos y su rol, y el odontólogo además su id de profesional

#### Scenario: Sin token (error)
- **WHEN** se pide `GET /api/v1/auth/me` sin encabezado de autorización
- **THEN** la respuesta es 401 con `error.code = "NOT_AUTHENTICATED"`

#### Scenario: Nombre cambiado después del login (borde)
- **WHEN** el nombre de la cuenta cambia en la base mientras el token sigue vigente
- **THEN** `GET /api/v1/auth/me` devuelve el nombre nuevo, porque los datos salen de la base y no del token
