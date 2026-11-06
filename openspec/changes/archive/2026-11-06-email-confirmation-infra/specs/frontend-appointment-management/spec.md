# Spec Delta

## MODIFIED Requirements

### Requirement: Agendar desde una franja libre (US-007, Flujo 2, RN-TU-01 a RN-TU-04, RN-TU-12)

"Agendar" en una franja libre SHALL abrir un panel con la fecha y la hora local de la franja (`Lun 09/11 10:00–10:30`) y el nombre del profesional, donde se elige o se crea el paciente. El botón "Agendar turno" MUST estar habilitado solo con un paciente elegido y MUST enviar un único `POST /api/v1/appointments` con el paciente, el profesional y el inicio de la franja tal como lo devolvió el servidor; mientras espera MUST quedar deshabilitado (un doble clic envía un solo pedido). Con 201, el panel MUST cerrarse, mostrarse "Turno agendado: <Apellido, Nombre>, <día> <HH:MM>. Se enviará la confirmación por email al paciente." y la agenda MUST volver a pedirse, con la franja ahora "Ocupado". Con un rechazo, el panel MUST quedar abierto con el mensaje del código (requirement "Mensajes de error por código"), el paciente elegido MUST conservarse y la agenda MUST volver a pedirse detrás. El aviso de éxito MUST NOT decir que el email ya se envió ni mostrar la dirección del paciente: el envío es posterior y lo hace el servidor (C-11, P-8).

#### Scenario: Agendar en una franja libre (esperado)
- **WHEN** la recepcionista elige "Agendar" en la franja de las 10:00 del lunes 09/11 de la Dra. A, busca y elige a Juan Perez y aprieta "Agendar turno"
- **THEN** se envía `POST /api/v1/appointments` con Juan Perez, la Dra. A y el inicio de esa franja, se ve "Turno agendado: Perez, Juan, Lun 09/11 10:00. Se enviará la confirmación por email al paciente." y la franja de las 10:00 pasa a "Ocupado" con "10:00–10:30 Perez, Juan"

#### Scenario: Otra recepcionista ocupó el horario (error de negocio)
- **WHEN** la franja de las 10:00 se ve "Libre" pero otra recepcionista acaba de agendar ahí, y se aprieta "Agendar turno"
- **THEN** la API responde 409 `SLOT_TAKEN`, el panel muestra "Ese horario se acaba de ocupar. Elegí otro horario" y la franja de las 10:00 pasa a "Ocupado" al volver a pedir la agenda

#### Scenario: Franja libre sin anticipación suficiente (error de negocio)
- **WHEN** faltan 2 horas para una franja libre, el consultorio pide 6 horas de anticipación y se intenta agendar
- **THEN** la API responde 400 `INSUFFICIENT_NOTICE` y el panel muestra "Ese horario ya pasó o no respeta la anticipación mínima del consultorio"

#### Scenario: Paciente con otro turno a esa hora (error de negocio)
- **WHEN** Juan Perez ya tiene un turno a las 10:00 con el Dr. B y se lo intenta agendar a las 10:00 con la Dra. A
- **THEN** el panel muestra "El paciente ya tiene otro turno en ese horario" sin ningún dato del otro turno ni de otro paciente

#### Scenario: Sin paciente elegido (borde)
- **WHEN** se abre el panel de agendar y todavía no se eligió paciente
- **THEN** "Agendar turno" está deshabilitado y no se envía ningún pedido

#### Scenario: Doble clic (borde)
- **WHEN** se aprieta dos veces seguidas "Agendar turno"
- **THEN** se envía un solo `POST /api/v1/appointments`

#### Scenario: Cerrar el panel sin agendar (borde)
- **WHEN** se abre el panel, se elige a un paciente y se aprieta "Cerrar"
- **THEN** no se envía ningún pedido de escritura y la franja sigue "Libre"

#### Scenario: El aviso no muestra el email del paciente (borde)
- **WHEN** se agenda a Juan Perez, cuyo email es `juan.perez@example.com`
- **THEN** el aviso de éxito no contiene `juan.perez@example.com`

### Requirement: Reprogramar a otra franja libre del mismo profesional (US-009, Flujo 3, RN-TU-06, DD-24, DD-25, DD-64, DD-67, P-3)

"Reprogramar" SHALL abrir un diálogo con un campo de fecha (al abrir, la fecha del turno) y las franjas "Libre" de ese día del mismo profesional cuyo inicio es posterior a ahora, pedidas a `GET /api/v1/professionals/{id}/slots`. Sin franjas para ofrecer MUST mostrarse "No hay horarios libres este día". Elegir una franja MUST mostrar "Mover de <día> <HH:MM> a <día> <HH:MM>" y "Reprogramar turno", que envía un único `POST /api/v1/appointments/{id}/reschedule` con el inicio de esa franja. Con 200 MUST cerrarse el diálogo, mostrarse "Turno reprogramado: <día> <HH:MM>. Se enviará la confirmación por email al paciente." y la agenda MUST volver a pedirse. Con un rechazo, el diálogo MUST mostrar el mensaje del código y el turno MUST verse sin cambios al volver a pedir la agenda (RN-TU-06). El profesional no cambia (DD-64): para cambiarlo se cancela y se agenda de nuevo.

#### Scenario: Reprogramar a otro día (esperado)
- **WHEN** la recepcionista reprograma el turno de Juan Perez del lunes 09/11 10:00, cambia la fecha al martes 10/11, elige 11:00 y aprieta "Reprogramar turno"
- **THEN** se envía `POST /api/v1/appointments/{id}/reschedule` con ese inicio, se ve "Turno reprogramado: Mar 10/11 11:00. Se enviará la confirmación por email al paciente.", y la franja del lunes a las 10:00 vuelve a "Libre"

#### Scenario: La nueva franja se ocupó (error de negocio)
- **WHEN** se elige las 11:00 y antes de confirmar otra recepcionista agenda ahí
- **THEN** la API responde 409 `SLOT_TAKEN`, el diálogo muestra "Ese horario se acaba de ocupar. Elegí otro horario" y el turno de Juan Perez sigue el lunes a las 10:00

#### Scenario: Paciente desactivado (error de negocio)
- **WHEN** Ana Gómez fue desactivada después de agendar y se intenta reprogramar su turno
- **THEN** se ve "El paciente está inactivo: reactivalo desde Pacientes para darle o moverle turnos" y el turno no cambia (DD-25)

#### Scenario: Día sin horarios libres (borde)
- **WHEN** se elige en el diálogo un domingo sin atención, o un día de licencia del profesional
- **THEN** se ve "No hay horarios libres este día" y no hay franjas para elegir

#### Scenario: El horario actual no se ofrece (borde)
- **WHEN** se abre el diálogo en la fecha del turno
- **THEN** la franja del propio turno no aparece entre las opciones (está "Ocupado"), así que no se puede pedir el mismo horario (DD-67)

#### Scenario: Volver sin reprogramar (borde)
- **WHEN** se elige una franja y se aprieta "Volver"
- **THEN** no se envía ningún pedido de escritura y el turno sigue igual
