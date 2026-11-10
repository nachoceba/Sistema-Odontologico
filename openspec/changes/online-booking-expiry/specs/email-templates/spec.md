# Spec Delta: email-templates

## ADDED Requirements

### Requirement: Email de cancelación por falta de confirmación (DD-140)

El aviso `booking_expired` SHALL ser texto plano, en el mismo estilo que la confirmación y el recordatorio de C-11, con el asunto "Tu turno en <nombre del consultorio> se canceló por falta de confirmación". El cuerpo MUST llevar:

- el nombre del paciente;
- el profesional, y la fecha y hora del turno en la zona del consultorio;
- la frase "Su turno se canceló porque no fue confirmado a tiempo con el enlace que le enviamos.";
- la indicación "Si todavía lo necesita, puede volver a reservar en <PUBLIC_APP_URL>/turnos.";
- el nombre, la dirección y el teléfono del consultorio.

MUST NOT incluir el documento, el motivo de consulta ni ningún dato de tratamiento ni de otras personas. Con `EMAIL_REDIRECT_TO` MUST aplicarse la misma línea de demostración que en los demás emails.

#### Scenario: Contenido del aviso (esperado)
- **WHEN** se arma el aviso de Lucía Díaz con la Dra. A el lunes 09/11/2026 a las 10:30 (hora del consultorio)
- **THEN** el asunto dice que el turno se canceló por falta de confirmación y el cuerpo trae "Dra. A", "lunes 09/11/2026 10:30", la frase de cancelación y el enlace a `/turnos`

#### Scenario: Sin datos ajenos (borde)
- **WHEN** se arma cualquier aviso de vencimiento
- **THEN** el texto no contiene el documento ni datos de otro paciente

#### Scenario: Hora local y no UTC (borde)
- **WHEN** el turno empieza a las 13:30 UTC y el consultorio está en `America/Argentina/Buenos_Aires`
- **THEN** el email dice 10:30
