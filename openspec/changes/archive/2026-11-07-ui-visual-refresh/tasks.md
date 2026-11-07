# Tasks: ui-visual-refresh (C-14)

> **Gobernanza MEDIA.** Las decisiones P-1 a P-11 están **CONFIRMADAS POR EL USUARIO**: P-2 (Stitch), P-6 (sin modo oscuro) y P-10 (paleta verde y verde agua) con su opción elegida, y las demás con la opción A (recomendada). Implementar con checkpoints al final de cada grupo y mostrar las decisiones no obvias. Modo TDD estricto: en cada task de código, primero el test que falla (RED, se ejecuta y se ve fallar), después el mínimo código (GREEN), un segundo caso (TRIANGULATE) y el refactor con los tests en verde (REFACTOR). Antes de tocar un archivo existente, safety net con sus tests. Solo frontend: el backend no se toca y su suite corre como red. TypeScript estricto sin `any`. Sin dependencias, variables de entorno ni recursos externos nuevos; el código que genere Stitch no se importa. Las clases `appointment--cancelled` y `day-column--today` se conservan. No leer ni editar `.env`; nunca escribir ni mostrar contraseñas. Sin commits ni push sin pedido explícito, y sin `Co-Authored-By`.

## 0. Decisiones

- [x] 0.1 Registrar en `design.md` P-2 = B (Stitch), P-6 = A (sin modo oscuro) y P-10 = B (paleta nueva) como CONFIRMADAS POR EL USUARIO, con las reglas de D-9 y los tokens de D-1
- [x] 0.2 Obtener respuesta del equipo a P-1, P-3, P-4, P-5, P-7, P-8, P-9 y P-11 y marcarlas CONFIRMADAS; si P-1 = B o C, partir el change con `/opsx:update`; si P-3 = B, sumar la dependencia con la autorización escrita de la licencia; si P-5 = B, quitar el requirement "Marco de navegación común" y las tasks 5.1 y 5.2; si P-8 = B, ajustar el requirement de anchos; si P-11 = B, quitar el escenario "Diálogo abierto"
- [x] 0.3 Registrar las decisiones como DD-117 en adelante en `knowledge-base/09_decisiones_y_supuestos.md` y verificar `openspec validate ui-visual-refresh --strict` en verde

## 1. Preparación y safety net

- [x] 1.1 Safety net: en el contenedor `pytest`, `pytest -m integration`, `pytest -m smoke`, `mypy --strict app/` y `ruff check`; en el frontend `npm test`, `npm run typecheck`, `npm run lint`, `npm run build` y `npm run check:bundle`; anotar los números (C-13 dejó 1713 por defecto, 331 de integración, 6 de smoke y 392 de frontend); si algo falla, frenar y reportarlo como falla previa
- [ ] 1.2 Con la app levantada, el usuario inicia sesión en el navegador integrado con cada rol del seed; recorrer con `mcp__Claude_Browser__resize_window` y `computer` `screenshot` las 13 pantallas del inventario a 375, 768 y 1280 px y anotar el estado inicial en `docs/skills-mcp/evidencias/ui-visual-refresh.md` (sección "Antes"); las capturas se guardan en `docs/` solo si el usuario lo aprueba

## 2. Skill propia `diseno-ui-odontologico`

- [x] 2.1 Leer `skill-creator` y escribir `.claude/skills/diseno-ui-odontologico/SKILL.md` con el diseño de `docs/skills-mcp/investigacion-diseno-ui.md` §4 (propósito, cuándo se activa, entradas, procedimiento, criterios C-1 a C-10, formato de respuesta, cómo revisar el resultado, límites), con el formato de `revisor-escenarios-turnos`; verificar que el archivo existe y que su `description` nombra los disparadores
- [x] 2.2 Correr los cuatro casos de prueba de la ficha (§4) en una sesión nueva y anotar el resultado de cada uno en la evidencia; verificar que el caso 1 encuentra el foco y el borde de campo, el 2 no cambia textos ni acciones por rol, el 3 frena por C-8 y el 4 marca un diente animado sin `prefers-reduced-motion` o dentro de la grilla por C-9
- [x] 2.3 Registrar la skill en `.atl/skill-registry.md` y verificar que aparece en la sesión

## 3. Referencias de diseño en Stitch (antes de tocar pantallas, D-9)

- [x] 3.1 Crear el proyecto propio con `create_project` (`title: "Sistema Odontologico"`) y anotar su `projectId` en la evidencia; verificar con `get_project` que el título es el esperado. No listar, abrir ni tocar ningún otro proyecto de la cuenta
- [x] 3.2 Crear el sistema de diseño con `create_design_system` y enseguida `update_design_system`, con los valores de D-9 (tema claro, primario `#0a7368`, secundario `#2a7148`, neutro `#f3faf8`, `ROUND_EIGHT`, `designMd` con las reglas de minimalismo y motivo dental sutil); verificar con `list_design_systems` del proyecto propio que existe
- [ ] 3.3 Generar con `generate_screen_from_text` una pantalla de referencia por grupo (login; agenda día y semana; detalle y diálogos de turno; pacientes; profesionales; usuarios), con el sistema de diseño de 3.2 y datos ficticios del seed; las descripciones no llevan código, rutas internas, claves ni datos reales; verificar con `list_screens` que están las seis
- [ ] 3.4 Revisión del equipo: ver cada referencia con `get_screen` y `download_file` (la imagen; el HTML no se usa), comparar con el inventario y con las specs funcionales (lo que la API no tiene se descarta) y aplicar ajustes con `edit_screens`; anotar en la evidencia el título del proyecto, la lista de pantallas y lo decidido. Las capturas se guardan en `docs/skills-mcp/evidencias/` solo si el usuario lo aprueba

## 4. Tokens y contraste — spec frontend-visual-system

- [x] 4.1 RED: `frontend/src/ui/contrast.test.ts` con casos conocidos: negro sobre blanco 21:1, blanco sobre blanco 1:1, blanco sobre `#0a7368` 5,73:1 (dos decimales), `#f0a500` sobre `#f5f8fa` 1,95:1; ver que fallan
- [x] 4.2 GREEN → TRIANGULATE → REFACTOR: `contrastRatio` en `frontend/src/ui/contrast.ts` (D-2); triangular con hexadecimales de 3 dígitos y en mayúsculas; verificar 4.1, `typecheck` y `lint` en verde
- [x] 4.3 RED: `frontend/src/ui/tokens.test.ts` que lee `styles.css`: falla si falta algún token de la tabla de D-1, si un par de la lista no llega a su mínimo (texto 4,5; foco, borde de campo y marcas de estado 3; todos los pares de la tabla de D-1), si hay colores sueltos fuera de `:root` o si un selector se define dos veces; triangular con un par que falla a propósito (`#2f7d4f` sobre `#e6f4ea`, 4,44:1) y ver que el mensaje nombra los dos tokens; ver que falla con la hoja actual
- [x] 4.4 GREEN → REFACTOR: safety net de toda la suite; reescribir `styles.css` con los tokens de D-1 en `:root` (paleta verde y verde agua, tema claro), reemplazar cada color suelto por su token, unir `.hint` y `.dialog`, contorno de foco de 3 px separado 2 px; verificar 4.3 y los 392 tests previos en verde sin tocar sus aserciones, `build` y `check:bundle`

## 5. Marco común, componentes visuales y motivo dental — spec frontend-visual-system

- [x] 5.1 Safety net de `App.test.tsx`, `agenda/access.test.tsx`, `users/access.test.tsx`, `patients/access.test.tsx` y `professionals/access.test.tsx`; RED: `frontend/src/layout.test.tsx` con `renderApp`: admin en `/pacientes` ve "Agenda", "Pacientes" (con `aria-current="page"`), "Profesionales", "Usuarios" y "Salir"; recepción y odontólogo en `/profesionales` no ven "Usuarios"; `/login` sin barra; el primer Tab llega a "Saltar al contenido" y al activarlo el foco queda en `main`; recepción en `/usuarios` ve la barra y el aviso con "Volver a la agenda" sin pedir `/users`; ver que fallan
- [x] 5.2 GREEN → TRIANGULATE → REFACTOR: marco `AppLayout` en `App.tsx` y `AppNav` con "Agenda" y `aria-current` (D-3, P-5); las páginas dejan su `AppNav` y su `<main>` propios y quitan el "Volver a la agenda" del encabezado; verificar 5.1 y la red en verde
- [x] 5.3 RED: `frontend/src/ui/ToothMark.test.tsx`: el SVG tiene `aria-hidden="true"` y `focusable="false"`, no agrega nombre accesible ni rol; en la barra y en el login el nombre del formulario, de los enlaces y del botón "Ingresar" no cambia; el aviso "Cargando…" conserva `role="status"` y su texto; con la grilla de la semana y las tablas montadas no hay ningún diente adentro; y un test que lee `styles.css` comprueba que la animación del diente existe y que `@media (prefers-reduced-motion: reduce)` la deja en `animation: none`; ver que fallan
- [x] 5.4 GREEN → TRIANGULATE → REFACTOR: `ToothMark` (SVG en línea, D-10) en la barra, el login y los avisos de carga y vacío; pulso suave en CSS con tokens; triangular con un aviso vacío de pacientes y con el aviso de carga de profesionales; verificar 5.3 y toda la suite en verde
- [x] 5.5 RED: en `frontend/src/appointments/cancel.test.tsx` y `frontend/src/patients/status.test.tsx`, con el diálogo abierto, Tab desde el último botón vuelve al primero, Shift+Tab desde el primero va al último y al cerrar el foco vuelve al botón que lo abrió; ver que fallan (P-11)
- [x] 5.6 GREEN → TRIANGULATE → REFACTOR: base común de diálogo usada por `Modal` y `ConfirmDialog`, conservando foco inicial y Escape; triangular con `RescheduleDialog` y la confirmación de asistencia; verificar 5.5 y `appointments/` y `patients/` en verde
- [x] 5.7 RED: tests de tablas en `pages/UsersPage.test.tsx` y `patients/search.test.tsx`: la tabla está dentro de una región con nombre ("Usuarios", "Pacientes") enfocable; ver que fallan (P-8)
- [x] 5.8 GREEN → REFACTOR: contenedor `.table-scroll` y clase `data-table` en usuarios, pacientes y profesionales; clases comunes de botones, campos y avisos (D-4); verificar 5.7 y toda la suite en verde
- [x] 5.9 Checkpoint visual con el navegador integrado, comparando con las referencias de Stitch del grupo 3: login, aviso de permiso y barra en las cuatro pantallas a 375, 768 y 1280 px, recorrido con Tab, color del foco medido con `javascript_tool` (color calculado) y ≥ 3:1, diente quieto con movimiento reducido; anotar en la evidencia (sección "Base")

**Punto de corte seguro**: con los grupos 1 a 5 en verde la app ya queda consistente y accesible con la identidad nueva; los grupos 6 a 8 se pueden hacer en otra sesión sin dejar nada a medias.

## 6. Agenda y gestión de turnos — specs frontend-visual-system, frontend-agenda y frontend-appointment-management (sin cambios de comportamiento)

- [x] 6.1 Safety net de `agenda/` y `appointments/`; RED: en `agenda/day.test.tsx` los botones "Agendar" y de turno llevan la clase de objetivo mínimo; ver que falla
- [x] 6.2 GREEN → REFACTOR: tomando la referencia de Stitch de agenda y de diálogos, barra de herramientas agrupada (fecha, vista, profesional), grilla día y semana, etiquetas de estado y conflicto, panel lateral, detalle, diálogos de cancelar y reprogramar, panel de conflictos con avisos diferenciados por tipo (D-5); verificar `agenda/` y `appointments/` en verde con las mismas aserciones
- [x] 6.3 Revisión con la skill `diseno-ui-odontologico` y el navegador integrado a 375, 768 y 1280 px con recepción y con un odontólogo: botones de la grilla ≥ 24 × 24 px medidos, semana sin desplazamiento horizontal, panel lateral a todo el ancho en 375 px, ningún diente en la grilla, mismas acciones por rol que antes; anotar hallazgos y su arreglo en la evidencia (sección "Agenda")

## 7. Pacientes, profesionales y usuarios — specs frontend-visual-system y las funcionales de cada pantalla (sin cambios de comportamiento)

- [x] 7.1 Safety net de `patients/`, `professionals/` y `pages/UsersPage.test.tsx`; GREEN → REFACTOR: tomando las referencias de Stitch, búsqueda, formularios, editor semanal, licencias, ficha y tablas con los componentes comunes (D-4, D-5), estilo para `patient-search`; verificar las tres suites en verde con las mismas aserciones
- [x] 7.2 Revisión con la skill y el navegador integrado a 375, 768 y 1280 px con administración, recepción y un odontólogo: tablas desplazables dentro de su región sin desplazar la página, carga y vacío con el diente y los mismos textos, error con el aspecto común, controles de escritura iguales por rol; anotar en la evidencia (sección "Catálogos")

## 8. Verificación integral

- [x] 8.1 Frontend: `npm test` (392 previos más los nuevos, todos en verde), `npm run typecheck`, `npm run lint`, `npm run build` y `npm run check:bundle` sin hallazgos
- [x] 8.2 Backend sin cambios: en el contenedor `pytest`, `pytest -m integration`, `docker compose exec api pytest -m smoke` (6 en verde), `mypy --strict app/` y `ruff check`; la matriz ruta × rol sigue con 32 rutas
- [x] 8.3 Con el navegador integrado, `read_network_requests` en cada pantalla: ningún pedido a dominios externos (ni fuentes ni imágenes) y los mismos pedidos a la API que en el grupo 1
- [x] 8.4 `openspec validate ui-visual-refresh --strict` en verde

## 9. Sincronización de docs

- [x] 9.1 `CHANGES.md`: estado de C-14 con números de tests y decisiones; árbol y tabla resumen
- [x] 9.2 `CLAUDE.md` y `AGENTS.md` iguales: 14 changes, sección de la skill `diseno-ui-odontologico` (cuándo usarla, qué necesita, cómo revisar el resultado, límites), del navegador integrado como herramienta de revisión y de Stitch como integración MCP externa (propósito, herramientas que se usan, reglas de datos, cómo revisar el resultado)
- [x] 9.3 `README.md`: cómo revisar la capa visual (tests de contraste, lista de verificación y referencias de Stitch); `docs/skills-mcp/investigacion-diseno-ui.md` con lo que se resolvió en el apply
- [x] 9.4 `knowledge-base/09_decisiones_y_supuestos.md`: DD nuevas confirmadas; verificar que los códigos citados en `CHANGES.md` existen
