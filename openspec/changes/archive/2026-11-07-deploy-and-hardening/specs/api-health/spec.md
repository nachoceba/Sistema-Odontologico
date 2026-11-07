# Spec Delta

## MODIFIED Requirements

### Requirement: CORS limitado a los orígenes configurados

La API SHALL permitir solicitudes de navegador solo desde los orígenes de `CORS_ORIGINS`. Las respuestas de CORS MUST permitir solo los métodos que usa el frontend (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`) y solo los encabezados `Authorization` y `Content-Type`, y MUST NOT habilitar credenciales del navegador (cookies), porque la sesión viaja en el encabezado `Authorization`.

#### Scenario: Origen permitido
- **WHEN** se pide `GET /api/v1/health` con `Origin: http://localhost:5173` y ese origen está en `CORS_ORIGINS`
- **THEN** la respuesta incluye `Access-Control-Allow-Origin: http://localhost:5173`

#### Scenario: Origen no permitido (error)
- **WHEN** se pide `GET /api/v1/health` con `Origin: http://malicioso.example`
- **THEN** la respuesta no incluye el encabezado `Access-Control-Allow-Origin`

#### Scenario: Origen del modo demo (esperado)
- **WHEN** `CORS_ORIGINS = http://localhost:5173,http://localhost:8080` y se pide `GET /api/v1/health` con `Origin: http://localhost:8080`
- **THEN** la respuesta incluye `Access-Control-Allow-Origin: http://localhost:8080`

#### Scenario: Preflight con encabezados del frontend (esperado)
- **WHEN** se envía `OPTIONS /api/v1/patients` con `Origin: http://localhost:5173`, `Access-Control-Request-Method: PATCH` y `Access-Control-Request-Headers: authorization, content-type`
- **THEN** la respuesta es 200, permite `PATCH` y los encabezados `Authorization` y `Content-Type`, y no incluye `Access-Control-Allow-Credentials: true`

#### Scenario: Preflight con un encabezado no usado (borde)
- **WHEN** se envía el preflight con `Access-Control-Request-Headers: x-otro-encabezado` desde un origen permitido
- **THEN** la respuesta no autoriza ese encabezado

#### Scenario: Preflight desde un origen no permitido (error)
- **WHEN** se envía el preflight desde `Origin: http://malicioso.example`
- **THEN** la respuesta no incluye `Access-Control-Allow-Origin`
