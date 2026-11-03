# Spec Delta

## MODIFIED Requirements

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
