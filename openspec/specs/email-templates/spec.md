# email-templates Specification

## Purpose
Definir el contenido de los emails informativos de confirmación y de recordatorio de un turno (asunto, cuerpo, formato de fecha y hora en la zona del consultorio y datos del consultorio), de modo que el paciente sepa cuándo, con quién y dónde es su turno sin poder actuar desde el email (DD-06, RN-NO-01, RN-NO-02).

## Requirements

### Requirement: Email de confirmación (RN-NO-01, DD-06, P-6)

El email `confirmation` SHALL ser texto plano con:
- Asunto: `Turno confirmado: <fecha y hora> - <nombre del consultorio>`.
- Cuerpo, en este orden: saludo con el nombre del paciente (`Hola, <Nombre> <Apellido>:`); "Tu turno quedó agendado."; fecha y hora; profesional (nombre a mostrar de su ficha); nombre del consultorio; dirección; teléfono (solo si el consultorio tiene); la línea "Este email es informativo: para cambiar o cancelar el turno comunicate con el consultorio." (DD-06).

La fecha y hora MUST mostrarse en la zona horaria del consultorio (RN-GL-01) con el formato `<día de la semana> <día> de <mes> de <año>, <HH:MM> h` en castellano y minúsculas (por ejemplo `lunes 9 de noviembre de 2026, 10:00 h`). Los datos MUST ser los vigentes al momento del envío (ficha del paciente, ficha del profesional y configuración del consultorio), y la fecha MUST ser la del horario de la notificación. El email MUST NOT incluir documento, teléfono ni fecha de nacimiento del paciente, el motivo de una cancelación, enlaces ni datos de otros turnos o pacientes. El mismo texto se usa al agendar y al reprogramar: indica el horario vigente.

#### Scenario: Confirmación de un turno agendado (esperado)
- **WHEN** se arma la confirmación del turno de Juan Perez con la Dra. A el lunes 09/11/2026 a las 13:00 UTC, con el consultorio "Consultorio Demo", dirección "Av. Siempre Viva 742" y teléfono "011 4000-0000", en la zona `America/Argentina/Buenos_Aires`
- **THEN** el asunto es `Turno confirmado: lunes 9 de noviembre de 2026, 10:00 h - Consultorio Demo` y el cuerpo contiene, en orden, `Hola, Juan Perez:`, `Tu turno quedó agendado.`, `lunes 9 de noviembre de 2026, 10:00 h`, el nombre de la Dra. A, `Consultorio Demo`, `Av. Siempre Viva 742`, `011 4000-0000` y la línea informativa

#### Scenario: Consultorio sin teléfono (borde)
- **WHEN** el consultorio no tiene teléfono cargado
- **THEN** el cuerpo no tiene la línea de teléfono ni una etiqueta vacía

#### Scenario: Turno cerca de la medianoche (borde)
- **WHEN** el turno empieza el martes 10/11/2026 a las 02:30 UTC
- **THEN** la fecha del email es `lunes 9 de noviembre de 2026, 23:30 h` (zona del consultorio), no la del día UTC

#### Scenario: Paciente que cambió su nombre después de agendar (borde)
- **WHEN** se agendó a "Juan Perez" y antes del envío recepción corrigió la ficha a "Juan Pérez"
- **THEN** el email saluda a `Juan Pérez` (datos vigentes, DD-73)

#### Scenario: Nada de datos sensibles (error de negocio)
- **WHEN** se arma una confirmación de un paciente con documento, teléfono y fecha de nacimiento cargados
- **THEN** el asunto y el cuerpo no contienen ninguno de esos tres datos

### Requirement: Email de recordatorio (RN-NO-02, DD-06, P-6)

El email `reminder` SHALL tener los mismos datos y el mismo formato que la confirmación, con asunto `Recordatorio de turno: <fecha y hora> - <nombre del consultorio>` y la frase "Te recordamos tu turno." en lugar de "Tu turno quedó agendado.". MUST NOT decir "mañana" ni "en 24 horas" (el envío sale el día anterior a la hora configurada, IN-01, y puede salir tarde). En C-11 la plantilla queda disponible y probada; quien crea los recordatorios es C-12.

#### Scenario: Recordatorio (esperado)
- **WHEN** se arma el recordatorio del mismo turno del lunes 09/11/2026 10:00 h
- **THEN** el asunto es `Recordatorio de turno: lunes 9 de noviembre de 2026, 10:00 h - Consultorio Demo` y el cuerpo contiene `Te recordamos tu turno.` y la línea informativa

#### Scenario: Recordatorio sin palabras relativas (borde)
- **WHEN** se arma cualquier recordatorio
- **THEN** el asunto y el cuerpo no contienen "mañana" ni "24 horas"

#### Scenario: Tipo desconocido (error)
- **WHEN** se pide armar un email de un tipo que no es `confirmation` ni `reminder`
- **THEN** se rechaza con un error de programación y no se arma ningún email

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
