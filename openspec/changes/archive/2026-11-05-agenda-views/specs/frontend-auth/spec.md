# Spec Delta: frontend-auth

## MODIFIED Requirements

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
