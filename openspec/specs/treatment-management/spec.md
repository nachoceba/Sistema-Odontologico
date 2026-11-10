# treatment-management Specification

## Purpose
Definir el catálogo de tratamientos del consultorio, qué tratamientos ofrece cada profesional y cuándo un tratamiento es válido para un turno nuevo, sin cambiar la duración de los turnos (DD-03).

## Requirements

### Requirement: Catálogo de tratamientos (DD-143, DD-145)

El sistema SHALL guardar un catálogo único de tratamientos del consultorio. Cada tratamiento tiene un identificador, un nombre y un indicador de activo. El nombre MUST recortarse de espacios al principio y al final, reducir los espacios repetidos a uno, tener entre 1 y 80 caracteres y ser único sin distinguir mayúsculas ni tildes. Solo el administrador MUST poder crear un tratamiento, cambiarle el nombre y activarlo o desactivarlo. Un tratamiento MUST NOT borrarse: se desactiva. El catálogo se lista ordenado por nombre.

#### Scenario: Alta de un tratamiento (esperado)
- **WHEN** el administrador crea el tratamiento "  Limpieza   dental "
- **THEN** queda guardado como "Limpieza dental", activo

#### Scenario: Nombre repetido sin distinguir mayúsculas ni tildes (error de negocio)
- **WHEN** existe "Extracción" y el administrador crea "extraccion"
- **THEN** se rechaza con `TREATMENT_NAME_TAKEN` y no se crea nada

#### Scenario: Cambiar el nombre al mismo nombre con otra mayúscula (borde)
- **WHEN** el administrador cambia "limpieza dental" a "Limpieza dental"
- **THEN** se acepta, porque es el mismo tratamiento

#### Scenario: Nombre vacío o demasiado largo (error)
- **WHEN** el administrador crea un tratamiento con nombre "   " o de 81 caracteres
- **THEN** se rechaza como entrada inválida y no se crea nada

#### Scenario: Desactivar no borra (borde)
- **WHEN** el administrador desactiva "Blanqueamiento"
- **THEN** sigue en el catálogo como inactivo y los turnos que ya lo tienen lo conservan

### Requirement: Tratamientos que ofrece cada profesional (DD-141)

El sistema SHALL guardar, para cada profesional, el conjunto de tratamientos que ofrece. Solo el administrador MUST poder cambiarlo, y lo hace reemplazando el conjunto completo. Cada identificador del conjunto MUST corresponder a un tratamiento existente; puede estar inactivo. Un identificador repetido cuenta una sola vez. Quitar un tratamiento de un profesional MUST NOT tocar los turnos que ya lo tienen. El conjunto ofrecido para agendar es el de los tratamientos asignados y activos, ordenados por nombre.

#### Scenario: Asignar tratamientos (esperado)
- **WHEN** el administrador asigna a la Dra. A "Consulta", "Limpieza dental" y "Arreglo de caries"
- **THEN** la Dra. A ofrece exactamente esos tres

#### Scenario: Reemplazo completo (esperado)
- **WHEN** la Dra. A ofrecía tres tratamientos y el administrador guarda solo "Consulta"
- **THEN** ofrece solo ese y los turnos ya agendados con los otros dos los conservan

#### Scenario: Tratamiento inexistente en la lista (error)
- **WHEN** el administrador guarda una lista con un identificador que no existe
- **THEN** se rechaza con `TREATMENT_NOT_FOUND` y la asignación anterior queda igual

#### Scenario: Lista vacía (borde)
- **WHEN** el administrador guarda una lista vacía para el Dr. B
- **THEN** el Dr. B no ofrece ningún tratamiento y no se le pueden agendar turnos nuevos hasta que tenga uno

#### Scenario: Asignado pero inactivo (borde)
- **WHEN** la Dra. A tiene asignado "Blanqueamiento" y está inactivo
- **THEN** sigue asignado pero no aparece entre los tratamientos ofrecidos para agendar

#### Scenario: Profesional inexistente (error)
- **WHEN** el administrador asigna tratamientos a un profesional que no existe
- **THEN** se rechaza con `PROFESSIONAL_NOT_FOUND`

### Requirement: Tratamiento válido para un turno nuevo (DD-142)

Todo turno nuevo, agendado por la recepción o reservado online, SHALL llevar un tratamiento. El tratamiento MUST existir, estar activo y estar asignado al profesional del turno en el momento de agendar. La regla es una función pura que recibe el tratamiento (o su ausencia), su estado y el conjunto asignado al profesional, y devuelve aceptado o el motivo: inexistente, inactivo o no ofrecido por ese profesional. El tratamiento MUST NOT cambiar la duración del turno, la grilla, las franjas libres ni la regla de no superposición: el fin del turno sigue siendo inicio más `slot_minutes` (DD-03, RN-TU-02).

#### Scenario: Tratamiento válido (esperado)
- **WHEN** se agenda con la Dra. A el tratamiento "Limpieza dental", activo y asignado a ella
- **THEN** la regla lo acepta y el turno dura `slot_minutes`

#### Scenario: Tratamiento de otro profesional (error de negocio)
- **WHEN** se agenda con el Dr. B el tratamiento "Blanqueamiento", que solo ofrece la Dra. A
- **THEN** la regla lo rechaza por no ofrecido

#### Scenario: Tratamiento inactivo (error de negocio)
- **WHEN** se agenda con la Dra. A "Blanqueamiento", asignado pero inactivo
- **THEN** la regla lo rechaza por inactivo

#### Scenario: Tratamiento inexistente (error)
- **WHEN** se agenda con un identificador de tratamiento que no existe
- **THEN** la regla lo rechaza por inexistente

#### Scenario: Mismo tratamiento, misma duración (borde)
- **WHEN** se agendan "Consulta" y "Extracción" en franjas seguidas de la Dra. A con `slot_minutes = 30`
- **THEN** los dos turnos duran 30 minutos y no se superponen

### Requirement: Turnos sin tratamiento (DD-148)

Los turnos creados antes de este cambio SHALL quedar sin tratamiento, sin completarlos con un valor inventado. Un turno sin tratamiento MUST poder verse, cancelarse, reprogramarse y marcarse como atendido o ausente igual que antes.

#### Scenario: Turno anterior sin tratamiento (borde)
- **WHEN** se lee un turno agendado antes de la migración
- **THEN** su tratamiento es nulo y el turno sigue funcionando como antes

#### Scenario: Reprogramar un turno anterior (borde)
- **WHEN** la recepción reprograma un turno sin tratamiento
- **THEN** se reprograma sin pedir tratamiento y sigue sin tratamiento
