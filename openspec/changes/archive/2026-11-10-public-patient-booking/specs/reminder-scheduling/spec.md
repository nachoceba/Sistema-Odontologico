# Spec Delta: reminder-scheduling

## MODIFIED Requirements

### Requirement: Turnos que reciben recordatorio (RN-NO-02, Flujo 4, DD-76)

Cuando la pasada actúa SHALL tomar los turnos en estado `scheduled` que no están pendientes de confirmación (C-15, DD-130) cuyo inicio cae en el día local siguiente al de la pasada, en la zona del consultorio (desde las 00:00 incluidas hasta las 00:00 del día posterior excluidas), de todos los profesionales. MUST NOT tomar turnos `cancelled`, `completed` ni `no_show`, ni turnos pendientes de confirmación, ni turnos que empiezan otro día aunque terminen o se superpongan con ese día. El registro del recordatorio MUST comprobar, en el mismo momento en que lo escribe, que el turno sigue `scheduled`, con el mismo inicio y sin estar pendiente. Los turnos de pacientes inactivos (DD-76) y los de profesionales inactivos o con turnos en conflicto por horario o licencia (RN-HO-04, DD-68) MUST recibir recordatorio igual mientras sigan `scheduled` y confirmados. Un turno online confirmado después de la pasada del día recibe solo la confirmación.

#### Scenario: Turnos de mañana de todos los profesionales (esperado)
- **WHEN** la pasada actúa el domingo 08/11/2026 a las 09:00 y hay turnos `scheduled` el lunes 09/11 a las 10:00 con la Dra. A y a las 15:00 con el Dr. B
- **THEN** ambos turnos reciben recordatorio

#### Scenario: Turno cancelado excluido (error de negocio)
- **WHEN** la pasada actúa y un turno del lunes 09/11 a las 11:00 está `cancelled`
- **THEN** ese turno no recibe recordatorio y no se registra ninguna notificación para él

#### Scenario: Turno pendiente de confirmación excluido (error de negocio)
- **WHEN** la pasada actúa y un turno online del lunes 09/11 sigue pendiente de confirmación
- **THEN** ese turno no recibe recordatorio

#### Scenario: Turno online confirmado antes de la pasada (esperado)
- **WHEN** un turno online del lunes se confirmó el domingo a las 08:30 y la pasada actúa a las 09:00
- **THEN** recibe recordatorio como cualquier otro

#### Scenario: Límites del día en la zona del consultorio (borde)
- **WHEN** la pasada actúa el domingo 08/11/2026 a las 09:00 hora local y hay turnos `scheduled` el lunes 09/11 a las 00:00 hora local (03:00 UTC del lunes), el domingo 08/11 a las 23:30 hora local (02:30 UTC del lunes) y el martes 10/11 a las 00:00 hora local
- **THEN** solo el del lunes 09/11 a las 00:00 recibe recordatorio

#### Scenario: Turno que cruza la medianoche (borde)
- **WHEN** la pasada actúa el domingo y hay un turno `scheduled` del domingo 23:45 al lunes 00:15 hora local
- **THEN** ese turno no recibe recordatorio (empieza el domingo)

#### Scenario: Paciente inactivo con turno vigente (borde)
- **WHEN** la pasada actúa y el paciente de un turno `scheduled` del lunes fue desactivado
- **THEN** ese turno recibe recordatorio (DD-76)

#### Scenario: Profesional inactivo o turno en conflicto (borde)
- **WHEN** la pasada actúa y un turno `scheduled` del lunes es de un profesional inactivo, o cae en un día de licencia cargada después de agendarlo
- **THEN** ese turno recibe recordatorio igual

#### Scenario: Sin turnos mañana (borde)
- **WHEN** la pasada actúa y no hay turnos `scheduled` el día siguiente
- **THEN** no se registra ninguna notificación y el registro de la pasada informa cero en todas las cantidades
