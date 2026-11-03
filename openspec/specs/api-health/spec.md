# api-health Specification

## Purpose
Exponer la API REST base bajo `/api/v1` con un endpoint de salud que permite a Docker y al frontend saber si la API está viva, y limitar el acceso desde navegadores a los orígenes configurados.

## Requirements

### Requirement: Endpoint de salud

La API SHALL responder `GET /api/v1/health` con estado 200 y el cuerpo JSON `{"status": "ok"}` mientras el proceso esté en marcha, sin consultar la base de datos ni Redis. La respuesta MUST NOT incluir versiones, configuración, nombres de host ni ningún dato de pacientes. El endpoint MUST NOT exigir autenticación.

#### Scenario: API viva (esperado)
- **WHEN** se pide `GET /api/v1/health` sin encabezado de autorización
- **THEN** la respuesta es 200 con cuerpo exactamente `{"status": "ok"}`

#### Scenario: Responde aunque la base no esté disponible (borde)
- **WHEN** la base de datos está caída y se pide `GET /api/v1/health`
- **THEN** la respuesta sigue siendo 200 con `{"status": "ok"}`

#### Scenario: Método no permitido (error)
- **WHEN** se pide `POST /api/v1/health`
- **THEN** la respuesta es 405

#### Scenario: Ruta fuera del prefijo versionado (error)
- **WHEN** se pide `GET /health`
- **THEN** la respuesta es 404

### Requirement: CORS limitado a los orígenes configurados

La API SHALL permitir solicitudes de navegador solo desde los orígenes de `CORS_ORIGINS`.

#### Scenario: Origen permitido
- **WHEN** se pide `GET /api/v1/health` con `Origin: http://localhost:5173` y ese origen está en `CORS_ORIGINS`
- **THEN** la respuesta incluye `Access-Control-Allow-Origin: http://localhost:5173`

#### Scenario: Origen no permitido (error)
- **WHEN** se pide `GET /api/v1/health` con `Origin: http://malicioso.example`
- **THEN** la respuesta no incluye el encabezado `Access-Control-Allow-Origin`

### Requirement: Documentación OpenAPI

La API SHALL publicar su esquema OpenAPI y MUST incluir en él la ruta `/api/v1/health`.

#### Scenario: El esquema lista el endpoint de salud
- **WHEN** se pide el esquema OpenAPI de la API
- **THEN** el esquema contiene la operación `GET /api/v1/health`
