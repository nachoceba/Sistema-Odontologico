# patient-repository Specification

## Purpose
Definir el contrato mínimo para consultar un paciente por identificador y saber si existe y si está activo, que es lo que necesitan los casos de uso de turnos para aplicar RN-PA-04 sin depender de la base de datos.

## Requirements

### Requirement: Contrato único para pacientes

Toda implementación del repositorio de pacientes SHALL cumplir los escenarios de esta spec; la batería de contrato MUST ejecutarse contra cada implementación registrada (la de memoria y la de PostgreSQL). Los pacientes iniciales de cada escenario MUST cargarse a través de la fábrica, que completa los datos que la base exige y la batería no usa (por ejemplo, un documento ficticio único), y la batería MUST referirse a ellos por los identificadores que devuelve la fábrica.

#### Scenario: La batería corre contra cada implementación (esperado)
- **DADO** la batería de contrato de pacientes y la lista de implementaciones registradas
- **CUANDO** se ejecuta la batería
- **ENTONCES** cada escenario corre una vez por implementación y todos pasan

#### Scenario: Identificador con formato que la base no usa (borde)
- **DADO** el repositorio de PostgreSQL con Juan Pérez cargado
- **CUANDO** se busca el paciente `no-existe`
- **ENTONCES** el resultado es "no encontrado", sin error

### Requirement: Buscar un paciente por identificador

Buscar un paciente SHALL devolver su identificador, nombre, apellido, email y si está activo, o un valor "no encontrado" si no existe (no es un error). El dato `active` devuelto MUST ser booleano, para poder pasarlo tal cual a la regla de `patient-booking-eligibility`.

#### Scenario: Paciente activo (esperado)
- **DADO** el paciente Juan Pérez cargado como activo
- **CUANDO** se lo busca por su identificador
- **ENTONCES** se devuelve con nombre, apellido, email y `active = true`

#### Scenario: Paciente inactivo, listo para la regla RN-PA-04 (error de negocio)
- **DADO** la paciente Ana Gómez cargada como inactiva
- **CUANDO** se la busca y su `active` se pasa a la regla de elegibilidad
- **ENTONCES** la regla rechaza con `PATIENT_INACTIVE`

#### Scenario: Paciente inexistente (borde)
- **DADO** un repositorio con Juan Pérez
- **CUANDO** se busca un identificador que no existe
- **ENTONCES** el resultado es "no encontrado", sin error

### Requirement: Leer la ficha completa de un paciente

El repositorio SHALL devolver la ficha completa de un paciente por identificador: identificador, nombre, apellido, documento normalizado, email, teléfono (o ausente), fecha de nacimiento (o ausente) y si está activo; o "no encontrado" si no existe o el identificador tiene un formato que la base no usa (no es un error). La búsqueda por identificador existente (`get`) MUST seguir devolviendo lo mismo que antes, para no cambiar a la agenda (C-08).

#### Scenario: Ficha con datos opcionales (esperado)
- **DADO** Juan Pérez cargado con documento `30111222`, teléfono `011-5550-0001` y sin fecha de nacimiento
- **CUANDO** se lee su ficha completa
- **ENTONCES** se devuelven todos sus datos, el teléfono y la fecha de nacimiento ausente

#### Scenario: Identificador inexistente o mal formado (borde)
- **CUANDO** se lee la ficha de `no-existe`
- **ENTONCES** el resultado es "no encontrado", sin error

#### Scenario: La búsqueda mínima no cambia (esperado)
- **DADO** Juan Pérez cargado con todos sus datos
- **CUANDO** se lo busca con la búsqueda mínima usada por la agenda
- **ENTONCES** se devuelven identificador, nombre, apellido, email y `active`, como antes de este change

### Requirement: Alta con documento único (RN-PA-01)

Dar de alta un paciente SHALL guardarlo activo y devolver su ficha con un identificador nuevo. Si ya existe un paciente (activo o inactivo) con el mismo documento normalizado, MUST rechazarse con `DOCUMENT_TAKEN` sin guardar nada. La garantía MUST valer también ante dos altas simultáneas con el mismo documento: en PostgreSQL la protege la restricción de unicidad de la base y el rechazo de la base MUST traducirse a `DOCUMENT_TAKEN`.

#### Scenario: Alta nueva (esperado)
- **CUANDO** se da de alta a Laura Ruiz con documento `40222333`
- **ENTONCES** queda guardada y activa, y leer su ficha devuelve los mismos datos

#### Scenario: Documento repetido (error de negocio)
- **DADO** Juan Pérez con documento `30111222`
- **CUANDO** se da de alta a otra persona con documento `30111222`
- **ENTONCES** se rechaza con `DOCUMENT_TAKEN` y sigue habiendo un solo paciente con ese documento

#### Scenario: Documento de un paciente inactivo (borde)
- **DADO** Ana Gómez inactiva con documento `30111223`
- **CUANDO** se da de alta a otra persona con documento `30111223`
- **ENTONCES** se rechaza con `DOCUMENT_TAKEN`

#### Scenario: Dos altas simultáneas con el mismo documento (borde, PostgreSQL)
- **CUANDO** dos sesiones dan de alta al mismo tiempo pacientes con documento `40222333`
- **ENTONCES** una se guarda y la otra se rechaza con `DOCUMENT_TAKEN`

### Requirement: Buscar pacientes (US-003, P-3 y P-5 confirmadas)

El repositorio SHALL buscar pacientes por un texto: un paciente coincide si su apellido contiene el texto sin distinguir mayúsculas de minúsculas, o si su documento normalizado empieza con el texto normalizado como documento. Sin texto, todos coinciden. Los caracteres `%` y `_` del texto MUST tratarse como caracteres comunes. Por defecto MUST devolver solo los activos; a pedido MUST incluir también los inactivos. El resultado MUST ordenarse por apellido, luego nombre y luego identificador, y MUST respetar un máximo de resultados indicado por quien llama. Las implementaciones en memoria y PostgreSQL MUST dar el mismo resultado para el mismo texto.

#### Scenario: Por apellido parcial sin distinguir mayúsculas (esperado)
- **DADO** Juan Pérez, Marta López y Lucía Torres activos
- **CUANDO** se busca `pÉ`
- **ENTONCES** el resultado es solo Juan Pérez

#### Scenario: Por inicio del documento con puntos (esperado)
- **DADO** documentos `30111222` y `30111223` y `40222333`
- **CUANDO** se busca `30.111`
- **ENTONCES** el resultado son los dos primeros, ordenados por apellido

#### Scenario: Inactivos excluidos por defecto (borde)
- **DADO** Juan Pérez activo y Ana Gómez inactiva
- **CUANDO** se busca sin texto, primero por defecto y después pidiendo incluir inactivos
- **ENTONCES** la primera búsqueda devuelve solo a Juan y la segunda a ambos con su estado

#### Scenario: Comodines como texto (borde)
- **DADO** pacientes cuyos apellidos no contienen `%`
- **CUANDO** se busca `%`
- **ENTONCES** el resultado es vacío

#### Scenario: Máximo de resultados (borde)
- **DADO** 5 pacientes activos
- **CUANDO** se busca sin texto con un máximo de 3
- **ENTONCES** se devuelven los 3 primeros en orden de apellido

### Requirement: Editar un paciente

El repositorio SHALL cambiar solo los datos indicados de un paciente y devolver la ficha actualizada; teléfono y fecha de nacimiento MUST poder borrarse. Cambiar el documento a uno que ya tiene otro paciente MUST rechazarse con `DOCUMENT_TAKEN` sin cambiar nada; mantener el propio documento MUST NOT ser un conflicto. Un paciente inexistente MUST rechazarse con `PATIENT_NOT_FOUND`.

#### Scenario: Cambiar email y borrar teléfono (esperado)
- **DADO** Juan Pérez con teléfono
- **CUANDO** se cambia su email y se borra su teléfono
- **ENTONCES** la ficha tiene el email nuevo, sin teléfono, y el resto igual

#### Scenario: Documento de otro paciente (error de negocio)
- **DADO** Juan Pérez `30111222` y Luis Fernández `30111224`
- **CUANDO** se cambia el documento de Luis a `30111222`
- **ENTONCES** se rechaza con `DOCUMENT_TAKEN` y Luis conserva `30111224`

#### Scenario: Reenviar el propio documento (borde)
- **CUANDO** se edita a Juan Pérez indicando su mismo documento `30111222`
- **ENTONCES** se guarda sin error

#### Scenario: Paciente inexistente (error de negocio)
- **CUANDO** se edita el paciente `no-existe`
- **ENTONCES** se rechaza con `PATIENT_NOT_FOUND`

### Requirement: Activar y desactivar (RN-PA-03)

El repositorio SHALL marcar un paciente como activo o inactivo y devolver su ficha. Marcar el estado que ya tiene MUST NOT ser un error. Desactivar MUST NOT modificar ni borrar sus turnos. Un paciente inexistente MUST rechazarse con `PATIENT_NOT_FOUND`.

#### Scenario: Desactivar y la regla RN-PA-04 lo ve (esperado)
- **DADO** Juan Pérez activo
- **CUANDO** se lo desactiva y luego se lo busca con la búsqueda mínima
- **ENTONCES** `active = false` y la regla de elegibilidad rechaza con `PATIENT_INACTIVE`

#### Scenario: Reactivar (esperado)
- **DADO** Ana Gómez inactiva
- **CUANDO** se la activa
- **ENTONCES** su ficha queda con `active = true`

#### Scenario: Desactivar a quien ya está inactivo (borde)
- **CUANDO** se desactiva a Ana Gómez, que ya está inactiva
- **ENTONCES** se devuelve su ficha inactiva, sin error

### Requirement: Borrar un paciente sin turnos (matriz RBAC, RN-PA-03, P-6 confirmada)

El repositorio SHALL borrar definitivamente un paciente y responder si existía. En PostgreSQL, si el paciente tiene algún turno (en cualquier estado), la base lo impide (`ON DELETE RESTRICT`, DD-39) y ese rechazo MUST traducirse a `PATIENT_HAS_APPOINTMENTS` sin borrar nada.

#### Scenario: Paciente sin turnos (esperado)
- **DADO** Laura Ruiz sin turnos
- **CUANDO** se la borra
- **ENTONCES** la respuesta es "borrado" y leer su ficha da "no encontrado"

#### Scenario: Paciente inexistente (borde)
- **CUANDO** se borra `no-existe`
- **ENTONCES** la respuesta es "no existía", sin error

#### Scenario: Paciente con un turno cancelado (error de negocio, PostgreSQL)
- **DADO** Juan Pérez con un turno `cancelled`
- **CUANDO** se lo borra
- **ENTONCES** se rechaza con `PATIENT_HAS_APPOINTMENTS` y el paciente y el turno siguen existiendo
