# Spec Delta: frontend-agenda

## MODIFIED Requirements

### Requirement: Licencias y turnos en conflicto (RN-HO-03, RN-HO-04, DD-68, P-5)

Un día cubierto por una licencia del profesional SHALL mostrarse como "Licencia" con su motivo si lo tiene, en lugar de "Sin atención este día" o de las franjas fuera de horario. Los turnos que figuran en `GET /professionals/{id}/conflicts` MUST mostrarse con el aviso "En conflicto: fuera del horario" o "En conflicto: en licencia", según el motivo. Para administración y recepción, elegir un turno en conflicto MUST abrir su detalle con "Reprogramar" y "Cancelar", y la lista completa de conflictos con acceso a resolverlos la define `frontend-appointment-management`; el odontólogo ve el aviso sin acciones para resolverlo. Los turnos `scheduled` que no figuran en esa lista (por ejemplo, porque ya empezaron) MUST mostrarse sin aviso.

#### Scenario: Día de licencia (esperado)
- **WHEN** la Dra. A tiene una licencia del 12/11 al 13/11 con motivo "Congreso" y se abre su semana del 09/11
- **THEN** el jueves y el viernes dicen "Licencia: Congreso"

#### Scenario: Turno agendado en un día de licencia (error de negocio)
- **WHEN** la Dra. A tenía un turno agendado el 12/11 a las 10:00 antes de cargar la licencia
- **THEN** el jueves dice "Licencia: Congreso" y además muestra ese turno con "En conflicto: en licencia"

#### Scenario: Turno fuera del horario nuevo (error de negocio)
- **WHEN** se acortó el horario de la Dra. A y su turno futuro de las 17:30 quedó fuera
- **THEN** el turno se ve a las 17:30 con "En conflicto: fuera del horario"

#### Scenario: Recepción abre un turno en conflicto (esperado)
- **WHEN** la recepcionista elige en la grilla el turno en conflicto del 12/11 a las 10:00
- **THEN** se abre su detalle con "En conflicto: en licencia", "Reprogramar" y "Cancelar"

#### Scenario: Odontóloga ve el conflicto sin resolverlo (borde)
- **WHEN** la Dra. A elige su turno en conflicto del 12/11 a las 10:00 antes de que empiece
- **THEN** ve el detalle con "En conflicto: en licencia" y sin "Reprogramar" ni "Cancelar"

#### Scenario: Licencia sin motivo (borde)
- **WHEN** la licencia no tiene motivo
- **THEN** el día dice "Licencia"

#### Scenario: Turno pasado en un día de licencia (borde)
- **WHEN** se mira una semana pasada con una licencia cargada después de que ocurrió un turno `scheduled` de ese día
- **THEN** el día dice "Licencia" y el turno se ve sin aviso de conflicto, porque ya empezó (DD-68)

## ADDED Requirements

### Requirement: Pedidos y actualización de la agenda (regla dura 6, DD-83)

La pantalla `/agenda` SHALL enviar solo pedidos `GET` y estos pedidos de escritura: `POST /appointments`, `POST /appointments/{id}/cancel`, `POST /appointments/{id}/reschedule`, `POST /appointments/{id}/attendance` y `POST /patients` (alta de paciente desde el panel de agendar), cada uno solo como resultado de una acción confirmada por la persona según `frontend-appointment-management`. MUST NOT enviar `PUT`, `PATCH` ni `DELETE`. La pantalla del odontólogo MUST enviar como escritura solo `POST /appointments/{id}/attendance`. La información MUST volver a pedirse al cambiar profesional, fecha o vista, al apretar "Actualizar", después de cada acción correcta y después de cada rechazo con código de la API; no hay actualización automática por tiempo.

#### Scenario: Mirar no escribe (esperado)
- **WHEN** la recepcionista recorre la semana de la Dra. A y abre el detalle de dos turnos sin confirmar ninguna acción
- **THEN** la pantalla solo hizo pedidos `GET`

#### Scenario: Actualizar trae lo nuevo (esperado)
- **WHEN** otra recepcionista agendó un turno a las 15:00 y se aprieta "Actualizar"
- **THEN** la franja de las 15:00 pasa a "Ocupado" con ese turno

#### Scenario: Después de agendar se vuelve a pedir (esperado)
- **WHEN** la recepcionista agenda un turno a las 10:00
- **THEN** la agenda se vuelve a pedir y la franja de las 10:00 dice "Ocupado" sin apretar "Actualizar"

#### Scenario: Odontóloga solo marca atención (borde)
- **WHEN** la Dra. A usa su agenda durante un día y marca dos turnos
- **THEN** los únicos pedidos que no son `GET` fueron dos `POST /appointments/{id}/attendance`

## REMOVED Requirements

### Requirement: Solo lectura (P-9, P-10, regla dura 6)
**Reason**: C-10 agrega a la agenda agendar, cancelar, reprogramar y marcar atención (DD-83 dejaba esas acciones para C-10).
**Migration**: lo que la pantalla puede enviar y cuándo se actualiza pasa al requirement "Pedidos y actualización de la agenda"; las acciones y quién las ve, a la spec `frontend-appointment-management`.
