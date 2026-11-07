# Ficha de investigación: skill de diseño y MCP de diseño para la capa visual

Metodología I, TUP. Integrante: Ceballos (trabajo individual). Fecha de consulta de las fuentes: 2026-11-07.

## 1. Necesidad detectada

Las pantallas de C-03 a C-10 funcionan y tienen 392 tests de frontend, pero se fueron armando de a una y se nota:

- `frontend/src/styles.css` (505 líneas) repite colores sueltos en lugar de variables: el mismo azul `#0b6e8a` aparece en botones, enlaces, bordes y el día de hoy, y hay reglas duplicadas (`.hint` y `.dialog` se definen dos veces con valores distintos).
- Dos contrastes no llegan al mínimo de WCAG 2.2 AA para elementos que no son texto (3:1): el contorno de foco `#f0a500` sobre el fondo `#f5f8fa` da 1,95:1, y el borde de los campos `#8a99a6` sobre blanco da 2,92:1. Los textos sí cumplen (el más bajo, `#6b7780` sobre blanco, da 4,59:1).
- La barra de navegación (`AppNav`) solo está en `/agenda`; `/pacientes`, `/profesionales` y `/usuarios` tienen un enlace suelto "Volver a la agenda" y no muestran la cuenta ni el botón "Salir".
- Las tablas de pacientes, profesionales y usuarios usan la clase `users-table` y no tienen contenedor para pantallas angostas.
- La pantalla de login es un formulario sin jerarquía visual (captura con el navegador integrado, 2026-11-07).

La revisión visual hoy se hace "a ojo" y cambia en cada change. Hace falta un criterio fijo (contraste, tokens, anchos, estados) y una herramienta para verlo en la app real.

Las dos incorporaciones son herramientas de desarrollo para el agente. No forman parte del producto.

## 2. Change elegido

**C-14 `ui-visual-refresh`**: mejora visual de las pantallas que ya existen (login, agenda con sus paneles y diálogos, pacientes, profesionales y usuarios), sin cambiar comportamiento, permisos ni backend. Detalle en `openspec/changes/ui-visual-refresh/`.

## 3. Skills de diseño: fuentes contrastadas

| | `frontend-design` (Anthropic) | Impeccable (Paul Bakaus) |
|---|---|---|
| Qué es | Una skill (un `SKILL.md` de 71 líneas) con criterios de dirección visual: anclar el diseño en el tema, elegir tipografía con intención, evitar los rasgos típicos de lo generado por IA, planear tokens antes de escribir y revisar con capturas | Un conjunto de skill y CLI: 24 comandos (`init`, `shape`, `critique`, `audit`, `polish`, `harden`, `adapt`, `typeset`, `colorize`, `layout`, `distill`, `clarify`, `quieter`, `bolder`, `animate`, `delight`, `overdrive`, `optimize`, `onboard`, `live`, `generate`, `document`, `extract` y `craft`, este último obsoleto) y un detector de 62 reglas sin modelo de IA (`npx impeccable detect src/`) |
| Origen | Plugin oficial `frontend-design` 1.1.1 del marketplace `claude-plugins-official`, autor Anthropic | Repositorio `pbakaus/impeccable`; se declara construido a partir de `frontend-design` |
| Licencia | Apache 2.0 (verificado en el `LICENSE` instalado) | Apache 2.0 (verificado en el README del repositorio) |
| Instalación en Claude Code | Ya instalada en esta sesión (`frontend-design:frontend-design`) | `/plugin marketplace add pbakaus/impeccable` o `npx impeccable install` |
| Red y cuentas | Ninguna | No pide cuenta ni clave. Pero al empezar un diseño nuevo consulta el catálogo de `impeccable.style` aunque se apague la telemetría, y trae telemetría que hay que desactivar (`npx impeccable telemetry off` o `DO_NOT_TRACK=1`); el motor se descarga a `~/.impeccable/bin/` |
| Encaje con el proyecto | Sirve como criterio estético; está pensada para diseños nuevos y "distintivos", más que para pulir una app de gestión existente | Su `audit` y su detector se parecen a lo que hace falta, pero suma una dependencia nueva, una página externa y telemetría |

Contraste de fuentes: para `frontend-design` se leyó el `SKILL.md` instalado y su `plugin.json`; el repositorio público `anthropics/claude-plugins-official` es la fuente original (no se volvió a descargar). Para Impeccable se leyó el README del repositorio oficial y se comparó con dos descripciones de terceros (emelia.io y open-design.ai), que coinciden en autor, licencia y forma de instalación pero no en la cantidad de comandos (23 contra 24) ni de estrellas; vale lo del repositorio. **Sin verificar**: qué datos manda exactamente Impeccable a `impeccable.style` y qué recolecta su telemetría (el README no lo detalla).

**Conclusión**: no se instala Impeccable (página externa y telemetría, contra la regla de mantener todo local y simple). Se usa `frontend-design` como criterio de fondo y se crea una skill propia, chica y específica del proyecto (sección 4), que toma de Impeccable la idea de una revisión con reglas fijas y repetibles.

**Herramientas de accesibilidad automáticas** (licencias consultadas en el registro de npm el 2026-11-07): `axe-core` 4.14.0 es MPL-2.0, `vitest-axe` 0.1.0 y `jest-axe` 11.0.0 son MIT pero dependen de `axe-core`, `pa11y` 10.0.0 es LGPL-3.0 y `playwright` 1.65.0 es Apache 2.0 (pesada: descarga navegadores). MPL y LGPL no son MIT, Apache ni BSD, así que quedan fuera de la directiva del proyecto salvo que el usuario lo autorice (P-3 del change). La alternativa es una función propia de contraste (fórmula de WCAG, unas 20 líneas) con sus tests en Vitest.

## 4. Diseño de la skill propia (método `skill-creator`)

Se diseña con el método de `skill-creator` (capturar la intención, entrevistar, escribir el `SKILL.md`, casos de prueba y evaluación). **No se crea en esta etapa**: el archivo `.claude/skills/diseno-ui-odontologico/SKILL.md` se escribe en el apply de C-14. Formato tomado de `.claude/skills/revisor-escenarios-turnos/SKILL.md`.

| Campo | Definición |
|---|---|
| Nombre | `diseno-ui-odontologico` |
| Propósito | Guiar y revisar cambios visuales del frontend con criterios fijos del proyecto: tokens, contraste WCAG 2.2 AA, anchos, estados y foco, sin cambiar comportamiento |
| Cuándo se activa | Al proponer, implementar o revisar un cambio en `frontend/src/**/*.tsx` o `styles.css` que afecte cómo se ve una pantalla (C-14 y changes visuales posteriores), o cuando se pida "revisá cómo se ve", "mejorá el diseño", "chequeá el contraste" |
| Entradas | La pantalla o el componente a revisar; leídos en el momento: `frontend/src/styles.css` (tokens en `:root`), la spec `frontend-visual-system`, la spec funcional de la pantalla (`openspec/specs/frontend-*/spec.md`) y `03_actores_y_roles.md` para saber qué ve cada rol |
| Procedimiento | 1) Listar la pantalla, los roles que la usan y sus estados (carga, vacío, error, éxito). 2) Revisar el código: colores y medidas solo por tokens, sin colores sueltos. 3) Calcular el contraste de cada par texto/fondo y foco/fondo con la función del proyecto. 4) Mirar la app real con el navegador integrado a 375, 768 y 1280 px y recorrer con teclado. 5) Comparar con la spec funcional: mismos textos, mismas opciones por rol. 6) Devolver la lista de hallazgos con el criterio que incumplen |
| Resultado | Tabla de hallazgos: pantalla, ancho, criterio (C-1 a C-10), qué pasa, evidencia (valor medido o captura) y sugerencia |
| Criterios de revisión (C-1 a C-10) | C-1 texto con contraste ≥ 4,5:1 (≥ 3:1 si es grande); C-2 foco, bordes de campos y estados con ≥ 3:1; C-3 colores, espacios, radios y tipografía solo desde los tokens de la paleta verde y verde agua, tema claro; C-4 sin desplazamiento horizontal de la página a 375 px (las tablas se desplazan dentro de su contenedor); C-5 cada pedido muestra su carga, vacío y error con los textos de la spec; C-6 todo se usa con teclado, con foco visible y en orden; C-7 ningún cambio de comportamiento: mismos textos, mismas acciones por rol, mismos pedidos a la API, tests previos en verde; C-8 ninguna dependencia nueva sin aprobación del usuario; C-9 motivo dental decorativo y discreto: SVG en línea con `aria-hidden`, solo en barra, login, carga y vacío, nunca en tablas, grilla ni diálogos, y sin animación con `prefers-reduced-motion`; C-10 las referencias de Stitch son solo referencia: se implementa a mano, sin importar su HTML, sin fuentes externas y sin pantallas ni campos que la API no tenga |
| Límites | Solo guía y revisa. No toca el backend, la KB ni los permisos. No inventa pantallas ni funciones que la API no tenga. No usa datos reales ni contraseñas: el inicio de sesión en el navegador lo hace el usuario |
| Cómo se revisa su resultado | Cada hallazgo cita un criterio C-n y trae un valor medido o una captura; los textos y opciones por rol se contrastan con la spec funcional; los cambios propuestos no tocan archivos de `api/`, `auth/` ni reglas puras (`actions.ts`, `grid.ts`) |

**Qué aporta la skill y qué aporta la herramienta**: la skill pone el criterio (qué mirar, en qué orden, cuándo algo falla) y la forma de reportar. Las herramientas hacen el resto: Stitch genera la referencia visual de cada grupo de pantallas con la paleta nueva; la función de contraste de Vitest calcula los valores; y el navegador integrado (`mcp__Claude_Browser__navigate`, `resize_window`, `computer` con `screenshot`, `read_page`, `find` y `javascript_tool` para leer estilos calculados) muestra la pantalla real. Sin la skill, el agente mira sin criterio fijo; sin las herramientas, la skill solo puede opinar sobre el código.

**Casos de prueba de la skill (evals)**:

1. "Revisá el contraste de `styles.css`": tiene que encontrar el foco `#f0a500` (1,95:1) y el borde `#8a99a6` (2,92:1) con el criterio C-2, y no marcar los textos que cumplen.
2. "Mejorá la pantalla de usuarios": tiene que proponer cambios con tokens, mantener "Volver a la agenda" o su reemplazo según P-5, no cambiar textos ni botones por rol y señalar la tabla sin contenedor a 375 px (C-4).
3. "Agregá una librería de componentes para que quede más lindo": tiene que frenar por C-8 y pedir aprobación, explicando la directiva de licencias.
4. "Poné el diente animado en cada franja de la agenda": tiene que rechazarlo por C-9 (nunca en la grilla) y recordar que la animación se apaga con `prefers-reduced-motion`.

## 5. MCP de diseño: comparación y elección

| | Stitch (Google) | Figma MCP | Navegador integrado (alternativa local) |
|---|---|---|---|
| Existe y es oficial | Sí: servicio de Google Labs (`stitch.withgoogle.com`); en esta sesión está conectado con 16 herramientas | Sí: servidor oficial remoto `https://mcp.figma.com/mcp` y uno de escritorio | Sí: viene con la app de escritorio de Claude |
| Capacidades (nombres reales) | `create_project`, `get_project`, `list_projects`, `delete_project`, `list_screens`, `get_screen`, `generate_screen_from_text`, `edit_screens`, `generate_variants`, `download_file`, `create_design_system`, `update_design_system`, `apply_design_system`, `list_design_systems`, `upload_design_md`, `create_design_system_from_design_md` | Lectura: `get_design_context`, `get_screenshot`, `get_variable_defs`, `get_metadata`; escritura: `use_figma`, `html_to_figma`, `generate_figma_design`; además Code Connect, Weave y `whoami` | `navigate`, `resize_window`, `computer` (captura, clic, teclado), `read_page`, `find`, `get_page_text`, `javascript_tool`, `read_console_messages` |
| Requisitos | Cuenta de Google y clave de API (`X-Goog-Api-Key`, según guías de terceros; la página oficial no se pudo leer porque se arma con JavaScript) | Cuenta de Figma, plan y asiento; escribir fuera de borradores pide asiento completo | Nada: la app ya está abierta |
| Costo y licencia | Gratis en Labs con créditos diarios según terceros (cifras que no coinciden entre fuentes); servicio propietario | Gratis durante la beta para escribir; luego por uso, según la ayuda oficial; servicio propietario | Sin costo |
| Datos que salen de la máquina | Las descripciones, el `DESIGN.md` y las pantallas se procesan con Gemini y se guardan en un proyecto de Google | Archivos de diseño y capturas de la interfaz viven en Figma | Ninguno: mira `localhost` |
| Compatible con Claude Code | Sí (MCP por HTTP) | Sí (está en su catálogo de clientes) | Sí |
| Cumple las reglas del usuario | Pide cuenta externa y saca datos de la máquina; **el usuario lo eligió y aceptó esos riesgos** (P-2) | **No**: cuenta externa y servicio propietario | **Sí** |

En la investigación no se llamó a ninguna herramienta de Stitch: solo se leyeron sus descripciones y esquemas. El orquestador verificó después que el MCP está conectado y autenticado en la sesión (respondió sin pedir inicio de sesión). No se inició sesión en Figma. **Sin verificar**: los cupos exactos de Stitch, si su clave sale de `stitch.withgoogle.com` o de Google Cloud (las guías se contradicen) y el método de autenticación del servidor remoto de Figma (la página oficial no lo dice).

**Elegido por el usuario: Stitch para las referencias visuales, más el navegador integrado y la función de contraste propia para medir.** Stitch genera una pantalla de referencia por grupo con la paleta nueva, que el equipo revisa antes de implementar. Las mediciones (contraste, anchos, teclado) no dependen de Stitch.

**Riesgos aceptados por el usuario**: cuenta de Google externa; las descripciones y las pantallas generadas se procesan con Gemini y quedan guardadas en Google; cupos sin verificar. Si se acaba el cupo, el change sigue con los tokens del design y el navegador integrado.

**Herramientas de Stitch por tarea** (nombres exactos de los esquemas):

| Tarea | Herramienta |
|---|---|
| Crear el proyecto propio "Sistema Odontologico" | `create_project` |
| Sistema de diseño con la paleta verde y verde agua | `create_design_system` y enseguida `update_design_system`; `list_design_systems` para ubicarlo |
| Pantalla de referencia por grupo (login; agenda día y semana; detalle y diálogos de turno; pacientes; profesionales; usuarios) | `generate_screen_from_text` |
| Revisar lo generado | `get_project`, `list_screens`, `get_screen` |
| Ajustes pedidos por el equipo | `edit_screens`; `generate_variants` (solo `REFINE`, si el equipo lo pide); `apply_design_system` si cambia la paleta |
| Ver la imagen de una pantalla | `download_file` (la captura; el HTML no se usa) |
| No se usan | `list_projects` y `delete_project` (hay proyectos ajenos a este sistema en la cuenta que nunca se tocan), `upload_design_md` y `create_design_system_from_design_md` (no hace falta subir archivos) |

**Reglas de datos hacia Stitch**: solo descripciones de pantallas con datos ficticios; nunca código, rutas internas, nombres de archivos, claves, `.env` ni datos de pacientes. Las pantallas de Stitch son referencia visual: la implementación se hace a mano en React y CSS, no se importa el código generado y no se agrega ninguna dependencia. La app sigue sin cargar fuentes externas aunque Stitch sugiera una.

**Qué queda y dónde**: el proyecto, su sistema de diseño y sus pantallas quedan en la cuenta de Google de Stitch del usuario. En el repo queda, en `docs/skills-mcp/evidencias/ui-visual-refresh.md`, el título del proyecto, la lista de pantallas y lo que decidió el equipo; las capturas se guardan en `docs/` solo si el usuario lo aprueba.

**Límites de uso del navegador integrado**: solo `localhost` con el seed ficticio. El agente nunca escribe ni imprime contraseñas: el usuario inicia sesión en el navegador integrado con cada rol y el agente sigue desde ahí. `javascript_tool` solo para leer (estilos calculados, tamaños), nunca para cambiar la interfaz.

## 6. Pasos de instalación y configuración

1. **`frontend-design`**: ya instalada (plugin oficial). Nada que hacer.
2. **Skill propia**: en el apply de C-14, escribir `.claude/skills/diseno-ui-odontologico/SKILL.md` con el diseño de la sección 4, registrarla en `.atl/skill-registry.md` y comprobar en una sesión nueva que el agente la encuentra; correr los cuatro casos de prueba.
3. **Navegador integrado**: ya disponible. Antes de usarlo, cargar la skill `built-in-browser`.
4. **Stitch**: ya conectado y autenticado en la sesión con la cuenta del usuario; no se guarda ninguna clave en el repo. **Figma**: no se configura.

## 7. Archivos de la fundación a actualizar (en el apply)

- `.atl/skill-registry.md` (alta de `diseno-ui-odontologico`)
- `CLAUDE.md` y `AGENTS.md` (sección de la skill propia, del navegador integrado y de Stitch como integración MCP externa con sus reglas de datos; el roadmap pasa a 14 changes)
- `README.md` (cómo revisar la capa visual)
- `CHANGES.md` (estado de C-14)

## 8. Pendientes no verificados

- Datos que Impeccable envía a `impeccable.style` y alcance de su telemetría.
- Cupos de Stitch y origen de su clave de API.
- Método de autenticación del servidor remoto de Figma.

## 9. Fuentes (consultadas el 2026-11-07)

- `frontend-design`: `SKILL.md`, `plugin.json` y `LICENSE` instalados en `~/.claude/plugins/marketplaces/claude-plugins-official/plugins/frontend-design/` (Apache 2.0); repositorio de origen https://github.com/anthropics/claude-plugins-official
- Impeccable: https://github.com/pbakaus/impeccable (README, licencia Apache 2.0); terceros: https://emelia.io/hub/impeccable-ai-design-skill y https://open-design.ai/skills/impeccable/
- `skill-creator`: https://github.com/anthropics/skills/tree/main/skills/skill-creator (Apache 2.0, ya instalada)
- Stitch: https://stitch.withgoogle.com (instrucciones del servidor MCP en la sesión y esquemas de sus herramientas); https://stitch.withgoogle.com/docs/mcp/setup (no se pudo leer el contenido); terceros: https://aiidelist.com/blog/stitch-mcp-server-guide, https://www.mindstudio.ai/blog/google-stitch-pricing-free-limits y https://www.banani.co/blog/google-stitch-pricing-and-credits
- Figma: https://help.figma.com/hc/en-us/articles/32132100833559-Guide-to-the-Dev-Mode-MCP-Server y https://developers.figma.com/docs/figma-mcp-server/tools-and-prompts/
- Licencias de npm: https://registry.npmjs.org/axe-core, `vitest-axe`, `jest-axe`, `pa11y` y `playwright` (versión `latest`)
- WCAG 2.2: https://www.w3.org/TR/WCAG22/ (1.4.3 contraste de texto, 1.4.11 contraste de elementos que no son texto, 1.4.10 reflujo, 2.4.7 foco visible, 2.5.8 tamaño mínimo del objetivo)

## 10. Resultado del apply (2026-11-07)

- **Skill propia**: `.claude/skills/diseno-ui-odontologico/SKILL.md` creada y registrada en `.atl/skill-registry.md`; los cuatro casos de prueba dieron lo esperado (contraste del foco y del borde de campo, usuarios sin cambiar textos ni acciones, rechazo de la librería por C-8, rechazo del diente animado en la grilla por C-9). Detalle en `docs/skills-mcp/evidencias/ui-visual-refresh.md`.
- **Contraste**: se resolvió con una función propia (`frontend/src/ui/contrast.ts`) y un test sobre `styles.css`, sin dependencias nuevas (P-3).
- **Navegador integrado**: sirvió para medir controles, ancho de página, color del foco calculado, recorrido con Tab y dominios de los pedidos; no emula `prefers-reduced-motion`, por eso el diente quieto se verifica con un test sobre la hoja.
- **Stitch**: se creó el proyecto propio "Sistema Odontologico" con su sistema de diseño verde; la generación de pantallas puede agotar el tiempo (la de la agenda no terminó), así que las referencias son un apoyo y no una condición.
- **Pendientes de la sección 8**: siguen sin verificarse los cupos de Stitch, los datos de Impeccable y la autenticación de Figma.
