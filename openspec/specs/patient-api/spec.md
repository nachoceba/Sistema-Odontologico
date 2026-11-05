# patient-api Specification

## Purpose
Exponer la gestión de pacientes en `/api/v1/patients` con sesión obligatoria, chequeo de rol por endpoint, validación de entrada sin eco de lo enviado y un formato de respuesta estable que usan la pantalla `/pacientes` y el selector de paciente de C-10.

## Requirements

### Requirement: Endpoints de pacientes

La API SHALL ofrecer, bajo `/api/v1/patients`:
- `GET /patients?q=<texto>&include_inactive=<bool>` → 200 `{"items": [Paciente...], "truncated": bool}` (máximo 50 ítems, `include_inactive` falso por defecto).
- `GET /patients/{id}` → 200 Paciente.
- `POST /patients` → 201 Paciente.
- `PATCH /patients/{id}` → 200 Paciente; un campo ausente no cambia; `phone` o `birth_date` en `null` lo borran.
- `POST /patients/{id}/deactivate` → 200 `{"patient": Paciente, "upcoming_appointments": [Turno...]}`.
- `POST /patients/{id}/reactivate` → 200 Paciente.
- `DELETE /patients/{id}` → 204 (P-6 confirmada).

Un Paciente MUST tener exactamente `id`, `first_name`, `last_name`, `document_number` (normalizado), `email`, `phone` (o `null`), `birth_date` (`AAAA-MM-DD` o `null`) y `active`. Cada Turno de `upcoming_appointments` MUST tener `id`, `professional_id`, `starts_at` y `ends_at` (instantes en UTC, como en `appointment-api`) y `status`.

#### Scenario: Alta y lectura (esperado)
- **CUANDO** la recepcionista hace `POST /api/v1/patients` con `{"first_name": "Laura", "last_name": "Ruiz", "document_number": "40.222.333", "email": "laura@example.com"}`
- **ENTONCES** la respuesta es 201 con `document_number = "40222333"`, `phone = null`, `birth_date = null`, `active = true`, y `GET /api/v1/patients/{id}` devuelve lo mismo

#### Scenario: Búsqueda (esperado)
- **CUANDO** se pide `GET /api/v1/patients?q=perez`
- **ENTONCES** la respuesta es 200 con Juan Pérez en `items` y `truncated = false`

#### Scenario: Desactivar con turnos futuros (esperado)
- **DADO** Juan Pérez con un turno `scheduled` mañana
- **CUANDO** la recepcionista hace `POST /api/v1/patients/{Juan}/deactivate`
- **ENTONCES** la respuesta es 200 con `patient.active = false` y ese turno en `upcoming_appointments`

#### Scenario: Borrar un dato opcional con null (borde)
- **CUANDO** se hace `PATCH` con `{"phone": null}` y después `PATCH` con `{"email": "nuevo@example.com"}`
- **ENTONCES** el primero borra el teléfono y el segundo cambia el email sin volver a tocar el teléfono

#### Scenario: Paciente inexistente (error de negocio)
- **CUANDO** se pide `GET /api/v1/patients/no-existe`
- **ENTONCES** la respuesta es 404 con `error.code = "PATIENT_NOT_FOUND"`

#### Scenario: Documento repetido (error de negocio)
- **CUANDO** se da de alta otra persona con el documento de Juan Pérez
- **ENTONCES** la respuesta es 409 con `error.code = "DOCUMENT_TAKEN"` y un mensaje que no incluye el documento ni el nombre de Juan

### Requirement: Validación de entrada sin eco (RN-PR-03, error-model)

Los cuerpos y parámetros SHALL validarse antes del caso de uso. Faltar nombre, apellido, documento o email en el alta, un documento, email o teléfono con formato inválido según `patient-data-rules`, textos fuera de largo, un `q` de más de 100 caracteres, campos desconocidos o una fecha que no sea un texto `AAAA-MM-DD` MUST responder 422 sin repetir el valor enviado. Una fecha numérica (por ejemplo `0`) MUST rechazarse con 422 y no interpretarse como fecha. Una fecha de nacimiento bien escrita pero futura MUST responder 400 `INVALID_PATIENT_DATA`. Enviar `null` en un campo obligatorio de `PATCH` MUST responder 422.

#### Scenario: Falta el email (error de negocio)
- **CUANDO** se hace `POST /api/v1/patients` sin `email`
- **ENTONCES** la respuesta es 422 y el cuerpo no contiene los otros datos enviados

#### Scenario: Documento inválido sin eco (error de negocio)
- **CUANDO** se envía `document_number = "30111222/1"`
- **ENTONCES** la respuesta es 422 y el cuerpo no contiene `30111222/1`

#### Scenario: Fecha como número (borde)
- **CUANDO** se envía `birth_date = 0`
- **ENTONCES** la respuesta es 422

#### Scenario: Fecha futura (error de negocio)
- **CUANDO** se envía `birth_date = "2999-01-01"`
- **ENTONCES** la respuesta es 400 con `error.code = "INVALID_PATIENT_DATA"`

#### Scenario: Email nulo en la edición (borde)
- **CUANDO** se hace `PATCH` con `{"email": null}`
- **ENTONCES** la respuesta es 422 y la ficha no cambia

### Requirement: Permisos por rol en cada endpoint (regla dura 4, matriz RBAC, P-4 y P-6 confirmadas)

Todo endpoint de pacientes SHALL exigir sesión: sin token MUST responder 401 antes de cualquier chequeo de rol. Las lecturas (`GET`) MUST permitirse a administración, recepción y odontólogo (con o sin ficha de profesional). Alta, edición, desactivar y reactivar MUST permitirse solo a administración y recepción; `DELETE` solo a administración. Un rol no permitido MUST recibir 403 `FORBIDDEN` aunque el cuerpo sea inválido (403 antes que 422) y MUST NOT cambiar nada. Cada endpoint MUST tener un test de permisos que pruebe administrador, recepción, odontólogo y falta de token.

#### Scenario: Odontólogo lee (esperado)
- **CUANDO** la Dra. A pide `GET /api/v1/patients?q=gomez` y `GET /api/v1/patients/{Ana}`
- **ENTONCES** ambas respuestas son 200

#### Scenario: Odontólogo escribe (error de negocio)
- **CUANDO** la Dra. A hace `POST`, `PATCH`, `deactivate`, `reactivate` o `DELETE` sobre pacientes
- **ENTONCES** cada respuesta es 403 `FORBIDDEN` y ningún paciente cambió

#### Scenario: Recepción borra (error de negocio)
- **CUANDO** la recepcionista hace `DELETE /api/v1/patients/{id}` de un paciente sin turnos
- **ENTONCES** la respuesta es 403 y el paciente sigue existiendo

#### Scenario: Sin token (borde)
- **CUANDO** se pide cualquier endpoint de pacientes sin token
- **ENTONCES** la respuesta es 401 con `WWW-Authenticate: Bearer`

#### Scenario: Rol no permitido con cuerpo inválido (borde)
- **CUANDO** la Dra. A hace `POST /api/v1/patients` con un cuerpo vacío
- **ENTONCES** la respuesta es 403 y no 422

### Requirement: Datos del paciente fuera de mensajes y registros (RN-PR-02, P-10 confirmada)

Ningún mensaje de error de pacientes SHALL incluir nombre, documento, email, teléfono ni fecha de nacimiento de un paciente. La aplicación MUST NOT escribir datos de pacientes en sus registros propios (logs) al rechazar un pedido por una regla de negocio, incluido el rechazo de unicidad que llega de la base.

#### Scenario: Documento repetido detectado por la base (borde)
- **CUANDO** dos altas simultáneas con documento `40222333` hacen que la base rechace una
- **ENTONCES** esa respuesta es 409 `DOCUMENT_TAKEN`, su cuerpo no contiene `40222333` y la aplicación no registró el detalle del rechazo de la base

#### Scenario: Error inesperado (error)
- **CUANDO** el alta falla por un error interno
- **ENTONCES** la respuesta es 500 y su cuerpo no contiene ningún dato enviado
