# Spec Delta: email-templates

## MODIFIED Requirements

### Requirement: Email de confirmación (RN-NO-01, DD-06, P-6)

El email `confirmation` SHALL ser texto plano con:
- Asunto: `Turno confirmado: <fecha y hora> - <nombre del consultorio>`.
- Cuerpo, en este orden: saludo con el nombre del paciente (`Hola, <Nombre> <Apellido>:`); "Tu turno quedó agendado."; fecha y hora; profesional (nombre a mostrar de su ficha); tratamiento (`Tratamiento: <nombre>`, solo si el turno tiene uno, C-17); nombre del consultorio; dirección; teléfono (solo si el consultorio tiene); la línea "Este email es informativo: para cambiar o cancelar el turno comunicate con el consultorio." (DD-06).

La fecha y hora MUST mostrarse en la zona horaria del consultorio (RN-GL-01) con el formato `<día de la semana> <día> de <mes> de <año>, <HH:MM> h` en castellano y minúsculas (por ejemplo `lunes 9 de noviembre de 2026, 10:00 h`). Los datos MUST ser los vigentes al momento del envío (ficha del paciente, ficha del profesional, nombre del tratamiento y configuración del consultorio), y la fecha MUST ser la del horario de la notificación. El email MUST NOT incluir documento, teléfono ni fecha de nacimiento del paciente, el motivo de una cancelación, enlaces ni datos de otros turnos o pacientes. El mismo texto se usa al agendar y al reprogramar: indica el horario vigente.

#### Scenario: Confirmación de un turno agendado (esperado)
- **WHEN** se arma la confirmación del turno de Juan Perez con la Dra. A el lunes 09/11/2026 a las 13:00 UTC, con el tratamiento "Limpieza dental", el consultorio "Consultorio Demo", dirección "Av. Siempre Viva 742" y teléfono "011 4000-0000", en la zona `America/Argentina/Buenos_Aires`
- **THEN** el asunto es `Turno confirmado: lunes 9 de noviembre de 2026, 10:00 h - Consultorio Demo` y el cuerpo contiene, en orden, `Hola, Juan Perez:`, `Tu turno quedó agendado.`, `lunes 9 de noviembre de 2026, 10:00 h`, el nombre de la Dra. A, `Tratamiento: Limpieza dental`, `Consultorio Demo`, `Av. Siempre Viva 742`, `011 4000-0000` y la línea informativa

#### Scenario: Turno sin tratamiento (borde)
- **WHEN** se arma la confirmación de un turno anterior a C-17, sin tratamiento
- **THEN** el cuerpo no tiene la línea de tratamiento ni una etiqueta vacía

#### Scenario: Tratamiento renombrado antes del envío (borde)
- **WHEN** se agendó con "Limpieza" y antes del envío el administrador lo renombró a "Limpieza dental"
- **THEN** el email dice `Tratamiento: Limpieza dental`

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

El email `reminder` SHALL tener los mismos datos y el mismo formato que la confirmación, incluida la línea de tratamiento cuando el turno tiene uno (C-17), con asunto `Recordatorio de turno: <fecha y hora> - <nombre del consultorio>` y la frase "Te recordamos tu turno." en lugar de "Tu turno quedó agendado.". MUST NOT decir "mañana" ni "en 24 horas" (el envío sale el día anterior a la hora configurada, IN-01, y puede salir tarde). En C-11 la plantilla queda disponible y probada; quien crea los recordatorios es C-12.

#### Scenario: Recordatorio (esperado)
- **WHEN** se arma el recordatorio del mismo turno del lunes 09/11/2026 10:00 h, con el tratamiento "Limpieza dental"
- **THEN** el asunto es `Recordatorio de turno: lunes 9 de noviembre de 2026, 10:00 h - Consultorio Demo` y el cuerpo contiene `Te recordamos tu turno.`, `Tratamiento: Limpieza dental` y la línea informativa

#### Scenario: Recordatorio sin palabras relativas (borde)
- **WHEN** se arma cualquier recordatorio
- **THEN** el asunto y el cuerpo no contienen "mañana" ni "24 horas"

#### Scenario: Tipo desconocido (error)
- **WHEN** se pide armar un email de un tipo que no es `confirmation` ni `reminder`
- **THEN** se rechaza con un error de programación y no se arma ningún email

### Requirement: Email para confirmar la reserva online (DD-130, DD-131)

El email de verificación SHALL tener el asunto "Confirmá tu turno en <nombre del consultorio>". Su cuerpo de texto MUST llevar:

- el nombre del paciente, el profesional, el tratamiento (`Tratamiento: <nombre>`, solo si la reserva tiene uno, C-17) y la fecha y hora local del turno;
- el enlace `<PUBLIC_APP_URL>/turnos/confirmar#token=<token>`;
- la hora local límite para confirmar;
- la aclaración de que, si no confirma, el horario se libera;
- la aclaración de que, si no pidió el turno, puede ignorar el email;
- el nombre, la dirección y el teléfono del consultorio, como la confirmación.

Con `EMAIL_REDIRECT_TO` MUST aplicarse la misma línea de demostración que en los demás emails. El email MUST NOT incluir el documento.

#### Scenario: Contenido del email (esperado)
- **WHEN** se arma el email de una reserva de Lucía Díaz con la Dra. A el lunes 09/11 a las 10:30, con el tratamiento "Consulta", que vence a las 13:00
- **THEN** el asunto es "Confirmá tu turno en <consultorio>" y el cuerpo trae paciente, profesional, "Tratamiento: Consulta", "lunes 09/11/2026 10:30", el enlace con el token en el fragmento y "hasta las 13:00"

#### Scenario: Sin documento (borde)
- **WHEN** se arma cualquier email de verificación
- **THEN** el texto no contiene el documento del paciente

### Requirement: Email de cancelación por falta de confirmación (DD-140)

El aviso `booking_expired` SHALL ser texto plano, en el mismo estilo que la confirmación y el recordatorio de C-11, con el asunto "Tu turno en <nombre del consultorio> se canceló por falta de confirmación". El cuerpo MUST llevar:

- el nombre del paciente;
- el profesional, el tratamiento (`Tratamiento: <nombre>`, solo si la reserva tenía uno, C-17) y la fecha y hora del turno en la zona del consultorio;
- la frase "Su turno se canceló porque no fue confirmado a tiempo con el enlace que le enviamos.";
- la indicación "Si todavía lo necesita, puede volver a reservar en <PUBLIC_APP_URL>/turnos.";
- el nombre, la dirección y el teléfono del consultorio.

MUST NOT incluir el documento, el motivo de consulta ni datos de otras personas. Con `EMAIL_REDIRECT_TO` MUST aplicarse la misma línea de demostración que en los demás emails.

#### Scenario: Contenido del aviso (esperado)
- **WHEN** se arma el aviso de Lucía Díaz con la Dra. A el lunes 09/11/2026 a las 10:30 (hora del consultorio), con el tratamiento "Limpieza dental"
- **THEN** el asunto dice que el turno se canceló por falta de confirmación y el cuerpo trae "Dra. A", "Tratamiento: Limpieza dental", "lunes 09/11/2026 10:30", la frase de cancelación y el enlace a `/turnos`

#### Scenario: Reserva sin tratamiento (borde)
- **WHEN** se arma el aviso de una reserva anterior a C-17, sin tratamiento
- **THEN** el cuerpo no tiene la línea de tratamiento

#### Scenario: Sin datos ajenos (borde)
- **WHEN** se arma cualquier aviso de vencimiento
- **THEN** el texto no contiene el documento ni datos de otro paciente

#### Scenario: Hora local y no UTC (borde)
- **WHEN** el turno empieza a las 13:30 UTC y el consultorio está en `America/Argentina/Buenos_Aires`
- **THEN** el email dice 10:30
