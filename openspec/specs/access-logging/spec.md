# access-logging Specification

## Purpose
Evitar que el registro de accesos de la API guarde datos de pacientes que viajan en la dirección (la búsqueda `q`, DD-77), conservando el método, la ruta y el código de respuesta para diagnosticar.

## Requirements

### Requirement: Registro de accesos sin la parte de consulta

Cada línea del registro de accesos de la API SHALL incluir el método, la ruta y el código de respuesta, y MUST NOT incluir la parte de consulta de la dirección (todo lo que sigue a `?`), en desarrollo y en modo demo. La regla MUST aplicarse a cualquier ruta, no solo a la búsqueda de pacientes. El registro MUST NOT incluir el cuerpo de la solicitud ni el encabezado `Authorization`. Los mensajes de la aplicación siguen sin escribir datos de pacientes (DD-77).

#### Scenario: Búsqueda de pacientes (esperado)
- **WHEN** la recepcionista pide `GET /api/v1/patients?q=ruiz` y la API responde 200
- **THEN** la línea del registro de accesos contiene `GET`, `/api/v1/patients` y `200`, y no contiene `ruiz` ni `q=`

#### Scenario: Búsqueda por documento (borde)
- **WHEN** se pide `GET /api/v1/patients?q=40555666`
- **THEN** la línea del registro de accesos no contiene `40555666`

#### Scenario: Otra ruta con consulta (borde)
- **WHEN** se pide `GET /api/v1/appointments?professional_id=<id>&from=<instante>&to=<instante>`
- **THEN** la línea del registro de accesos contiene `/api/v1/appointments` y no contiene `professional_id=`

#### Scenario: Ruta sin consulta (esperado)
- **WHEN** se pide `GET /api/v1/health`
- **THEN** la línea del registro de accesos contiene `GET`, `/api/v1/health` y `200`

#### Scenario: Error con consulta (error)
- **WHEN** se pide sin token `GET /api/v1/patients?q=ruiz` y la API responde 401
- **THEN** la línea del registro de accesos contiene `401` y no contiene `ruiz`
