# Spec Delta: frontend-agenda

## ADDED Requirements

### Requirement: Tratamiento en la grilla (C-17, DD-146)

En la vista del día y de la semana, cada turno con tratamiento SHALL mostrar el nombre del tratamiento después del nombre del paciente, separado por " · ", antes de las etiquetas de estado y de origen. Si el nombre no entra en el ancho de la columna, MUST cortarse con puntos suspensivos sin desplazamiento horizontal, y el texto completo MUST quedar disponible para lectores de pantalla y en el detalle. Un turno sin tratamiento MUST verse como antes, sin texto ni etiqueta vacía. La grilla sigue sin mostrar email, teléfono ni documento del paciente.

#### Scenario: Turno con tratamiento (esperado)
- **WHEN** a las 10:00 hay un turno de Juan Perez con "Limpieza dental"
- **THEN** la grilla muestra "10:00–10:30 Perez, Juan · Limpieza dental" con su etiqueta de estado

#### Scenario: Turno anterior sin tratamiento (borde)
- **WHEN** un turno no tiene tratamiento
- **THEN** la línea es igual a la de antes de C-17

#### Scenario: Nombre largo en la semana a 375 px (borde)
- **WHEN** la vista de la semana tiene un turno de "Arreglo de caries" y la pantalla mide 375 px
- **THEN** el nombre se corta con puntos suspensivos y la página no se desplaza en horizontal

#### Scenario: Turno cancelado con tratamiento (borde)
- **WHEN** un turno cancelado tenía "Extracción"
- **THEN** se ve tachado y atenuado con el tratamiento, como el resto de la línea
