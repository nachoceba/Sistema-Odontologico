# frontend-patient-management Specification

## Purpose
Darle a recepción y administración una pantalla `/pacientes` para buscar, dar de alta, editar, desactivar y reactivar pacientes (y al odontólogo una vista de solo lectura), con un buscador y un formulario reutilizables por la pantalla de turnos de C-10.

## Requirements

### Requirement: Acceso a la pantalla de pacientes (matriz RBAC, P-4 y P-11 confirmadas)

El frontend SHALL ofrecer la ruta protegida `/pacientes` y el enlace "Pacientes" para los tres roles. Administración y recepción MUST ver los controles de alta, edición, desactivar y reactivar; solo administración MUST ver "Borrar". El odontólogo MUST ver la búsqueda y las fichas sin ningún control de escritura. Sin sesión, `/pacientes` MUST llevar a `/login`.

#### Scenario: Recepción con controles (esperado)
- **CUANDO** la recepcionista abre `/pacientes`
- **ENTONCES** ve el botón "Nuevo paciente" y, en cada fila, "Editar" y "Desactivar" o "Reactivar", y no ve "Borrar"

#### Scenario: Odontólogo en modo lectura (esperado)
- **CUANDO** la Dra. A abre `/pacientes`
- **ENTONCES** ve el listado y la búsqueda, y no ve "Nuevo paciente", "Editar", "Desactivar", "Reactivar" ni "Borrar"

#### Scenario: Sin sesión (borde)
- **CUANDO** alguien sin token abre `/pacientes`
- **ENTONCES** el frontend lo lleva a `/login`

### Requirement: Buscar y listar en pantalla (US-003)

La pantalla SHALL mostrar una tabla con apellido y nombre, documento, email, teléfono y estado ("Activo" o "Inactivo") de los pacientes que devuelve la búsqueda, en el orden recibido. Escribir en el cuadro de búsqueda MUST pedir la búsqueda a la API como máximo una vez cada 300 ms. Una casilla "Incluir inactivos" MUST sumar los inactivos. Si la API indica que hay más resultados, MUST mostrarse "Hay más resultados: afiná la búsqueda". Sin resultados MUST mostrarse "No se encontraron pacientes". Mientras carga MUST mostrar "Cargando…"; ante un error de red o un 5xx, "No se pudo conectar con el servidor".

#### Scenario: Buscar por apellido (esperado)
- **CUANDO** la recepcionista escribe `pér`
- **ENTONCES** se pide la búsqueda con `q=pér` una sola vez y la tabla muestra a Juan Pérez

#### Scenario: Incluir inactivos (esperado)
- **CUANDO** marca "Incluir inactivos"
- **ENTONCES** la tabla suma a Ana Gómez con el estado "Inactivo"

#### Scenario: Resultado truncado (borde)
- **CUANDO** la API responde con `truncated = true`
- **ENTONCES** se muestra "Hay más resultados: afiná la búsqueda"

#### Scenario: Servidor caído (error)
- **CUANDO** la búsqueda falla por error de red
- **ENTONCES** se muestra "No se pudo conectar con el servidor"

### Requirement: Formulario de alta y edición

El formulario SHALL pedir nombre, apellido, documento y email (obligatorios) y teléfono y fecha de nacimiento (opcionales). Con un obligatorio vacío MUST mostrar el error junto al campo sin llamar a la API. Un 409 `DOCUMENT_TAKEN` MUST mostrarse como "Ya existe un paciente con ese documento" junto al documento, conservando lo escrito. Un 422 MUST mostrarse como "Revisá los datos ingresados" y un 400 `INVALID_PATIENT_DATA` como "La fecha de nacimiento no puede ser futura". Tras guardar, la tabla MUST reflejar el cambio. El formulario MUST poder usarse fuera de la pantalla (C-10) y avisar a quien lo usa el paciente guardado.

#### Scenario: Alta correcta (esperado)
- **CUANDO** la recepcionista completa los obligatorios de Laura Ruiz y guarda
- **ENTONCES** se envía `POST /api/v1/patients` y Laura aparece en la tabla

#### Scenario: Documento repetido (error de negocio)
- **CUANDO** la API responde 409 `DOCUMENT_TAKEN`
- **ENTONCES** se muestra "Ya existe un paciente con ese documento" y los datos escritos siguen en el formulario

#### Scenario: Email vacío (borde)
- **CUANDO** se intenta guardar sin email
- **ENTONCES** se muestra el error junto al email y no se llama a la API

#### Scenario: Borrar el teléfono al editar (borde)
- **CUANDO** al editar a Juan Pérez se vacía el teléfono y se guarda
- **ENTONCES** se envía `PATCH` con `phone = null`

### Requirement: Desactivar, reactivar y borrar

"Desactivar" SHALL pedir confirmación ("¿Desactivar a <nombre y apellido>? Sus turnos no se cancelan.") y, tras desactivar, si la respuesta trae turnos futuros MUST mostrar "Este paciente tiene N turnos agendados. Para reprogramarlos, reactivalo primero; si no, cancelalos desde la agenda" con fecha y hora local de cada uno (zona del consultorio). "Reactivar" SHALL actuar sin confirmación. "Borrar" (solo administración) SHALL pedir confirmación; un 409 `PATIENT_HAS_APPOINTMENTS` MUST mostrarse como "No se puede borrar: tiene turnos. Desactivalo en su lugar".

#### Scenario: Desactivar con turnos (esperado)
- **CUANDO** la recepcionista confirma desactivar a Juan Pérez y la respuesta trae un turno el jueves 05/11 a las 10:00 (hora del consultorio)
- **ENTONCES** Juan figura "Inactivo" y se muestra el aviso con `jue 05/11 10:00`

#### Scenario: Cancelar la confirmación (borde)
- **CUANDO** la recepcionista pulsa "Desactivar" y luego cancela
- **ENTONCES** no se llama a la API y Juan sigue "Activo"

#### Scenario: Borrar con turnos (error de negocio)
- **CUANDO** el administrador confirma borrar a Juan Pérez y la API responde 409 `PATIENT_HAS_APPOINTMENTS`
- **ENTONCES** se muestra "No se puede borrar: tiene turnos. Desactivalo en su lugar" y Juan sigue en la tabla

### Requirement: Buscador reutilizable para elegir un paciente (para C-10)

El frontend SHALL ofrecer un buscador de pacientes reutilizable que muestra solo pacientes activos y avisa a quien lo usa el paciente elegido. MUST NOT ofrecer elegir pacientes inactivos (RN-PA-04).

#### Scenario: Elegir un paciente (esperado)
- **CUANDO** se escribe `torres` en el buscador y se elige a Lucía Torres
- **ENTONCES** quien usa el buscador recibe el identificador y el nombre de Lucía

#### Scenario: Inactivos no aparecen (borde)
- **CUANDO** se escribe `gomez` y Ana Gómez está inactiva
- **ENTONCES** el buscador muestra "No se encontraron pacientes"
