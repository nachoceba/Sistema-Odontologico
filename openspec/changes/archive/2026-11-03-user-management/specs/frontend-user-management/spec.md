# Spec Delta: frontend-user-management

## Purpose

Darle al administrador una pantalla `/usuarios` para ver, crear, editar, desactivar, reactivar y asignar contraseña a las cuentas del personal, mostrando los rechazos de la API con mensajes claros y sin guardar contraseñas en el navegador.

## ADDED Requirements

### Requirement: Acceso a la pantalla de usuarios (matriz RBAC)

El frontend SHALL ofrecer la ruta protegida `/usuarios`. El enlace "Usuarios" MUST mostrarse solo cuando la cuenta con sesión tiene rol `admin`. Una cuenta de otro rol que abre `/usuarios` escribiendo la dirección MUST ver el aviso "No tenés permiso para esta acción" con un enlace a `/agenda`, sin pedir el listado a la API y sin perder la sesión (P-11, confirmada). Sin sesión, `/usuarios` lleva a `/login` como toda ruta protegida.

#### Scenario: Administrador ve el enlace (esperado)
- **WHEN** el administrador con sesión está en `/agenda`
- **THEN** ve el enlace "Usuarios" que lleva a `/usuarios`

#### Scenario: Recepción no ve el enlace (esperado)
- **WHEN** la recepcionista con sesión está en `/agenda`
- **THEN** no ve el enlace "Usuarios"

#### Scenario: Odontólogo escribe la dirección (error de negocio)
- **WHEN** un odontólogo con sesión abre `/usuarios`
- **THEN** ve "No tenés permiso para esta acción", su sesión sigue abierta y no se pidió `GET /api/v1/users`

#### Scenario: Sin sesión (borde)
- **WHEN** alguien sin token abre `/usuarios`
- **THEN** el frontend lo lleva a `/login`

### Requirement: Listado de usuarios en pantalla

La pantalla `/usuarios` SHALL mostrar una tabla con nombre, email, rol en castellano ("Administrador", "Recepción", "Odontólogo/a") y estado ("Activo" o "Inactivo") de cada cuenta que devuelve `GET /api/v1/users`, en el orden recibido. Mientras carga MUST mostrar "Cargando…"; ante un error de red o un 5xx MUST mostrar "No se pudo conectar con el servidor".

#### Scenario: Tabla con las cuentas (esperado)
- **WHEN** la API devuelve cuatro cuentas, una inactiva
- **THEN** la tabla muestra las cuatro y la inactiva con el estado "Inactivo"

#### Scenario: Servidor caído (error)
- **WHEN** la solicitud del listado falla por error de red
- **THEN** la pantalla muestra "No se pudo conectar con el servidor"

### Requirement: Formulario de alta

La pantalla SHALL ofrecer un formulario de alta con email, nombre completo, rol y contraseña inicial (campo de tipo contraseña). Si el rol elegido es odontólogo/a, MUST mostrar además "Nombre a mostrar" (opcional) y "Matrícula" (opcional). Mientras espera, el botón MUST quedar deshabilitado. Si la API responde 201, la cuenta nueva MUST aparecer en la tabla y el formulario se vacía. Si responde 409 `EMAIL_TAKEN`, MUST mostrar "Ya existe un usuario con ese email" conservando lo escrito salvo la contraseña. Si responde 422, MUST mostrar "Revisá los datos: hay campos inválidos". La contraseña MUST NOT guardarse en ningún almacenamiento del navegador.

#### Scenario: Alta de odontóloga (esperado)
- **WHEN** el administrador completa el formulario con rol odontólogo/a y matrícula, y envía
- **THEN** se envía `POST /api/v1/users` con esos datos y la cuenta nueva aparece en la tabla

#### Scenario: Email repetido (error de negocio)
- **WHEN** la API responde 409 con `error.code = "EMAIL_TAKEN"`
- **THEN** la pantalla muestra "Ya existe un usuario con ese email", conserva email y nombre y vacía la contraseña

#### Scenario: Campos de ficha solo para odontólogos (borde)
- **WHEN** el administrador elige el rol "Recepción" en el formulario
- **THEN** no se muestran "Nombre a mostrar" ni "Matrícula"

#### Scenario: Envío doble (borde)
- **WHEN** el administrador hace clic dos veces seguidas en "Crear"
- **THEN** se envía una sola solicitud de alta

### Requirement: Editar, desactivar, reactivar y asignar contraseña

Cada fila SHALL ofrecer "Editar" (nombre, email y rol), "Desactivar" o "Reactivar" según su estado, y "Asignar contraseña". Desactivar MUST pedir confirmación antes de llamar a la API e informar, si la cuenta es de un odontólogo, que sus turnos futuros no se cancelan. En la fila de la propia cuenta del administrador MUST NOT ofrecerse "Desactivar" ni el cambio de rol. Para una cuenta de odontólogo, el selector de rol MUST NOT ofrecer otros roles (P-4, confirmada). Los rechazos de la API MUST mostrarse con estos mensajes: `EMAIL_TAKEN` → "Ya existe un usuario con ese email"; `ROLE_CHANGE_NOT_ALLOWED` → "No se puede cambiar el rol de un odontólogo"; `SELF_MODIFICATION_NOT_ALLOWED` → "No podés desactivar ni cambiar el rol de tu propia cuenta"; `USER_NOT_FOUND` → "El usuario ya no existe", y en ese caso la tabla se vuelve a cargar.

#### Scenario: Desactivar con confirmación (esperado)
- **WHEN** el administrador hace clic en "Desactivar" en la fila de la recepcionista y confirma
- **THEN** se envía `POST /api/v1/users/{id}/deactivate` y la fila pasa a "Inactivo" con el botón "Reactivar"

#### Scenario: Cancelar la confirmación (borde)
- **WHEN** el administrador hace clic en "Desactivar" y cancela la confirmación
- **THEN** no se envía ninguna solicitud y la fila no cambia

#### Scenario: Propia fila sin desactivar (borde)
- **WHEN** el administrador mira la fila de su propia cuenta
- **THEN** no ve "Desactivar" y el rol no se puede cambiar

#### Scenario: Rol de odontólogo bloqueado (borde)
- **WHEN** el administrador edita la cuenta de un odontólogo
- **THEN** el selector de rol solo ofrece "Odontólogo/a"

#### Scenario: Rechazo de la API al editar (error de negocio)
- **WHEN** al guardar una edición la API responde 409 con `error.code = "EMAIL_TAKEN"`
- **THEN** la pantalla muestra "Ya existe un usuario con ese email" y la fila conserva sus datos anteriores

#### Scenario: Asignar contraseña (esperado)
- **WHEN** el administrador escribe una contraseña nueva de 10 caracteres para una cuenta y confirma
- **THEN** se envía `PUT /api/v1/users/{id}/password`, la pantalla muestra "Contraseña actualizada" y el campo se vacía
