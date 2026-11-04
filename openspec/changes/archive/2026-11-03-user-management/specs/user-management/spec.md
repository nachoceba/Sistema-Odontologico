# Spec Delta: user-management

## Purpose

Permitir que el administrador del consultorio dé de alta, edite, desactive, reactive y asigne contraseña a las cuentas del personal desde la API, creando la ficha de profesional de cada odontólogo en la misma operación y sin exponer nunca contraseñas ni hashes (US-002).

> Los valores marcados "(P-n, confirmada)" son la opción recomendada en `design.md`; si la usuaria elige otra, se ajustan antes de implementar (grupo 0 de `tasks.md`).

## ADDED Requirements

### Requirement: Solo el administrador gestiona usuarios (US-002, matriz RBAC, regla dura 4)

Toda ruta bajo `/api/v1/users` SHALL exigir sesión y el rol `admin`. Sin token MUST responder 401 con `error.code = "NOT_AUTHENTICATED"`; con sesión de `receptionist` o `dentist` MUST responder 403 con `error.code = "FORBIDDEN"` sin modificar ningún dato. Cada ruta MUST tener un test de permisos que pruebe los tres roles y la falta de token.

#### Scenario: Administrador accede (esperado)
- **WHEN** el administrador pide `GET /api/v1/users` con su token vigente
- **THEN** la respuesta es 200 con el listado de cuentas

#### Scenario: Recepción intenta crear un usuario (error de negocio)
- **WHEN** la recepcionista envía `POST /api/v1/users` con datos válidos
- **THEN** la respuesta es 403 con `error.code = "FORBIDDEN"` y no se crea ninguna cuenta

#### Scenario: Odontólogo intenta desactivar una cuenta (error de negocio)
- **WHEN** un odontólogo envía `POST /api/v1/users/{id}/deactivate` sobre la cuenta de la recepcionista
- **THEN** la respuesta es 403 con `error.code = "FORBIDDEN"` y la cuenta sigue activa

#### Scenario: Sin token (borde)
- **WHEN** se pide cualquier ruta de `/api/v1/users` sin encabezado `Authorization`
- **THEN** la respuesta es 401 (no 403) con `error.code = "NOT_AUTHENTICATED"`

### Requirement: Listado de usuarios

`GET /api/v1/users` SHALL devolver todas las cuentas, activas e inactivas, ordenadas por nombre completo sin distinguir mayúsculas, sin paginación (P-9, confirmada). Cada elemento MUST incluir `id`, `email`, `full_name`, `role`, `active` y `professional_id` (vacío si no tiene ficha) y MUST NOT incluir el hash ni la contraseña.

#### Scenario: Listado con el seed (esperado)
- **WHEN** el administrador pide el listado sobre la base con los datos del seed
- **THEN** recibe las cuatro cuentas ordenadas por nombre; las dos de odontólogo traen su `professional_id`

#### Scenario: Cuenta desactivada en el listado (borde)
- **WHEN** una cuenta está desactivada y el administrador pide el listado
- **THEN** la cuenta aparece con `active = false`

#### Scenario: Sin datos sensibles (error)
- **WHEN** el administrador pide el listado
- **THEN** ningún elemento de la respuesta contiene `password_hash` ni `password`

### Requirement: Alta de usuario con contraseña inicial (US-002, DD-38)

`POST /api/v1/users` SHALL crear una cuenta activa con `email`, `full_name`, `role` y `password` elegida por el administrador (P-1, confirmada). El email MUST recortarse y guardarse en minúsculas, MUST tener entre 3 y 254 caracteres, un único `@` y ningún espacio. El nombre MUST recortarse y tener entre 1 y 200 caracteres. La contraseña MUST tener entre 8 y 128 caracteres, no se recorta y se guarda solo como hash. Un email que ya existe, sin distinguir mayúsculas, MUST responder 409 con `error.code = "EMAIL_TAKEN"`. Campos faltantes o fuera de rango MUST responder 422. La respuesta exitosa MUST ser 201 con los mismos datos que un elemento del listado.

#### Scenario: Alta de recepcionista (esperado)
- **WHEN** el administrador crea `Nueva.Recepcion@Example.com ` con rol `receptionist` y contraseña de 12 caracteres
- **THEN** la respuesta es 201 con `email = "nueva.recepcion@example.com"`, `active = true` y `professional_id` vacío, y esa cuenta puede iniciar sesión con la contraseña elegida

#### Scenario: Email repetido con otras mayúsculas (error de negocio)
- **WHEN** el administrador crea una cuenta con el email de la recepcionista del seed escrito en mayúsculas
- **THEN** la respuesta es 409 con `error.code = "EMAIL_TAKEN"` y no se crea ninguna cuenta

#### Scenario: Contraseña demasiado corta (borde)
- **WHEN** el administrador envía una contraseña de 7 caracteres
- **THEN** la respuesta es 422 y no se crea ninguna cuenta

#### Scenario: Email mal formado (borde)
- **WHEN** el administrador envía el email `sin-arroba.example.com`
- **THEN** la respuesta es 422 y no se crea ninguna cuenta

#### Scenario: Rol inexistente (error)
- **WHEN** el administrador envía `role = "superadmin"`
- **THEN** la respuesta es 422

### Requirement: El alta de un odontólogo crea su ficha en la misma operación (US-002, DD-38)

Cuando la cuenta creada tiene rol `dentist`, el sistema SHALL crear su ficha en `professionals` en la misma transacción, con `display_name` (si no se envía, el nombre completo de la cuenta) y `license_number` opcional (P-10, confirmada), ambas activas. Si cualquiera de las dos inserciones falla, MUST NOT quedar ni la cuenta ni la ficha. Una cuenta de otro rol MUST NOT tener ficha.

#### Scenario: Alta de odontólogo con ficha (esperado)
- **WHEN** el administrador crea una cuenta `dentist` con nombre "Dra. Ficticia Nueva" y matrícula "MN-0001"
- **THEN** la respuesta es 201 con un `professional_id`, y la ficha tiene `display_name = "Dra. Ficticia Nueva"`, `license_number = "MN-0001"` y está activa

#### Scenario: Sin nombre a mostrar (borde)
- **WHEN** el administrador crea una cuenta `dentist` sin enviar `display_name`
- **THEN** la ficha toma como `display_name` el nombre completo de la cuenta

#### Scenario: Falla al crear la ficha (error)
- **WHEN** la inserción de la ficha falla después de insertar la cuenta
- **THEN** no queda ni la cuenta ni la ficha y el email sigue libre para un nuevo intento

#### Scenario: Recepcionista sin ficha (borde)
- **WHEN** el administrador crea una cuenta `receptionist` enviando también `license_number`
- **THEN** la cuenta se crea sin ficha de profesional

### Requirement: Edición de nombre y email

`PATCH /api/v1/users/{id}` SHALL permitir cambiar `full_name` y `email` (P-3, confirmada) con las mismas validaciones del alta; los campos no enviados no cambian. Un email ya usado por otra cuenta MUST responder 409 `EMAIL_TAKEN`. Un id inexistente o mal formado MUST responder 404 con `error.code = "USER_NOT_FOUND"`. Cambiar el email MUST NOT cerrar la sesión abierta de esa cuenta; desde ese momento inicia sesión con el email nuevo y el anterior deja de servir.

#### Scenario: Corregir el nombre (esperado)
- **WHEN** el administrador cambia el `full_name` de la recepcionista
- **THEN** la respuesta es 200 con el nombre nuevo y el resto de los datos sin cambios

#### Scenario: Email de otra cuenta (error de negocio)
- **WHEN** el administrador cambia el email de la recepcionista por el de un odontólogo
- **THEN** la respuesta es 409 con `error.code = "EMAIL_TAKEN"` y nada cambia

#### Scenario: Mismo email con otras mayúsculas en la propia cuenta (borde)
- **WHEN** el administrador envía para una cuenta su mismo email escrito con otras mayúsculas
- **THEN** la respuesta es 200 y el email queda en minúsculas

#### Scenario: Cuenta inexistente o id mal formado (error)
- **WHEN** el administrador edita un UUID que no existe o el texto `no-es-un-uuid`
- **THEN** la respuesta es 404 con `error.code = "USER_NOT_FOUND"`

### Requirement: Cambio de rol (RN-AU-02, DD-38)

`PATCH /api/v1/users/{id}` SHALL permitir cambiar el rol según estas reglas (P-4, confirmada): entre `admin` y `receptionist` se permite; de `admin` o `receptionist` a `dentist` se permite y crea la ficha en la misma transacción; de `dentist` a otro rol MUST responder 409 con `error.code = "ROLE_CHANGE_NOT_ALLOWED"` y nada cambia. Enviar el mismo rol que ya tiene no cambia nada y responde 200. El administrador MUST NOT cambiar su propio rol (409 `SELF_MODIFICATION_NOT_ALLOWED`, P-5). Toda ficha de profesional MUST pertenecer a una cuenta `dentist`. La sesión abierta de la cuenta cuyo rol cambió MUST recibir 401 en su siguiente llamada (spec access-control).

#### Scenario: Recepción pasa a administración (esperado)
- **WHEN** el administrador cambia el rol de la recepcionista a `admin`
- **THEN** la respuesta es 200 con `role = "admin"` y la siguiente llamada con el token anterior de esa cuenta recibe 401

#### Scenario: Recepción pasa a odontóloga (borde)
- **WHEN** el administrador cambia a `dentist` el rol de una cuenta `receptionist`
- **THEN** la respuesta es 200 con un `professional_id` nuevo y su ficha activa con el nombre de la cuenta

#### Scenario: Odontólogo a otro rol (error de negocio)
- **WHEN** el administrador cambia a `receptionist` el rol de un odontólogo del seed
- **THEN** la respuesta es 409 con `error.code = "ROLE_CHANGE_NOT_ALLOWED"` y la cuenta y su ficha no cambian

#### Scenario: Cambiar el propio rol (error de negocio)
- **WHEN** el administrador cambia su propio rol a `receptionist`
- **THEN** la respuesta es 409 con `error.code = "SELF_MODIFICATION_NOT_ALLOWED"`

### Requirement: Desactivar y reactivar cuentas (RN-AU-03, DD-39)

`POST /api/v1/users/{id}/deactivate` SHALL marcar la cuenta con `active = false` y `POST /api/v1/users/{id}/reactivate` SHALL volver a `active = true`; no existe borrado físico (P-8, confirmada). Ambas operaciones MUST ser idempotentes y responder 200 con los datos de la cuenta. Una cuenta desactivada MUST NOT poder iniciar sesión y su token vigente MUST recibir 401 en la siguiente llamada. Si la cuenta es de un odontólogo, su ficha MUST desactivarse y reactivarse junto con ella (P-7, confirmada), y sus turnos MUST NOT modificarse (P-6, confirmada). El administrador MUST NOT desactivarse a sí mismo (409 `SELF_MODIFICATION_NOT_ALLOWED`, P-5, confirmada); junto con la prohibición de cambiar su propio rol, esto garantiza que siempre quede al menos un administrador activo. Un id inexistente o mal formado MUST responder 404 `USER_NOT_FOUND`.

#### Scenario: Desactivar bloquea el login (esperado)
- **WHEN** el administrador desactiva a la recepcionista y ella intenta iniciar sesión con su contraseña correcta
- **THEN** la desactivación responde 200 con `active = false` y el login responde 401 `INVALID_CREDENTIALS`

#### Scenario: Sesión abierta de una cuenta desactivada (error de negocio)
- **WHEN** la recepcionista tiene un token vigente y el administrador la desactiva
- **THEN** la siguiente llamada de la recepcionista con ese token recibe 401 `NOT_AUTHENTICATED`

#### Scenario: Odontólogo con turnos futuros (borde)
- **WHEN** el administrador desactiva a un odontólogo que tiene turnos `scheduled` futuros
- **THEN** la cuenta y su ficha quedan inactivas y sus turnos conservan su estado

#### Scenario: Desactivarse a sí mismo (error de negocio)
- **WHEN** el administrador pide desactivar su propia cuenta
- **THEN** la respuesta es 409 con `error.code = "SELF_MODIFICATION_NOT_ALLOWED"` y sigue activo

#### Scenario: Un administrador desactiva a otro (borde)
- **WHEN** hay dos administradores activos y uno desactiva al otro
- **THEN** la respuesta es 200 y queda un administrador activo, que no puede desactivarse a sí mismo

#### Scenario: Reactivar (esperado)
- **WHEN** el administrador reactiva a un odontólogo desactivado
- **THEN** la cuenta y su ficha quedan activas y el odontólogo puede volver a iniciar sesión

#### Scenario: Desactivar dos veces (borde)
- **WHEN** el administrador desactiva una cuenta que ya está desactivada
- **THEN** la respuesta es 200 con `active = false` y nada más cambia

### Requirement: Asignar una contraseña nueva (P-2, confirmada)

`PUT /api/v1/users/{id}/password` SHALL reemplazar la contraseña de la cuenta por la que envía el administrador (8 a 128 caracteres, sin recortar) y responder 204 sin cuerpo. Desde ese momento la contraseña anterior MUST dejar de servir para iniciar sesión. Un id inexistente o mal formado MUST responder 404 `USER_NOT_FOUND`.

#### Scenario: Contraseña olvidada (esperado)
- **WHEN** el administrador asigna una contraseña nueva a la recepcionista
- **THEN** la respuesta es 204, el login con la nueva funciona y con la anterior responde 401

#### Scenario: Contraseña demasiado larga (borde)
- **WHEN** el administrador envía una contraseña de 129 caracteres
- **THEN** la respuesta es 422 y la contraseña anterior sigue sirviendo

#### Scenario: Cuenta inexistente (error)
- **WHEN** el administrador asigna contraseña a un UUID que no existe
- **THEN** la respuesta es 404 con `error.code = "USER_NOT_FOUND"`

### Requirement: Las contraseñas nunca salen del servidor (RN-PR-03, DD-41)

Ninguna respuesta de la API SHALL contener una contraseña ni un hash de contraseña, ni siquiera en errores de validación. Las contraseñas MUST guardarse solo como hash argon2 y MUST NOT escribirse en los registros (logs) de la aplicación.

#### Scenario: Error de validación con contraseña (borde)
- **WHEN** el alta responde 422 por un email mal formado y la contraseña enviada era válida
- **THEN** el cuerpo de la respuesta no contiene el texto de la contraseña

#### Scenario: Hash en la base (esperado)
- **WHEN** se crea una cuenta con una contraseña
- **THEN** la columna `password_hash` guarda un hash argon2 distinto del texto de la contraseña
