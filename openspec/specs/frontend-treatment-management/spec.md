# frontend-treatment-management Specification

## Purpose
Dar al administrador una pantalla simple para mantener el catálogo de tratamientos y marcar qué tratamientos ofrece cada profesional, con el estilo y la accesibilidad del resto de la app (C-14).

## Requirements

### Requirement: Pantalla de tratamientos solo para administración

La app SHALL tener la pantalla `/tratamientos`, con el enlace "Tratamientos" en la barra, solo para el rol `admin`. Otro rol que abra la dirección MUST ver la misma pantalla de acceso denegado que en `/usuarios`, y la barra MUST NOT mostrarle el enlace.

#### Scenario: Administrador (esperado)
- **WHEN** el administrador inicia sesión
- **THEN** ve el enlace "Tratamientos" y la pantalla lista el catálogo

#### Scenario: Recepción abre la dirección (error de negocio)
- **WHEN** la recepcionista abre `/tratamientos`
- **THEN** no ve el catálogo ni el enlace en la barra

### Requirement: Mantener el catálogo

La pantalla SHALL listar los tratamientos por nombre, con su estado ("Activo" o "Inactivo"), y permitir agregar uno con un campo "Nombre", cambiarle el nombre y activarlo o desactivarlo. Desactivar MUST pedir confirmación con el texto "Los turnos que ya lo tienen no cambian. No se va a poder elegir en turnos nuevos.". La pantalla MUST mostrar los estados de carga, vacío ("Todavía no hay tratamientos.") y error con reintento, y el mensaje "Ya existe un tratamiento con ese nombre." ante `TREATMENT_NAME_TAKEN`. Un doble clic en guardar MUST mandar un solo pedido.

#### Scenario: Agregar (esperado)
- **WHEN** el administrador escribe "Tratamiento de conducto" y guarda
- **THEN** aparece en la lista como activo, en su lugar alfabético

#### Scenario: Nombre repetido (error de negocio)
- **WHEN** guarda un nombre que ya existe
- **THEN** ve "Ya existe un tratamiento con ese nombre." y la lista no cambia

#### Scenario: Desactivar con confirmación (esperado)
- **WHEN** toca "Desactivar" en "Blanqueamiento" y confirma
- **THEN** el tratamiento queda "Inactivo" y puede volver a activarlo

#### Scenario: Catálogo vacío (borde)
- **WHEN** no hay ningún tratamiento
- **THEN** ve "Todavía no hay tratamientos." y el formulario para agregar

### Requirement: Tratamientos que ofrece cada profesional en su ficha

En la pantalla de profesionales, la ficha de cada profesional SHALL tener la sección "Tratamientos que ofrece". El administrador la ve como una lista de casillas con todo el catálogo (los inactivos marcados como "Inactivo") y un botón "Guardar tratamientos" que reemplaza la asignación. La recepción y el odontólogo (este solo en su ficha) la ven como lista de solo lectura de los tratamientos asignados. Si el profesional no tiene ninguno activo, la sección MUST mostrar "Sin tratamientos activos: no se le pueden dar turnos nuevos.".

#### Scenario: Asignar desde la ficha (esperado)
- **WHEN** el administrador marca "Extracción" en la ficha del Dr. B y guarda
- **THEN** la ficha muestra la asignación nueva y el panel de agendar del Dr. B ofrece "Extracción"

#### Scenario: Solo lectura para recepción (esperado)
- **WHEN** la recepcionista abre la ficha de la Dra. A
- **THEN** ve la lista de tratamientos sin casillas ni botón de guardar

#### Scenario: Profesional sin tratamientos activos (borde)
- **WHEN** el Dr. B no tiene ningún tratamiento activo asignado
- **THEN** la sección muestra el aviso de que no se le pueden dar turnos nuevos

### Requirement: Revisión visual de las pantallas nuevas

La pantalla `/tratamientos` y la sección de la ficha SHALL cumplir los criterios C-1 a C-6, C-8 y C-9 de la capa visual (C-14): tokens de color existentes, contraste AA, objetivos de al menos 24 px, foco visible, uso completo con teclado, estados de carga, vacío y error, sin dependencias nuevas, sin el motivo dental en listas ni diálogos y sin desplazamiento horizontal a 375, 768 y 1280 px. Lo mismo vale para el selector de tratamiento del panel de agendar y de `/turnos`.

#### Scenario: Ancho de teléfono (borde)
- **WHEN** se abre `/tratamientos` a 375 px
- **THEN** no hay desplazamiento horizontal y cada control se alcanza con Tab
