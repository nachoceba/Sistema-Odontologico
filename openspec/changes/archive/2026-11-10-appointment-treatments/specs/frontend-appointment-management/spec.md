# Spec Delta: frontend-appointment-management

## ADDED Requirements

### Requirement: Elegir el tratamiento al agendar (C-17, DD-142)

El panel de agendar SHALL mostrar, debajo del paciente, un selector "Tratamiento" con los tratamientos activos que ofrece el profesional de la agenda, ordenados por nombre, pedidos con `GET /api/v1/professionals/{professional_id}/treatments`. El selector arranca sin elección ("Elegí el tratamiento"). "Agendar turno" MUST estar habilitado solo con paciente y tratamiento elegidos, y el `POST /api/v1/appointments` MUST llevar `treatment_id`. Si el profesional no tiene tratamientos activos, el panel MUST mostrar "Este profesional no tiene tratamientos activos. Pedile al administrador que se los asigne." y no permitir agendar. Ante `TREATMENT_NOT_AVAILABLE` el panel MUST mostrar "Ese tratamiento ya no está disponible para este profesional. Elegí otro.", volver a pedir los tratamientos y conservar el paciente. El aviso de éxito MUST sumar el tratamiento: "Turno agendado: <Apellido, Nombre>, <día> <HH:MM>, <tratamiento>. Se enviará la confirmación por email al paciente.". La carga y el error de la lista de tratamientos MUST mostrarse con los avisos de C-14.

#### Scenario: Agendar con tratamiento (esperado)
- **WHEN** la recepcionista elige la franja de las 10:00 de la Dra. A, elige a Juan Perez y "Limpieza dental" y aprieta "Agendar turno"
- **THEN** se envía un `POST /api/v1/appointments` con `treatment_id` de "Limpieza dental" y se ve "Turno agendado: Perez, Juan, Lun 09/11 10:00, Limpieza dental. Se enviará la confirmación por email al paciente."

#### Scenario: Sin tratamiento elegido (borde)
- **WHEN** hay paciente elegido pero no tratamiento
- **THEN** "Agendar turno" está deshabilitado y no se envía ningún pedido

#### Scenario: Profesional sin tratamientos activos (borde)
- **WHEN** se abre el panel de agendar del Dr. B y no tiene tratamientos activos
- **THEN** se ve el aviso para pedírselos al administrador y no se puede agendar

#### Scenario: Tratamiento desactivado mientras se agendaba (error de negocio)
- **WHEN** el administrador desactiva "Blanqueamiento" y la recepcionista aprieta "Agendar turno" con ese tratamiento elegido
- **THEN** el panel muestra "Ese tratamiento ya no está disponible para este profesional. Elegí otro.", la lista se vuelve a pedir sin "Blanqueamiento" y el paciente sigue elegido

#### Scenario: Doble clic con tratamiento (borde)
- **WHEN** se aprieta dos veces seguidas "Agendar turno" con paciente y tratamiento elegidos
- **THEN** se envía un solo `POST /api/v1/appointments`

### Requirement: Tratamiento en el detalle del turno (C-17, DD-144, DD-148)

El detalle del turno SHALL mostrar la fila "Tratamiento" con el nombre del tratamiento, o "Sin tratamiento" si el turno no tiene. El detalle MUST NOT ofrecer cambiar el tratamiento. Reprogramar MUST mantener el tratamiento y el diálogo de reprogramar MUST mostrarlo como dato fijo. Los tres roles ven el tratamiento en el detalle.

#### Scenario: Turno con tratamiento (esperado)
- **WHEN** la recepcionista abre un turno de "Extracción"
- **THEN** el detalle muestra "Tratamiento: Extracción" y ninguna acción para cambiarlo

#### Scenario: Turno anterior sin tratamiento (borde)
- **WHEN** se abre un turno agendado antes de C-17
- **THEN** el detalle muestra "Tratamiento: Sin tratamiento"

#### Scenario: Reprogramar muestra el tratamiento (esperado)
- **WHEN** la recepcionista reprograma un turno de "Extracción"
- **THEN** el diálogo muestra "Extracción" y el turno movido lo conserva
