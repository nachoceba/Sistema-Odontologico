# frontend-auth Specification

## Purpose
Que el personal inicie sesión desde el navegador, que ninguna pantalla salvo el login se muestre sin sesión, y que la sesión se cierre de forma clara al salir o cuando la API la rechaza, sin que ningún secreto del servidor llegue al frontend.

## Requirements

### Requirement: Pantalla de login

El frontend SHALL ofrecer en `/login` un formulario con email y contraseña que envía las credenciales a `POST /api/v1/auth/login`. Mientras espera, el botón MUST quedar deshabilitado. Si la API responde 401, la pantalla MUST mostrar "Email o contraseña incorrectos" (P-5, CONFIRMADA (2026-11-03)) sin borrar el email escrito; ante un error de red o un 5xx MUST mostrar "No se pudo conectar con el servidor". La contraseña MUST NOT guardarse en ningún almacenamiento del navegador.

#### Scenario: Login correcto (esperado)
- **WHEN** el usuario escribe credenciales válidas y envía el formulario
- **THEN** el frontend guarda el token y navega a `/agenda`

#### Scenario: Credenciales inválidas (error de negocio)
- **WHEN** la API responde 401 al login
- **THEN** la pantalla muestra "Email o contraseña incorrectos", conserva el email y queda en `/login`

#### Scenario: Servidor caído (error)
- **WHEN** la solicitud de login falla por error de red
- **THEN** la pantalla muestra "No se pudo conectar con el servidor"

#### Scenario: Envío doble mientras espera (borde)
- **WHEN** el usuario hace clic dos veces seguidas en "Ingresar"
- **THEN** se envía una sola solicitud de login

### Requirement: Rutas protegidas y redirección por rol (RN-AU-01)

Toda ruta del frontend salvo `/login` SHALL exigir sesión: sin token guardado, el frontend MUST redirigir a `/login`. Después de iniciar sesión, cada rol MUST ir a `/agenda` (P-7 de C-03, CONFIRMADA (2026-11-03); P-8 de C-09, CONFIRMADA (2026-11-04)), que muestra la agenda del día según la spec `frontend-agenda`; la página provisoria con el nombre y el rol deja de existir. Un usuario con sesión que entra a `/login` MUST ir a `/agenda`.

#### Scenario: Sin sesión a una ruta protegida (error)
- **WHEN** alguien sin token abre `/agenda`
- **THEN** el frontend lo lleva a `/login`

#### Scenario: Con sesión en la agenda (esperado)
- **WHEN** un odontólogo con sesión y ficha abre `/agenda`
- **THEN** ve su propia agenda del día de hoy, con su nombre y el rol odontólogo en la barra de navegación

#### Scenario: Con sesión abre el login (borde)
- **WHEN** un usuario con sesión abre `/login`
- **THEN** el frontend lo lleva a `/agenda`

#### Scenario: Ruta inexistente (borde)
- **WHEN** alguien abre una ruta que no existe
- **THEN** el frontend lo lleva a `/agenda` si tiene sesión o a `/login` si no la tiene

### Requirement: Token en cada llamada y fin de sesión

El frontend SHALL enviar el token guardado en `Authorization: Bearer <token>` en toda llamada a la API salvo el login y el chequeo de salud. El token MUST guardarse en `sessionStorage` (P-2, CONFIRMADA (2026-11-03)), nunca en `localStorage` ni en cookies creadas por el frontend. Si una llamada protegida responde 401, el frontend MUST borrar el token y volver a `/login` con el aviso "Tu sesión terminó. Volvé a ingresar". El botón "Salir" MUST borrar el token y volver a `/login` (P-11, CONFIRMADA (2026-11-03)). El frontend MUST NOT recibir ni usar `JWT_SECRET_KEY` ni ninguna variable secreta.

#### Scenario: Llamada con token (esperado)
- **WHEN** el frontend con sesión pide `GET /api/v1/auth/me`
- **THEN** la solicitud lleva `Authorization: Bearer <token guardado>`

#### Scenario: Sesión vencida durante el uso (error de negocio)
- **WHEN** una llamada protegida responde 401
- **THEN** el token se borra y el usuario vuelve a `/login` con el aviso "Tu sesión terminó. Volvé a ingresar"

#### Scenario: Salir (esperado)
- **WHEN** el usuario hace clic en "Salir"
- **THEN** el token se borra del navegador y el usuario queda en `/login`

#### Scenario: Recargar la página con sesión (borde)
- **WHEN** el usuario con sesión recarga la pantalla `/agenda` en la misma pestaña
- **THEN** sigue con sesión y no vuelve al login

#### Scenario: 403 no cierra la sesión (borde)
- **WHEN** una llamada protegida responde 403
- **THEN** el token se conserva y la pantalla muestra "No tenés permiso para esta acción"
