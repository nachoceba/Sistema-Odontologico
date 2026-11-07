# frontend-visual-system Specification

## Purpose
Dar a todas las pantallas del frontend una misma base visual minimalista en verdes y verde agua (tokens, contraste, foco, anchos, estados y un motivo dental discreto), medible y accesible según WCAG 2.2 AA, sin cambiar textos, acciones por rol ni pedidos a la API.

## Requirements

### Requirement: Tokens visuales únicos

Los colores, la tipografía, los espacios, los radios y las sombras del frontend SHALL definirse una sola vez como tokens (variables CSS en la raíz de la hoja de estilos). Fuera de esa definición, la hoja de estilos MUST NOT tener colores escritos a mano (hexadecimales, `rgb()` o nombres de color) y MUST NOT definir dos veces el mismo selector con valores distintos. El frontend MUST NOT cargar tipografías ni hojas de estilo desde servidores externos.

#### Scenario: Color por token (esperado)
- **WHEN** se revisa cualquier regla de la hoja de estilos fuera de la raíz
- **THEN** cada color que usa es una referencia a un token, por ejemplo el botón principal usa el token del color principal

#### Scenario: Color suelto (error)
- **WHEN** una regla fuera de la raíz escribe un color hexadecimal
- **THEN** el test de tokens falla y nombra el selector

#### Scenario: Selector repetido (borde)
- **WHEN** la hoja de estilos define dos veces el mismo selector con propiedades distintas, como hoy `.hint` y `.dialog`
- **THEN** el test de tokens falla

#### Scenario: Sin recursos externos (esperado)
- **WHEN** se abre cualquier pantalla con la app en Docker Compose
- **THEN** ningún pedido de fuentes ni estilos sale a un dominio distinto del frontend y la API

### Requirement: Contraste mínimo (WCAG 2.2 AA, 1.4.3 y 1.4.11)

Todo texto SHALL tener un contraste de al menos 4,5:1 con su fondo (3:1 si es texto grande: 24 px, o 18,66 px en negrita). El contorno de foco, el borde de los campos de formulario y las marcas que distinguen un estado (por ejemplo franja libre, ocupada, licencia, conflicto) MUST tener al menos 3:1 contra los colores que tienen al lado. El contorno de foco MUST ir separado del elemento, de modo que el color que tiene al lado sea el fondo. Todos los pares de tokens de la paleta que se usan juntos (texto/fondo, texto sobre botón, estado sobre su fondo suave, foco y borde de campo sobre fondo) MUST figurar en una lista verificada por un test. La paleta MUST ser de tema claro, en verdes y verde agua, sin modo oscuro.

#### Scenario: Texto común (esperado)
- **WHEN** se mide el texto principal `#12302b` sobre el fondo de la página `#f3faf8`
- **THEN** el contraste es de al menos 4,5:1 (13,38:1)

#### Scenario: Botón principal verde agua (esperado)
- **WHEN** se mide el texto blanco sobre el color principal `#0a7368`
- **THEN** el contraste es de al menos 4,5:1 (5,73:1)

#### Scenario: Estados sobre su fondo suave (esperado)
- **WHEN** se miden éxito, error, aviso y pendiente sobre su fondo suave
- **THEN** cada par da al menos 4,5:1

#### Scenario: Par de la paleta que no cumple (error)
- **WHEN** alguien cambia un token y un par de la lista queda por debajo de su mínimo, por ejemplo el verde secundario `#2f7d4f` sobre su fondo suave `#e6f4ea` (4,44:1)
- **THEN** el test de contraste falla y nombra los dos tokens

#### Scenario: Foco hoy insuficiente (error que este change corrige)
- **WHEN** se mide el contorno de foco actual `#f0a500` sobre el fondo `#f5f8fa`
- **THEN** da 1,95:1, por debajo de 3:1, y el test de contraste lo rechaza; el token nuevo de foco da al menos 3:1 sobre el fondo de la página y sobre el blanco de paneles y tarjetas, y va separado del botón

#### Scenario: Borde de campo hoy insuficiente (borde)
- **WHEN** se mide el borde de campo actual `#8a99a6` sobre blanco
- **THEN** da 2,92:1 y el test lo rechaza; el token nuevo de borde de campo da al menos 3:1

#### Scenario: Estado que no depende solo del color (esperado)
- **WHEN** una franja de la agenda está libre, ocupada o fuera de horario, o un turno está cancelado o en conflicto
- **THEN** además del color se distingue por su texto ("Libre", "Ocupado", la etiqueta de estado o de conflicto), como hoy

### Requirement: Foco visible y uso con teclado (WCAG 2.4.7, 2.4.11 y 2.1.1)

Todo elemento interactivo SHALL mostrar un foco visible cuando se llega con el teclado, sin quedar tapado por la barra, el panel lateral ni un diálogo. Cada pantalla con sesión MUST ofrecer como primer elemento enfocable un enlace "Saltar al contenido" que lleva al contenido principal. El orden del foco MUST seguir el orden visual. Los diálogos MUST conservar lo que ya hacen (foco inicial en la opción segura y Escape cierra) y MUST mantener el foco dentro del diálogo mientras está abierto (P-11).

#### Scenario: Recorrido con Tab (esperado)
- **WHEN** recepción abre `/agenda` y aprieta Tab varias veces
- **THEN** el foco pasa por "Saltar al contenido", la barra de navegación, la barra de herramientas de la agenda y la grilla, en ese orden, y cada paso tiene un contorno visible

#### Scenario: Saltar al contenido (esperado)
- **WHEN** la persona activa "Saltar al contenido"
- **THEN** el foco queda en el contenido principal de la pantalla, después de la barra de navegación

#### Scenario: Diálogo abierto (borde)
- **WHEN** está abierto el diálogo "Cancelar turno" y la persona aprieta Tab desde el último botón
- **THEN** el foco vuelve al primer elemento del diálogo y no pasa a la grilla de atrás

#### Scenario: Escape en un diálogo (esperado)
- **WHEN** está abierto un diálogo de confirmación y la persona aprieta Escape
- **THEN** el diálogo se cierra sin confirmar, igual que hoy

### Requirement: Tamaño mínimo de los objetivos (WCAG 2.5.8)

Todo botón, enlace de acción y control de formulario SHALL ocupar al menos 24 × 24 px CSS, incluidos los botones chicos de la grilla ("Agendar" en una franja y el botón de cada turno).

#### Scenario: Botón de la grilla (esperado)
- **WHEN** se mide el botón "Agendar" de una franja libre a 375 px de ancho
- **THEN** mide al menos 24 px de alto y 24 px de ancho

#### Scenario: Enlace dentro de un texto (borde)
- **WHEN** un enlace está dentro de una oración, como "Volver a la agenda" en el aviso de permiso
- **THEN** queda exceptuado del tamaño mínimo, como permite WCAG 2.5.8

### Requirement: Pantallas usables a 375, 768 y 1280 px (WCAG 1.4.10)

Cada pantalla SHALL verse y usarse completa a 375, 768 y 1280 px de ancho, sin desplazamiento horizontal de la página. Las tablas de pacientes, profesionales y usuarios MUST desplazarse dentro de su propio contenedor, que tiene nombre accesible y se puede enfocar con el teclado (P-8). El panel lateral MUST ocupar todo el ancho en pantallas angostas, como hoy. Con el zoom del navegador al 200 % a 1280 px el contenido MUST seguir completo.

#### Scenario: Tabla en un teléfono (esperado)
- **WHEN** administración abre `/usuarios` a 375 px
- **THEN** la página no se desplaza a lo ancho, la tabla se desplaza dentro de su contenedor y todos los botones de cada fila se pueden alcanzar

#### Scenario: Semana en una tableta (esperado)
- **WHEN** recepción abre la vista "Semana" a 768 px
- **THEN** los días se acomodan en columnas sin cortar texto ni salir de la pantalla

#### Scenario: Panel lateral angosto (borde)
- **WHEN** recepción abre "Agendar" desde una franja a 375 px
- **THEN** el panel ocupa todo el ancho y su botón "Agendar turno" se ve sin desplazar a lo ancho

### Requirement: Estados de carga, vacío, error y éxito con el mismo aspecto

Los avisos de carga, de listado vacío, de error y de éxito SHALL verse igual en todas las pantallas (mismo componente visual por tipo de aviso) y MUST conservar los textos exactos y los roles accesibles que ya fijan las specs funcionales (`role="status"` para carga, vacío y éxito; `role="alert"` para errores). El color MUST NOT ser la única diferencia entre un error y un éxito.

#### Scenario: Carga (esperado)
- **WHEN** `/pacientes` espera la respuesta del listado
- **THEN** se ve "Cargando…" con el aspecto común de carga y con `role="status"`

#### Scenario: Listado vacío (esperado)
- **WHEN** la búsqueda de pacientes no encuentra resultados
- **THEN** se ve el mismo texto de vacío que hoy, con el aspecto común de vacío

#### Scenario: Error del servidor (error)
- **WHEN** la API no responde al abrir `/profesionales`
- **THEN** se ve el mismo mensaje de error que hoy, con `role="alert"`, un borde o ícono además del color y el aspecto común de error

#### Scenario: Éxito tras una acción (esperado)
- **WHEN** recepción agenda un turno y la API responde 201
- **THEN** el aviso de éxito conserva su texto y se distingue del de error por algo más que el color

### Requirement: Motivo dental decorativo y discreto

El frontend SHALL mostrar un diente simple como marca discreta en la barra de navegación y en la pantalla de login, y como ícono en los avisos de carga y de listado vacío. El motivo MUST ser un gráfico vectorial en línea, sin imágenes externas ni librerías nuevas, MUST estar oculto para lectores de pantalla (`aria-hidden="true"`) y MUST NOT recibir foco. MUST NOT aparecer dentro de tablas, de la grilla de la agenda ni de diálogos. Mientras se carga, el diente SHALL tener un pulso o brillo suave; con `prefers-reduced-motion: reduce` MUST quedar quieto. Los textos y roles accesibles de la barra, el login y los avisos MUST ser los mismos que sin el motivo.

#### Scenario: Marca en la barra (esperado)
- **WHEN** recepción abre `/agenda`
- **THEN** la barra muestra el diente junto al nombre del sistema, el diente tiene `aria-hidden="true"` y no aparece en el árbol de accesibilidad

#### Scenario: Carga con pulso (esperado)
- **WHEN** `/pacientes` espera el listado
- **THEN** el aviso "Cargando…" conserva `role="status"` y su texto, y el diente tiene la animación suave

#### Scenario: Movimiento reducido (borde)
- **WHEN** el sistema operativo pide reducir el movimiento y una pantalla está cargando
- **THEN** el diente se ve quieto, sin animación

#### Scenario: Agenda densa (borde)
- **WHEN** se muestra la grilla de la semana con turnos
- **THEN** no hay ningún diente dentro de la grilla ni de las tablas

#### Scenario: Sin foco ni texto extra (error que se evita)
- **WHEN** se recorre el login con Tab o se lee con un lector de pantalla
- **THEN** el diente no recibe foco ni agrega texto; el nombre accesible del formulario y del botón "Ingresar" no cambia

### Requirement: Marco de navegación común en las pantallas con sesión (P-5)

Toda pantalla con sesión (`/agenda`, `/pacientes`, `/profesionales`, `/usuarios` y el aviso de permiso) SHALL mostrar la misma barra de navegación con el nombre y el rol de la cuenta, los enlaces "Agenda", "Pacientes", "Profesionales", "Usuarios" (solo administración) y "Salir". El enlace de la pantalla actual MUST marcarse con `aria-current="page"` y un estilo visible. La pantalla de login MUST NOT mostrar la barra. Los destinos que ve cada rol MUST ser los mismos que hoy.

#### Scenario: Administración (esperado)
- **WHEN** el administrador abre `/pacientes`
- **THEN** ve la barra con "Agenda", "Pacientes" (marcado como actual), "Profesionales", "Usuarios" y "Salir"

#### Scenario: Recepción y odontología (esperado)
- **WHEN** recepción o un odontólogo abre `/profesionales`
- **THEN** ve la barra sin "Usuarios", con "Profesionales" marcado como actual

#### Scenario: Aviso de permiso (error)
- **WHEN** recepción escribe `/usuarios` en la dirección
- **THEN** ve la barra común y el aviso "No tenés permiso para esta acción" con el enlace a `/agenda`, sin pedir el listado a la API y sin perder la sesión, igual que hoy

#### Scenario: Login (borde)
- **WHEN** alguien sin sesión abre `/login`
- **THEN** no ve la barra de navegación

### Requirement: La mejora visual no cambia comportamiento ni permisos

El change SHALL limitarse a la presentación. Para cada rol, cada pantalla MUST mostrar los mismos textos, campos, botones y acciones que antes, MUST hacer los mismos pedidos a la API con el mismo método, ruta y cuerpo, y MUST conservar las rutas del frontend. Las pruebas previas del frontend MUST seguir pasando sin cambiar lo que comprueban; las suites del backend, el smoke de punta a punta y la matriz ruta × rol MUST seguir en verde. El movimiento MUST respetar `prefers-reduced-motion`.

#### Scenario: Mismas acciones por rol (esperado)
- **WHEN** un odontólogo abre un turno propio ya iniciado en `/agenda`
- **THEN** ve solo "Marcar atendido" y "Marcar ausente", igual que antes del change

#### Scenario: Mismos pedidos (esperado)
- **WHEN** recepción cancela un turno con motivo
- **THEN** el frontend envía el mismo `POST /api/v1/appointments/{id}/cancel` con el mismo cuerpo que antes

#### Scenario: Tests previos (esperado)
- **WHEN** se corre la suite de Vitest al terminar el change
- **THEN** pasan los 392 tests previos sin cambios en sus aserciones, más los nuevos

#### Scenario: Movimiento reducido (borde)
- **WHEN** el sistema operativo pide reducir el movimiento y se abre el panel lateral
- **THEN** el panel aparece sin animación, como hoy
