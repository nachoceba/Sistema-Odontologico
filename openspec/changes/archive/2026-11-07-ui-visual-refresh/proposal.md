# Proposal: ui-visual-refresh (C-14)

> **Gobernanza MEDIA** (toca la apariencia de todas las pantallas y la barra de navegación que ven los tres roles, sin tocar comportamiento, permisos ni backend). En `design.md`, las decisiones P-1 a P-11 están **CONFIRMADAS POR EL USUARIO**: P-2 (Stitch como MCP de diseño), P-6 (sin modo oscuro) y P-10 (paleta nueva en verdes y verde agua) con la opción elegida por él, y las demás con la opción A (recomendada).

## Why

Las pantallas de C-03 a C-10 funcionan, pero se armaron de a una: `styles.css` repite colores sueltos y reglas duplicadas, el contorno de foco (1,95:1) y el borde de los campos (2,92:1) no llegan al contraste mínimo de WCAG 2.2 AA para elementos que no son texto (3:1), la barra de navegación solo está en `/agenda` y las tablas no tienen arreglo para pantallas angostas. Con el roadmap funcional archivado (C-13), es el momento de ordenar la capa visual antes de la prueba con una recepcionista real (R-8), sin sumar funciones.

## What Changes

- **Identidad nueva, minimalista** (P-10): paleta de verdes y verde agua (primario `#0a7368`, secundario `#2a7148`, fondo menta `#f3faf8`, texto `#12302b`), tema claro solo (P-6), clara de entender.
- **Base visual compartida**: tokens de color, tipografía, espacios, radios y sombras como variables CSS en `:root` de `frontend/src/styles.css`; todas las reglas usan tokens. Se quitan las reglas duplicadas (`.hint`, `.dialog`). Sin librerías nuevas.
- **Detalles dentales sutiles**: un diente en SVG en línea como marca discreta en la barra y el login, y en los avisos de carga y de listado vacío, con un pulso suave mientras carga que se apaga con `prefers-reduced-motion`. Decorativo (`aria-hidden`), nunca en tablas, grilla de la agenda ni diálogos.
- **Referencias de diseño en Stitch** (P-2): antes de tocar las pantallas, un proyecto propio "Sistema Odontologico" en Stitch con el sistema de diseño de la paleta y una pantalla de referencia por grupo, con datos ficticios, que el equipo revisa. Son solo referencia: la implementación es a mano en React y CSS, sin importar código generado.
- **Accesibilidad medible**: contraste de texto ≥ 4,5:1 y de foco, bordes de campos y marcas de estado ≥ 3:1, comprobado por un test de Vitest que lee los tokens de `styles.css` con una función propia de contraste (sin dependencias). Objetivos táctiles de al menos 24 × 24 px.
- **Marco común de las pantallas con sesión**: la barra de navegación (`AppNav`) pasa a todas las pantallas con sesión, con el enlace "Agenda" y la página actual marcada (P-5). Los roles ven exactamente los mismos destinos que hoy ("Usuarios" solo administración).
- **Componentes visuales comunes**: botones (principal, secundario, peligro, enlace), campos y formularios, avisos (carga, vacío, error, éxito), tablas con contenedor desplazable en pantallas angostas (P-8), panel lateral y diálogos con el mismo aspecto.
- **Pantalla por pantalla**: login, agenda (barra de herramientas, grilla día y semana, panel de agendar, detalle, cancelar, reprogramar, marcar atención, conflictos), pacientes, profesionales (ficha, horario semanal, licencias) y usuarios, con anchos de 375, 768 y 1280 px.
- **Skill propia `diseno-ui-odontologico`**: se diseña en este change (`docs/skills-mcp/investigacion-diseno-ui.md`) y se crea en el apply, con el método de `skill-creator`.
- **Sin cambios de comportamiento**: mismos textos, mismas acciones por rol, mismos pedidos a la API, mismas rutas. Sin backend, endpoints, migraciones, variables de entorno ni dependencias nuevas. La app no carga fuentes ni recursos externos.

## Capabilities

### New Capabilities
- `frontend-visual-system`: tokens visuales, contraste mínimo, foco visible, tamaño de objetivos, anchos de pantalla sin desplazamiento horizontal, estados de carga, vacío y error con el mismo aspecto, motivo dental decorativo, marco de navegación común en las pantallas con sesión y la garantía de que la mejora visual no cambia textos, acciones por rol ni pedidos a la API.

### Modified Capabilities
- Ninguna. Las specs funcionales (`frontend-auth`, `frontend-agenda`, `frontend-appointment-management`, `frontend-patient-management`, `frontend-professional-schedules`, `frontend-user-management`, `frontend-shell`) siguen valiendo tal cual: este change solo cambia cómo se ven.

## Impact

- **Frontend**: `frontend/src/styles.css` (tokens y reglas), `frontend/src/App.tsx` (marco común de las rutas con sesión), `frontend/src/agenda/AppNav.tsx`, las páginas de `frontend/src/pages/` y los componentes de `agenda/`, `appointments/`, `patients/`, `professionals/` y `users/` solo en su marcado de clases y estructura visual. Módulos nuevos y chicos `frontend/src/ui/contrast.ts` y `frontend/src/ui/ToothMark.tsx` (SVG en línea) con sus tests. No se tocan `api/`, `auth/session.ts`, `actions.ts`, `messages.ts` ni `grid.ts`.
- **Backend**: sin cambios. La suite por defecto, la de integración, el smoke y la matriz ruta × rol (32 rutas) corren como red de seguridad.
- **Tests**: los 392 de Vitest siguen en verde sin cambiar sus aserciones; se suman los de tokens y contraste, marco de navegación y tablas. Verificación visual con el navegador integrado a 375, 768 y 1280 px.
- **Servicio externo**: Stitch (Google), elegido por el usuario con sus riesgos aceptados (cuenta de Google, las descripciones salen a Google, cuotas sin verificar). Solo recibe descripciones con datos ficticios; el proyecto queda en la cuenta del usuario.
- **Docs**: `docs/skills-mcp/investigacion-diseno-ui.md` (nuevo), `CHANGES.md`; en el apply, la skill, `.atl/skill-registry.md`, `CLAUDE.md`/`AGENTS.md` y `README.md`.
- **Fuera de alcance** (no existe en la API): pantalla de configuración del consultorio, listado de recordatorios enviados, historia clínica, portal de pacientes. Siguen abiertos SU-02, el endurecimiento de sesión y login (DD-46, DD-47, DD-112) y la prueba con una recepcionista real (R-8).
