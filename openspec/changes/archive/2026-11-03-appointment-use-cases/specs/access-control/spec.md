# Spec Delta: access-control

## MODIFIED Requirements

### Requirement: Un odontólogo solo accede a lo propio (RN-AU-04)

El sistema SHALL ofrecer una regla de alcance que decide si una cuenta puede leer los turnos u horarios de un profesional dado: el administrador y la recepción pueden con cualquier profesional; un odontólogo solo con el profesional asociado a su cuenta. Un odontólogo sin profesional asociado MUST NOT acceder a ningún profesional (P-12, CONFIRMADA (2026-11-03)). Cuando la regla niega el acceso, la ruta MUST responder 403 con `error.code = "FORBIDDEN"` (P-13, CONFIRMADA (2026-11-03)). Desde C-08, la regla MUST aplicarse en los endpoints reales de turnos y franjas (`appointment-api`), tanto cuando el profesional llega en la ruta o en la consulta como cuando sale del turno pedido, y MUST probarse de punta a punta contra esos endpoints con los usuarios del seed (DD-53). Las rutas de horarios que aplican esta regla llegan en C-07.

#### Scenario: Odontólogo con su propio profesional (esperado)
- **WHEN** un odontólogo pide los turnos de su propio profesional
- **THEN** la regla permite el acceso

#### Scenario: Odontólogo con otro profesional (error de negocio)
- **WHEN** un odontólogo pide los turnos del otro profesional del seed
- **THEN** la regla niega el acceso y la ruta responde 403 con `error.code = "FORBIDDEN"`

#### Scenario: Recepción y administración con cualquier profesional (esperado)
- **WHEN** la recepcionista y el administrador piden los turnos de cualquiera de los dos profesionales
- **THEN** la regla permite el acceso a ambos

#### Scenario: Odontólogo sin ficha de profesional (borde)
- **WHEN** una cuenta con rol `dentist` que no tiene fila en `professionals` pide los turnos de cualquier profesional
- **THEN** la regla niega el acceso

#### Scenario: Identificador de profesional mal formado (borde)
- **WHEN** un odontólogo pide los turnos de un profesional con un identificador que no es un UUID válido
- **THEN** la regla niega el acceso sin error interno

#### Scenario: De punta a punta contra el endpoint real (esperado)
- **WHEN** la Dra. A del seed, con su token, pide `GET /api/v1/appointments/{id}` de un turno del Dr. B y `GET /api/v1/appointments?professional_id=<Dr. B>`
- **THEN** ambos pedidos responden 403 con `error.code = "FORBIDDEN"` y no devuelven ningún dato del turno

#### Scenario: El profesional sale del turno, no del pedido (borde)
- **WHEN** la Dra. A pide marcar atención de un turno del Dr. B usando el identificador del turno, sin mandar ningún profesional
- **THEN** la regla se aplica sobre el profesional del turno y la respuesta es 403
