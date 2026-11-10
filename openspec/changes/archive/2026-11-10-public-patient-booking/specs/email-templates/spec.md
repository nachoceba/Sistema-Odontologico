# Spec Delta: email-templates

## ADDED Requirements

### Requirement: Email para confirmar la reserva online (DD-130, DD-131)

El email de verificación SHALL tener el asunto "Confirmá tu turno en <nombre del consultorio>". Su cuerpo de texto MUST llevar:

- el nombre del paciente, el profesional y la fecha y hora local del turno;
- el enlace `<PUBLIC_APP_URL>/turnos/confirmar#token=<token>`;
- la hora local límite para confirmar;
- la aclaración de que, si no confirma, el horario se libera;
- la aclaración de que, si no pidió el turno, puede ignorar el email;
- el nombre, la dirección y el teléfono del consultorio, como la confirmación.

Con `EMAIL_REDIRECT_TO` MUST aplicarse la misma línea de demostración que en los demás emails. El email MUST NOT incluir el documento.

#### Scenario: Contenido del email (esperado)
- **WHEN** se arma el email de una reserva de Lucía Díaz con la Dra. A el lunes 09/11 a las 10:30, que vence a las 13:00
- **THEN** el asunto es "Confirmá tu turno en <consultorio>" y el cuerpo trae paciente, profesional, "lunes 09/11/2026 10:30", el enlace con el token en el fragmento y "hasta las 13:00"

#### Scenario: Sin documento (borde)
- **WHEN** se arma cualquier email de verificación
- **THEN** el texto no contiene el documento del paciente
