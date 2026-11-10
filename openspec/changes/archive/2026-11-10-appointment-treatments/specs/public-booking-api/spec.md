# Spec Delta: public-booking-api

## MODIFIED Requirements

### Requirement: Endpoints públicos de reserva

La API SHALL exponer, sin exigir el encabezado `Authorization`, solo estos endpoints públicos:

- `GET /api/v1/public/professionals`: lista `[{id, display_name}]` de los profesionales ofrecidos.
- `GET /api/v1/public/professionals/{professional_id}/treatments`: lista `[{id, name}]` de los tratamientos activos que ofrece el profesional, ordenada por nombre (C-17). Un profesional no ofrecido responde 404 `PROFESSIONAL_NOT_FOUND`.
- `GET /api/v1/public/professionals/{professional_id}/slots?date=AAAA-MM-DD`: lista `[{starts_at, ends_at}]` de franjas reservables, en UTC. Un profesional no ofrecido responde 404 `PROFESSIONAL_NOT_FOUND`.
- `POST /api/v1/public/appointments` con cuerpo `{professional_id, treatment_id, starts_at, document_number, first_name, last_name, email, phone, website}`: responde 202 con `{starts_at, ends_at, professional_display_name, treatment_name, confirm_before}`. La respuesta es la misma para un DNI nuevo y para uno existente con nombre coincidente.
- `POST /api/v1/public/appointment-confirmations` con cuerpo `{token}`: responde 200 con `{starts_at, ends_at, professional_display_name, treatment_name}`. `treatment_name` es nulo solo si la reserva es anterior a C-17.

Ninguno MUST tener un `GET` con efectos. Los endpoints MUST ignorar un encabezado `Authorization` si llega, sin cambiar la respuesta. Nunca MUST devolver email, teléfono, documento, fecha de nacimiento ni nombre de un paciente. El endpoint de tratamientos MUST NOT devolver tratamientos inactivos, la lista de asignaciones de otros profesionales ni ningún dato además del identificador y el nombre.

#### Scenario: Reserva sin token (esperado)
- **WHEN** se hace `POST /api/v1/public/appointments` sin `Authorization` con datos válidos, un tratamiento que ofrece el profesional y una franja reservable
- **THEN** la respuesta es 202 con inicio, fin, nombre visible del profesional, nombre del tratamiento y `confirm_before`, sin datos del paciente

#### Scenario: Confirmación sin token de sesión (esperado)
- **WHEN** se hace `POST /api/v1/public/appointment-confirmations` con un token válido
- **THEN** la respuesta es 200 con inicio, fin, nombre visible del profesional y nombre del tratamiento

#### Scenario: Con un token de sesión cualquiera (borde)
- **WHEN** se llama a un endpoint público con `Authorization: Bearer basura`
- **THEN** la respuesta es la misma que sin encabezado, nunca 401

#### Scenario: Profesional no ofrecido en franjas (error)
- **WHEN** se piden franjas de un profesional inactivo
- **THEN** la respuesta es 404 con `error.code = "PROFESSIONAL_NOT_FOUND"`

#### Scenario: Tratamientos públicos sin token (esperado)
- **WHEN** se hace `GET /api/v1/public/professionals/{id}/treatments` sin `Authorization` para un profesional ofrecido
- **THEN** la respuesta es 200 con `[{id, name}]` solo de los tratamientos activos que ofrece

#### Scenario: Tratamientos de un profesional no ofrecido (error)
- **WHEN** se piden los tratamientos públicos de un profesional inactivo o inexistente
- **THEN** la respuesta es 404 con `error.code = "PROFESSIONAL_NOT_FOUND"`

#### Scenario: Reserva sin tratamiento (error)
- **WHEN** se hace `POST /api/v1/public/appointments` sin `treatment_id`
- **THEN** la respuesta es 422 sin repetir lo enviado y no se escribe nada

## ADDED Requirements

### Requirement: Tratamiento rechazado en la reserva pública (C-17)

Un `treatment_id` inexistente, inactivo o no ofrecido por el profesional SHALL responder 409 con `error.code = "TREATMENT_NOT_AVAILABLE"` y el mensaje "El tratamiento elegido ya no está disponible. Elija otro.", el mismo en los tres casos, sin crear ni vincular pacientes. El endpoint de tratamientos públicos MUST contar en el grupo de lecturas del límite de pedidos (60 por minuto por IP, junto a profesionales y franjas): al superarlo responde 429 `TOO_MANY_REQUESTS` con `Retry-After` sin ejecutar el caso de uso.

#### Scenario: Tratamiento no ofrecido (error de negocio)
- **WHEN** se reserva con el Dr. B un tratamiento que solo ofrece la Dra. A
- **THEN** la respuesta es 409 `TREATMENT_NOT_AVAILABLE` y no se crea ni el paciente ni el turno

#### Scenario: Misma respuesta para inexistente e inactivo (borde)
- **WHEN** se reserva una vez con un identificador inexistente y otra con un tratamiento inactivo
- **THEN** las dos respuestas tienen el mismo código, el mismo mensaje y la misma forma

#### Scenario: Lectura número 61 en un minuto (error)
- **WHEN** una IP hizo 60 lecturas públicas en el minuto (mezclando profesionales, tratamientos y franjas) y pide los tratamientos otra vez
- **THEN** la respuesta es 429 con `TOO_MANY_REQUESTS` y `Retry-After`

#### Scenario: Grupos independientes (borde)
- **WHEN** una IP agotó las lecturas
- **THEN** todavía puede reservar y confirmar dentro de sus propios topes
