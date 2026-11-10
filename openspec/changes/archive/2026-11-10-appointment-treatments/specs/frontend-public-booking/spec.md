# Spec Delta: frontend-public-booking

## ADDED Requirements

### Requirement: Elegir el tratamiento después del profesional (C-17)

En `/turnos`, después de elegir el profesional, la página SHALL mostrar el paso "Tratamiento" con los tratamientos públicos de ese profesional como botones (`aria-pressed`), y recién con un tratamiento elegido MUST mostrar el día y las franjas. Cambiar de profesional MUST borrar el tratamiento y la franja elegidos. Cambiar de tratamiento MUST conservar el día y borrar la franja. La reserva MUST enviar `treatment_id`. El texto "Turno elegido" del formulario MUST incluir el tratamiento. Ante `TREATMENT_NOT_AVAILABLE`, la página MUST mostrar "El tratamiento elegido ya no está disponible. Elija otro.", volver a pedir los tratamientos, borrar el tratamiento elegido y conservar los datos escritos del formulario. La lista de tratamientos MUST mostrar su carga y su error con reintento, como los profesionales.

#### Scenario: Elegir tratamiento (esperado)
- **WHEN** el paciente elige a la Dra. A
- **THEN** ve "Consulta", "Limpieza dental" y los demás que ofrece, y todavía no ve los días ni las franjas

#### Scenario: Franjas después del tratamiento (esperado)
- **WHEN** el paciente elige "Limpieza dental"
- **THEN** ve el selector de día y las franjas, y el turno elegido dice "Dra. Ana Alvarez, Limpieza dental, <día y hora>"

#### Scenario: Cambiar de profesional (borde)
- **WHEN** el paciente eligió a la Dra. A y "Blanqueamiento" y después elige al Dr. B
- **THEN** no queda ningún tratamiento ni franja elegidos y ve los tratamientos del Dr. B

#### Scenario: Tratamiento que dejó de estar disponible (error de negocio)
- **WHEN** el paciente envía la reserva y la API responde `TREATMENT_NOT_AVAILABLE`
- **THEN** ve "El tratamiento elegido ya no está disponible. Elija otro.", la lista se vuelve a pedir y sus datos siguen escritos

#### Scenario: Error al cargar tratamientos (error)
- **WHEN** la API no responde al pedir los tratamientos
- **THEN** ve un aviso de error con la opción de reintentar

### Requirement: Tratamiento en las pantallas de resultado (C-17)

La pantalla "Turno registrado exitosamente" y la de "Turno confirmado" SHALL mostrar la fila "Tratamiento" con el nombre que devolvió la API, junto al profesional y al día y hora. En "Turno registrado" el texto MUST seguir siendo idéntico para un DNI nuevo y uno existente. En "Turno confirmado" la fila MUST omitirse si la API devuelve `treatment_name` nulo.

#### Scenario: Turno registrado con tratamiento (esperado)
- **WHEN** la reserva de "Limpieza dental" con la Dra. A responde 202
- **THEN** la pantalla muestra "Tratamiento: Limpieza dental" y no muestra email, nombre ni documento del paciente

#### Scenario: Turno confirmado con tratamiento (esperado)
- **WHEN** el paciente confirma desde el enlace
- **THEN** la pantalla "Turno confirmado" muestra el tratamiento

#### Scenario: Confirmación de una reserva sin tratamiento (borde)
- **WHEN** se confirma una reserva hecha antes de C-17
- **THEN** la pantalla "Turno confirmado" no muestra la fila de tratamiento
