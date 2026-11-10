# public-booking-api Specification

## Purpose
Endpoints HTTP públicos de la reserva online bajo `/api/v1/public/`, que funcionan sin sesión y se protegen con validación estricta, límite de pedidos por IP, un campo trampa y respuestas que no exponen datos de pacientes.

## Requirements

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

### Requirement: Validación estricta de la entrada pública

Los cuerpos públicos SHALL rechazar con 422 cualquiera de estos casos:

- un campo desconocido;
- un `starts_at` sin zona horaria;
- un documento, nombre, apellido, email o teléfono fuera de las reglas de `patient-data-rules`;
- un `token` vacío o de más de 128 caracteres;
- un texto más largo de lo permitido.

El 422 MUST tener la forma de siempre, sin repetir los valores enviados. El parámetro `date` MUST ser una fecha `AAAA-MM-DD`.

#### Scenario: Campo desconocido (error)
- **WHEN** el cuerpo de la reserva trae `{"active": false, ...}`
- **THEN** la respuesta es 422 y no se escribe nada

#### Scenario: Inicio sin zona (error)
- **WHEN** `starts_at` es `2026-11-10T10:00:00`
- **THEN** la respuesta es 422

#### Scenario: Email inválido sin eco (error)
- **WHEN** `email` es `no-es-email`
- **THEN** la respuesta es 422 y el cuerpo no contiene `no-es-email`

### Requirement: Rechazos de negocio con código y estado HTTP

Los rechazos públicos SHALL responder con el cuerpo uniforme `{"error": {"code", "message"}}` y estos estados:

| Código | Estado | Mensaje |
|---|---|---|
| `SLOT_TAKEN` | 409 | — |
| `SLOT_UNAVAILABLE` | 409 | — |
| `BOOKING_NOT_POSSIBLE` | 409 | "Verifique sus datos ingresados." |
| `CONFIRMATION_LINK_INVALID` | 410 | "El enlace no es válido o ya venció." |
| `PROFESSIONAL_NOT_FOUND` | 404 | — |
| `BOOKING_REJECTED` | 400 | — |
| `TOO_MANY_REQUESTS` | 429 | — |

`BOOKING_NOT_POSSIBLE` MUST ser idéntico, en código, mensaje y forma, para el nombre que no coincide, el paciente inactivo, el turno superpuesto y la carrera de DNI. Sus mensajes MUST NOT nombrar al paciente ni decir el motivo.

#### Scenario: Nombre que no coincide (error de negocio)
- **WHEN** el documento existe y el apellido escrito es otro
- **THEN** la respuesta es 409 `BOOKING_NOT_POSSIBLE` con el mensaje "Verifique sus datos ingresados." y sin datos de la ficha

#### Scenario: Paciente inactivo, misma respuesta (borde)
- **WHEN** el documento y el nombre coinciden con un paciente inactivo
- **THEN** la respuesta es exactamente la misma que la del nombre que no coincide

#### Scenario: Enlace vencido o usado (error)
- **WHEN** se confirma con un token vencido o ya usado
- **THEN** la respuesta es 410 `CONFIRMATION_LINK_INVALID` en los dos casos

### Requirement: Límite de pedidos por IP (P-5)

Cada endpoint público SHALL contar los pedidos por dirección IP del cliente en ventanas fijas guardadas en el Redis existente. Los topes son:

- lecturas (`professionals` y `slots`): 60 por minuto;
- reservas (`appointments`): 5 por hora;
- confirmaciones (`appointment-confirmations`): 10 por hora.

Al superar el tope, la respuesta MUST ser 429 con `error.code = "TOO_MANY_REQUESTS"` y el encabezado `Retry-After` en segundos, sin ejecutar el caso de uso. Los contadores de cada grupo son independientes. La IP MUST salir de la conexión, no de encabezados como `X-Forwarded-For`. Si Redis no responde, el pedido MUST seguir sin límite y registrar un aviso sin la IP ni datos del cuerpo. La clave en Redis MUST NOT contener el documento, el token ni otros datos del cuerpo.

#### Scenario: Sexta reserva en una hora (error)
- **WHEN** una misma IP hizo 5 `POST /api/v1/public/appointments` en la hora y manda el sexto
- **THEN** la respuesta es 429 con `TOO_MANY_REQUESTS` y `Retry-After`, y no se crea ningún turno

#### Scenario: Prueba de documentos y nombres (error)
- **WHEN** una IP intenta una sexta reserva en la hora con otro documento para ver si existe
- **THEN** la respuesta es 429 y no dice nada del documento

#### Scenario: Prueba de tokens (error)
- **WHEN** una IP manda una undécima confirmación en la hora
- **THEN** la respuesta es 429

#### Scenario: Grupos independientes (borde)
- **WHEN** una IP agotó las reservas
- **THEN** todavía puede pedir franjas y confirmar

#### Scenario: Encabezado reenviado ignorado (borde)
- **WHEN** una IP agotó su tope y manda `X-Forwarded-For` con otra dirección
- **THEN** sigue recibiendo 429

#### Scenario: Redis caído (borde)
- **WHEN** Redis no responde al contar un pedido
- **THEN** el pedido se atiende normalmente y queda un aviso en el log sin IP ni datos personales

### Requirement: Campo trampa contra robots (P-5)

El cuerpo de `appointments` SHALL traer el campo `website`, que la página pública deja oculto y vacío. Si llega con texto, la respuesta MUST ser 400 con `error.code = "BOOKING_REJECTED"`, sin consultar pacientes ni escribir nada. Ese pedido cuenta igual para el límite.

#### Scenario: Campo trampa completo (error)
- **WHEN** una reserva llega con `website = "http://spam"`
- **THEN** la respuesta es 400 `BOOKING_REJECTED` y no se crea paciente, turno ni email

#### Scenario: Campo trampa vacío (esperado)
- **WHEN** una reserva válida llega con `website = ""`
- **THEN** se procesa normalmente

### Requirement: Registro de accesos de las rutas públicas (DD-77, DD-107)

El registro de accesos SHALL anotar en las rutas públicas solo método, ruta y código, igual que en el resto de la API: nunca el cuerpo, el documento, el token ni la parte de consulta.

#### Scenario: Confirmación en el log (borde)
- **WHEN** se hace `POST /api/v1/public/appointment-confirmations` con un token
- **THEN** la línea del registro no contiene el token

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
