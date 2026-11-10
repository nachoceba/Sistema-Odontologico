# Spec Delta: treatment-api

## Purpose

Exponer por la API interna, con sesión y chequeo de rol, el catálogo de tratamientos y los tratamientos que ofrece cada profesional, con su matriz de permisos y sus códigos de error.

## ADDED Requirements

### Requirement: Endpoints del catálogo y de la asignación

La API SHALL exponer, todos con JWT:

- `GET /api/v1/treatments`: lista `[{id, name, active}]` de todo el catálogo, ordenada por nombre.
- `POST /api/v1/treatments` con cuerpo `{name}`: crea un tratamiento activo y responde 201 con `{id, name, active}`.
- `PATCH /api/v1/treatments/{treatment_id}` con cuerpo `{name?, active?}`: cambia el nombre, el estado o los dos, y responde 200 con el tratamiento. Un campo ausente no cambia.
- `GET /api/v1/professionals/{professional_id}/treatments`: lista `[{id, name, active}]` de los tratamientos asignados al profesional, activos e inactivos, ordenada por nombre.
- `PUT /api/v1/professionals/{professional_id}/treatments` con cuerpo `{treatment_ids: [...]}`: reemplaza la asignación y responde 200 con la lista nueva.

Los cuerpos MUST rechazar campos desconocidos con 422. El nombre MUST validarse como en `treatment-management` y el 422 MUST NOT repetir lo enviado. `treatment_ids` MUST tener como mucho 100 elementos.

#### Scenario: Listar el catálogo (esperado)
- **WHEN** la recepcionista pide `GET /api/v1/treatments`
- **THEN** recibe todos los tratamientos con su estado, ordenados por nombre

#### Scenario: Crear un tratamiento (esperado)
- **WHEN** el administrador hace `POST /api/v1/treatments` con `{"name": "Tratamiento de conducto"}`
- **THEN** la respuesta es 201 con el tratamiento activo

#### Scenario: Desactivar (esperado)
- **WHEN** el administrador hace `PATCH /api/v1/treatments/{id}` con `{"active": false}`
- **THEN** la respuesta es 200 con `active = false` y el nombre sin cambios

#### Scenario: Campo desconocido (error)
- **WHEN** se manda `POST /api/v1/treatments` con `{"name": "X", "duration": 60}`
- **THEN** la respuesta es 422 y no se crea nada

#### Scenario: Reemplazar la asignación (esperado)
- **WHEN** el administrador hace `PUT /api/v1/professionals/{id}/treatments` con dos identificadores existentes
- **THEN** la respuesta es 200 con esos dos tratamientos

### Requirement: Rechazos del catálogo con código y estado HTTP

Los rechazos SHALL responder con el cuerpo uniforme de `error-model`: 404 `TREATMENT_NOT_FOUND` (tratamiento inexistente en `PATCH` o en la lista de `PUT`), 404 `PROFESSIONAL_NOT_FOUND`, 409 `TREATMENT_NAME_TAKEN` (nombre repetido) y 409 `TREATMENT_NOT_AVAILABLE` (al agendar, ver `appointment-api`). Los mensajes MUST estar en castellano.

#### Scenario: Nombre repetido (error de negocio)
- **WHEN** el administrador crea "limpieza dental" y ya existe "Limpieza dental"
- **THEN** la respuesta es 409 con `error.code = "TREATMENT_NAME_TAKEN"`

#### Scenario: Editar un tratamiento inexistente (error)
- **WHEN** el administrador hace `PATCH` sobre un identificador que no existe
- **THEN** la respuesta es 404 con `error.code = "TREATMENT_NOT_FOUND"`

### Requirement: Permisos por endpoint (matriz RBAC)

Las lecturas `GET /api/v1/treatments` y `GET /api/v1/professionals/{professional_id}/treatments` SHALL permitirse a los tres roles. El odontólogo MUST leer solo los tratamientos de su propio profesional (RN-AU-04, DD-53) y recibe 403 con otro. `POST /api/v1/treatments`, `PATCH /api/v1/treatments/{treatment_id}` y `PUT /api/v1/professionals/{professional_id}/treatments` MUST exigir el rol `admin`: otro rol recibe 403 `FORBIDDEN` antes de validar el cuerpo. Cada ruta MUST figurar en la matriz única de permisos con su test.

#### Scenario: Recepción no crea tratamientos (error de negocio)
- **WHEN** la recepcionista hace `POST /api/v1/treatments`
- **THEN** la respuesta es 403 con `error.code = "FORBIDDEN"`

#### Scenario: Odontólogo lee los suyos (esperado)
- **WHEN** el odontólogo de la Dra. A pide los tratamientos de la Dra. A
- **THEN** la respuesta es 200

#### Scenario: Odontólogo lee los de otro (error de negocio)
- **WHEN** el odontólogo de la Dra. A pide los tratamientos del Dr. B
- **THEN** la respuesta es 403 con `error.code = "FORBIDDEN"`

#### Scenario: Sin token (error)
- **WHEN** se pide cualquiera de las cinco rutas sin `Authorization`
- **THEN** la respuesta es 401 con `error.code = "NOT_AUTHENTICATED"`
