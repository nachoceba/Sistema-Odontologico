# frontend-shell Specification

## Purpose
Proveer la aplicación web mínima (SPA) sobre la que se construyen las pantallas de login, pacientes y agenda, con la URL de la API como única configuración y una indicación visible de si la API responde.

## Requirements

### Requirement: URL de la API configurable

El frontend SHALL tomar la URL base de la API de `VITE_API_URL`. Si la variable falta o está vacía, el frontend MUST mostrar un mensaje de configuración incompleta en lugar de consultar una URL inventada.

#### Scenario: URL configurada (esperado)
- **WHEN** `VITE_API_URL = http://localhost:8000/api/v1`
- **THEN** el frontend consulta `http://localhost:8000/api/v1/health`

#### Scenario: URL con barra final (borde)
- **WHEN** `VITE_API_URL = http://localhost:8000/api/v1/`
- **THEN** el frontend consulta `http://localhost:8000/api/v1/health`, sin doble barra

#### Scenario: Falta la URL (error)
- **WHEN** `VITE_API_URL` no está definida
- **THEN** la pantalla muestra "Falta configurar la URL de la API" y no se hace ninguna solicitud

### Requirement: Estado de la API visible

La pantalla de login (`/login`, la única pública del frontend) SHALL mostrar el nombre del sistema ("Sistema Odontológico") y el estado de la API: "Verificando…" mientras espera, "API disponible" si `/health` responde 200 con `status = ok`, y "API no disponible" ante cualquier otra respuesta o un error de red. La consulta a `/health` MUST NOT llevar el token de sesión.

#### Scenario: API disponible (esperado)
- **WHEN** `/health` responde 200 con `{"status": "ok"}` y el usuario está en `/login`
- **THEN** la pantalla muestra "Sistema Odontológico" y "API disponible"

#### Scenario: Mientras espera (borde)
- **WHEN** la respuesta de `/health` todavía no llegó
- **THEN** la pantalla de login muestra "Verificando…"

#### Scenario: API caída (error)
- **WHEN** la solicitud a `/health` falla por error de red
- **THEN** la pantalla de login muestra "API no disponible"

#### Scenario: Respuesta inesperada (error)
- **WHEN** `/health` responde 500
- **THEN** la pantalla de login muestra "API no disponible"

#### Scenario: Chequeo de salud sin token (borde)
- **WHEN** hay un token guardado y el frontend consulta `/health`
- **THEN** la solicitud no lleva el encabezado `Authorization`
