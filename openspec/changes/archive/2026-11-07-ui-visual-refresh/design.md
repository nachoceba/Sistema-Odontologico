# Design: ui-visual-refresh (C-14)

## Context

Motivación en `proposal.md`. Este design parte de lo que se leyó en el código el 2026-11-07, no de suposiciones.

- **Stack visual actual**: React 19 + React Router 8 + Vite 8, una sola hoja `frontend/src/styles.css` (505 líneas, CSS plano, sin variables, sin librerías de componentes ni de estilos). Fuente del sistema (`system-ui`). Dependencias de producción: `react`, `react-dom` y `react-router`; nada más.
- **Tests**: 392 de Vitest con Testing Library y `jsdom`. Consultan por rol y texto accesible; solo dos clases CSS se comprueban en tests: `appointment--cancelled` (`agenda/day.test.tsx`) y `day-column--today` (`agenda/day.test.tsx`, `agenda/week.test.tsx`). Esas dos clases se conservan. Los tests montan la app entera con `renderApp` (`test-utils.tsx`), así que un marco común en `App.tsx` se prueba sin cambiar el arnés.
- **Backend**: 32 rutas en la matriz ruta × rol (`backend/tests/unit/api/test_permission_matrix.py`, DD-110). La interfaz consume 30: no usa `GET /professionals/{id}` ni `GET /patients/{id}` (están en el cliente pero ninguna pantalla los llama). No existe ruta para la configuración del consultorio ni para listar recordatorios enviados, aunque la matriz de `03_actores_y_roles.md` los nombre: quedan fuera.
- **App en marcha**: `http://localhost:5173` responde y `GET /api/v1/health` da `{"status":"ok"}`. Se miró `/login` con el navegador integrado. Las pantallas con sesión se revisaron desde el código y los tests: iniciar sesión necesita la contraseña de demo, que vive en el `.env` local del usuario y no se lee.

### Inventario de pantallas y flujos

| # | Pantalla o flujo | Ruta | Roles | Qué hace | Endpoints | Tests existentes | Estado visual observado |
|---|---|---|---|---|---|---|---|
| 1 | Login | `/login` | Pública | Email y contraseña; estado de la API | `GET /health`, `POST /auth/login`, `GET /auth/me` | `App.test.tsx`, `auth/session.test.ts`, `config.test.ts` | Formulario centrado de 24rem sin jerarquía ni marca; el estado de la API es un texto suelto al pie (captura 2026-11-07) |
| 2 | Carga inicial y aviso de permiso | `*`, `/usuarios` sin permiso | Todos | "Cargando…" mientras valida la sesión; aviso con enlace a `/agenda` | `GET /auth/me` | `App.test.tsx`, `users/access.test.tsx` | Texto plano sin marco ni barra |
| 3 | Agenda día y semana | `/agenda` | Admin y recepción (con selector de profesional); odontólogo (solo la propia) | Grilla de franjas libres, ocupadas y fuera de horario, turnos con estado, licencias, navegación de fechas | `GET /professionals`, `GET /appointments`, `GET /professionals/{id}/slots`, `GET /professionals/{id}/time-off` | `agenda/*.test.*` | Única pantalla con `AppNav`, que no tiene enlace "Agenda" ni marca la página actual; botones "Agendar" y de turno con `padding: 0.15rem` (riesgo de objetivo < 24 px); barra de herramientas sin agrupación visual |
| 4 | Agendar desde una franja | panel en `/agenda` | Admin y recepción | Buscar o crear paciente y agendar | `GET /patients?q=`, `POST /patients`, `POST /appointments` | `appointments/booking.test.tsx`, `flows.test.tsx` | Panel lateral correcto en angosto; `PatientSearch` usa la clase `patient-search`, que no tiene estilo |
| 5 | Detalle del turno | panel en `/agenda` | Todos (acciones según rol) | Datos del turno y acciones posibles | (datos de la grilla) | `appointments/detail.test.tsx` | Lista de definición legible; etiqueta de conflicto como `<p>` con estilo de chip |
| 6 | Cancelar con motivo | diálogo | Admin y recepción | Motivo obligatorio | `POST /appointments/{id}/cancel` | `appointments/cancel.test.tsx` | Diálogo sin retener el foco con Tab |
| 7 | Reprogramar | diálogo | Admin y recepción | Fecha y franja libre nueva | `GET /professionals/{id}/slots`, `POST /appointments/{id}/reschedule` | `appointments/reschedule.test.tsx` | Igual que 6 |
| 8 | Marcar atendido o ausente | diálogo de confirmación | Todos (odontólogo solo lo propio) | Confirmar asistencia | `POST /appointments/{id}/attendance` | `appointments/attendance.test.tsx` | Usa `ConfirmDialog` de pacientes: dos diálogos con el mismo aspecto pero código distinto |
| 9 | Turnos en conflicto | sección en `/agenda` | Admin y recepción | Lista con acceso a reprogramar o cancelar | `GET /professionals/{id}/conflicts`, `GET /appointments/{id}` | `appointments/conflicts.test.tsx` | Mismo naranja que "aviso" y "licencia": no se distinguen tipos de aviso |
| 10 | Pacientes | `/pacientes` | Todos (odontólogo solo lectura; borrar solo admin) | Buscar, alta, edición, desactivar, reactivar, borrar | `GET /patients`, `POST /patients`, `PATCH /patients/{id}`, `POST .../deactivate`, `POST .../reactivate`, `DELETE /patients/{id}` | `patients/*.test.tsx` | Sin barra de navegación ni "Salir"; tabla con clase `users-table` y sin contenedor para 375 px; avisos de carga, vacío y error como texto plano |
| 11 | Profesionales | `/profesionales` | Todos (edita solo admin; odontólogo solo la propia) | Ficha, horario semanal por tramos, licencias, aviso de conflictos | `GET /professionals`, `PATCH /professionals/{id}`, `GET`/`PUT .../working-hours`, `GET`/`POST .../time-off`, `DELETE .../time-off/{id}` | `professionals/*.test.tsx` | Sin barra; editor semanal en `fieldset` con borde `#d0d4da` de 1,49:1; campos de hora sin estilo común |
| 12 | Usuarios | `/usuarios` | Solo admin | Alta, edición de rol, desactivar, reactivar, contraseña | `GET`/`POST /users`, `PATCH /users/{id}`, `POST .../deactivate`, `POST .../reactivate`, `PUT .../password` | `pages/UsersPage.test.tsx`, `users/access.test.tsx` | Sin barra; tabla con varios botones por fila que no entran a 375 px |
| 13 | Salir | botón de la barra | Todos | Borra el token y vuelve a `/login` | — | `App.test.tsx` | Solo visible en `/agenda` |

Total: 13 pantallas o flujos, 30 endpoints usados de los 32 de la matriz (los 2 restantes no tienen pantalla y no se agregan).

Hallazgos transversales medidos (fórmula de WCAG): texto principal `#1a2733` sobre `#f5f8fa` 14,25:1; azul principal `#0b6e8a` sobre blanco 5,81:1; texto secundario `#6b7780` sobre blanco 4,59:1 (justo); **foco `#f0a500` sobre `#f5f8fa` 1,95:1 y sobre blanco 2,08:1 (no cumple 3:1)**; **borde de campo `#8a99a6` sobre blanco 2,92:1 (no cumple)**; borde de tarjetas `#c9d3da` sobre blanco 1,52:1 (decorativo, no obligatorio). Reglas duplicadas: `.hint` (líneas 116 y 427) y `.dialog` (190 y 438). El único `@media` de ancho es el del panel lateral.

### Pendientes del roadmap y la KB que este change no resuelve

- **SU-02**: proveedor SMTP de producción (desarrollo y demo usan Mailpit). No afecta la UI.
- **Endurecer sesión y login** (DD-46, DD-47, DD-112): cookie httpOnly y límite de intentos. El login se rediseña visualmente sin cambiar cómo guarda el token ni cómo responde a errores.
- **R-8, adopción con una recepcionista real** (DD-114, `docs/adopcion-recepcion.md`): la prueba sigue pendiente; este change la facilita pero no la reemplaza.
- **Preguntas abiertas de dominio** (SU-01 zona horaria, SU-05 varios turnos por día, duración real del slot, sillones, duración por prestación, sobreturnos): ninguna se toca; la UI muestra lo que la API ya devuelve.
- **Sin endpoint** (exclusión): configuración del consultorio (matriz "Configuración (slot) RU") y recordatorios enviados (matriz "R"). Si se quieren pantallas para eso, primero hace falta un change de backend.

## Goals / Non-Goals

**Goals:**
- Una base de tokens y componentes visuales que las pantallas usen sin repetir valores.
- Cumplir WCAG 2.2 AA en contraste, foco, tamaño de objetivos y reflujo, con pruebas que lo midan.
- Misma barra y mismo aspecto de avisos en todas las pantallas con sesión.

**Non-Goals:**
- Cambiar textos, flujos, validaciones, permisos, rutas o pedidos a la API.
- Modo oscuro, temas o personalización (P-6).
- Pantallas nuevas o datos que la API no devuelve.
- Pruebas de regresión visual automáticas con navegadores descargados (P-7).

## Decisiones (P-1 a P-11)

Todas las decisiones P-1 a P-11 están **CONFIRMADAS POR EL USUARIO** (2026-11-07): P-2 = B (Stitch), P-6 = A (sin modo oscuro), P-10 = B (paleta nueva) y las demás con la opción A (recomendada). El usuario además pidió detalles dentales sutiles (D-10).

### P-1 — ¿Un change o varios? — CONFIRMADA POR EL USUARIO: A
- **A (recomendada)**: un solo change C-14 por grupos, con un punto de corte seguro después del grupo 5 (referencias de Stitch, tokens, componentes comunes, motivo dental y marco de navegación). Si hay que frenar ahí, la app ya queda consistente y accesible. Sigue el criterio de DD-115.
- B: C-14a `ui-visual-foundation` (tokens, componentes, marco) y C-14b `ui-visual-pages` (pantalla por pantalla).
- C: tres changes (base, agenda, catálogos).
- Motivo: el trabajo es solo de frontend y chico por pantalla; partirlo duplica revisión y docs sin bajar el riesgo.

### P-2 — ¿Se usa un MCP de diseño (Stitch o Figma)? — CONFIRMADA POR EL USUARIO: B (Stitch)
- A: ninguno; solo el navegador integrado y la función de contraste propia.
- **B (elegida por el usuario)**: Stitch, para generar pantallas de referencia visual con la paleta nueva antes de implementar. El MCP ya está conectado y autenticado en la sesión.
- C: Figma MCP (cuenta, asiento y servicio propietario).
- Riesgos aceptados por el usuario: cuenta de Google externa, las descripciones y pantallas se procesan con Gemini y quedan en Google, cuotas sin verificar. Reglas de uso en D-9. Las mediciones siguen con `contrastRatio` y el navegador integrado; Stitch no reemplaza ninguna prueba. Comparación en `docs/skills-mcp/investigacion-diseno-ui.md` §5.

### P-3 — ¿Cómo se comprueba la accesibilidad de forma automática? — CONFIRMADA POR EL USUARIO: A
- **A (recomendada)**: función propia de contraste (`frontend/src/ui/contrast.ts`, fórmula de WCAG) y un test que lee los tokens de `styles.css` y verifica la lista de pares; los roles, nombres y foco se siguen probando con Testing Library.
- B: `vitest-axe` (MIT), que depende de `axe-core` (MPL-2.0): fuera de la directiva MIT/Apache/BSD salvo autorización.
- C: solo revisión manual.
- Motivo: A no suma dependencias, cumple la licencia y cubre lo que más falla hoy (contraste de foco y bordes).

### P-4 — ¿Qué tipografía? — CONFIRMADA POR EL USUARIO: A
- **A (recomendada)**: la del sistema (`system-ui` y una escala tipográfica definida en tokens). No descarga nada y funciona sin red. La fuente que se elija en el sistema de diseño de Stitch es solo para la referencia: la app no la carga.
- B: una fuente abierta guardada en el repositorio (por ejemplo con licencia SIL OFL): no es MIT/Apache/BSD, habría que autorizarla.
- C: Google Fonts: descarga desde una página externa; descartada por las reglas.
- Motivo: simple, local y sin licencias nuevas; la jerarquía la dan tamaños y pesos.

### P-5 — ¿Barra común en todas las pantallas con sesión? — CONFIRMADA POR EL USUARIO: A
- **A (recomendada)**: sí. `AppNav` pasa a un marco común de las rutas con sesión (en `App.tsx`), suma el enlace "Agenda", marca la página actual con `aria-current="page"` y agrega "Saltar al contenido". Los encabezados de página dejan "Volver a la agenda" (lo reemplaza la barra); el aviso de permiso lo conserva (lo pide `frontend-user-management`).
- B: dejar la barra solo en `/agenda` y mejorar solo el aspecto de los enlaces "Volver a la agenda".
- C: menú lateral fijo.
- Motivo: hoy fuera de la agenda no se ve con qué cuenta se está ni cómo salir; A no cambia los destinos de ningún rol.

### P-6 — ¿Modo oscuro? — CONFIRMADA POR EL USUARIO: A (sin modo oscuro)
- **A (elegida)**: no hay modo oscuro; solo tema claro.
- B: seguir `prefers-color-scheme` automáticamente.

### P-7 — ¿Cómo se verifica el resultado visual? — CONFIRMADA POR EL USUARIO: A
- **A (recomendada)**: lista de verificación por pantalla y ancho (375, 768, 1280 px) recorrida con el navegador integrado, con medidas anotadas en `docs/skills-mcp/evidencias/ui-visual-refresh.md`, más los tests de contraste y tokens. Las capturas se guardan en `docs/` solo si el usuario lo aprueba.
- B: regresión visual con Playwright (`toHaveScreenshot`, Apache 2.0): suma una dependencia pesada que descarga navegadores.
- C: solo los tests de Vitest.
- Motivo: A no suma dependencias ni cuentas y mira la app real.

### P-8 — ¿Cómo se ven las tablas en pantallas angostas? — CONFIRMADA POR EL USUARIO: A
- **A (recomendada)**: contenedor con desplazamiento horizontal propio, nombre accesible (`role="region"` con `aria-label`) y `tabindex="0"`; la tabla no cambia.
- B: pasar a tarjetas por fila debajo de 40rem (cambia el marcado de la tabla y obliga a revisar los tests que consultan filas y celdas).
- Motivo: A no toca la estructura que usan los tests y cumple el reflujo.

### P-9 — ¿Skill propia o Impeccable? — CONFIRMADA POR EL USUARIO: A
- **A (recomendada)**: crear en el apply la skill propia `diseno-ui-odontologico` (diseño en la ficha de investigación §4) y usar `frontend-design` como criterio de fondo.
- B: instalar Impeccable (Apache 2.0), que consulta `impeccable.style` y trae telemetría.
- C: sin skill nueva, solo `frontend-design`.
- Motivo: A deja criterios fijos y verificables del proyecto sin red ni dependencias.

### P-10 — ¿Se mantiene la identidad de color actual? — CONFIRMADA POR EL USUARIO: B (paleta nueva)
- A: mantener el azul petróleo `#0b6e8a`.
- **B (elegida)**: identidad nueva en verdes y verde agua, minimalista, clara de entender. Tokens en D-1; cada par de texto y fondo se valida con `contrastRatio` en un test.

### P-11 — ¿Los diálogos retienen el foco con Tab? — CONFIRMADA POR EL USUARIO: A
- **A (recomendada)**: sí. `Modal` y `ConfirmDialog` comparten una base que, además de lo que hacen hoy (foco inicial seguro y Escape), mantiene el foco adentro y lo devuelve al elemento que abrió el diálogo al cerrarse.
- B: solo unificar el aspecto, sin cambiar el teclado.
- Motivo: es un arreglo de accesibilidad (WCAG 2.4.3) que no cambia ninguna acción; queda en la spec "Foco visible y uso con teclado".

## Decisions

### D-1 — Tokens en `:root` de `styles.css` (paleta verde y verde agua, P-10)
Variables CSS con nombres por función, no por color. Alternativa descartada: CSS Modules o una librería de estilos (más archivos y dependencias sin beneficio para una sola hoja).

| Token | Valor | Uso | Contraste medido (fórmula de WCAG) |
|---|---|---|---|
| `--color-bg` | `#f3faf8` | Fondo de la página (blanco menta) | — |
| `--color-surface` | `#ffffff` | Paneles, tarjetas, diálogos, tablas | — |
| `--color-text` | `#12302b` | Texto principal (verde casi negro) | 13,38 sobre bg; 14,16 sobre surface |
| `--color-text-muted` | `#4b625d` | Texto secundario y pistas | 6,19 sobre bg; 6,55 sobre surface; 5,85 sobre outside |
| `--color-primary` | `#0a7368` | Verde agua principal: botón principal, enlaces, día de hoy | Blanco encima 5,73; como texto 5,41 sobre bg y 4,97 sobre primary-soft |
| `--color-primary-hover` | `#08645a` | Botón principal al pasar el mouse | Blanco encima 7,05 |
| `--color-primary-soft` | `#dff3ef` | Fondo suave de selección y franja ocupada | Texto encima 12,27 |
| `--color-secondary` | `#2a7148` | Verde: botón secundario, marca de franja libre | 5,91 sobre surface; 5,20 sobre secondary-soft |
| `--color-secondary-soft` | `#e6f4ea` | Fondo de franja libre y aviso informativo | — |
| `--color-border` | `#cfe3de` | Bordes decorativos de tarjetas y tablas | Decorativo, sin mínimo |
| `--color-border-input` | `#6b8a83` | Borde de campos de formulario | 3,76 sobre surface; 3,55 sobre bg |
| `--color-focus` | `#12302b` | Contorno de foco de 3 px separado 2 px del elemento | 13,38 sobre bg; 14,16 sobre surface (el par medido es foco/fondo porque el contorno va separado; contra el botón principal daría 2,71, por eso la separación es obligatoria) |
| `--color-success` / `--color-success-bg` | `#1d6b3c` / `#e7f5ec` | Aviso de éxito, "Atendido" | 5,80 |
| `--color-error` / `--color-error-bg` | `#a3262c` / `#fdeced` | Errores, botón de peligro, "Ausente" | 6,41; blanco sobre error 7,31 |
| `--color-warning` / `--color-warning-bg` | `#7a5200` / `#fff4dc` | Licencias, turnos en conflicto | 6,34 |
| `--color-pending` / `--color-pending-bg` | `#0e5f73` / `#e3f2f6` | Pendiente: "Cargando…", "Verificando…", turno agendado | 6,30 |
| `--color-outside` | `#eef3f2` | Franja fuera de horario | Texto 12,63; texto secundario 5,85 |
| `--color-accent` | `#9fd8cc` | Solo el motivo dental decorativo (D-10); nunca texto ni borde que transmita información | Decorativo, sin mínimo |

Además: `--font-sans` (`system-ui`, P-4), escala `--font-size-1` a `--font-size-6`, `--space-1` a `--space-6`, `--radius-sm|md|lg` y `--shadow-sm|md`. Estilo minimalista: un solo color de acento fuerte (el primario), superficies blancas sobre fondo menta, bordes finos y sombras mínimas.

### D-2 — Contraste medido con una función propia
`frontend/src/ui/contrast.ts` exporta `contrastRatio(a, b)` (luminancia relativa de WCAG). `frontend/src/ui/tokens.test.ts` lee `styles.css` como texto, extrae los tokens de `:root`, recorre una lista de pares (texto/fondo con mínimo 4,5, foco y bordes de campo con mínimo 3) y además falla si encuentra colores sueltos fuera de `:root` o selectores repetidos. Así el test no se desincroniza de la hoja.

### D-3 — Marco común en `App.tsx`
Un componente de marco (`AppLayout`) con `Outlet` envuelve las rutas con sesión: enlace "Saltar al contenido", `AppNav` y `<main id="contenido">`. Las páginas dejan de renderizar su propio `<main>` y `AppNav`. Los textos de la barra no cambian; se suma "Agenda".

### D-4 — Componentes visuales sin lógica
Clases comunes en `styles.css` para botones (`button`, `.secondary`, `.danger`, `.link-button`), campos (`.field`), avisos (`.notice--info|ok|warning|error` sobre los `role` actuales), tablas (`.data-table` dentro de `.table-scroll`) y tarjetas. `users-table` pasa a `data-table` en las tres pantallas. Sin componentes React nuevos salvo el marco y la base de diálogo (P-11).

### D-5 — Pantalla por pantalla, en el orden del inventario
Primero login y marco, después agenda (la más usada por recepción), después pacientes, profesionales y usuarios. En cada una: tokens, estados, anchos, foco. Las clases `appointment--cancelled` y `day-column--today` se conservan.

### D-6 — Verificación visual con el navegador integrado
Con la app en Docker Compose y el seed ficticio, el usuario inicia sesión en el navegador integrado con cada rol (el agente nunca escribe la contraseña). El agente usa `mcp__Claude_Browser__resize_window` (375, 768 y 1280 px), `navigate`, `computer` con `screenshot`, `read_page` y `find` para roles y nombres accesibles, `computer` con `key` (`Tab`, `Escape`) para el teclado y `javascript_tool` solo para leer estilos calculados y tamaños. Resultado en `docs/skills-mcp/evidencias/ui-visual-refresh.md`.

### D-7 — Qué aporta cada herramienta
| Tarea | Skill o criterio | Herramienta concreta |
|---|---|---|
| Referencia visual por grupo de pantallas | `frontend-design` (dirección visual) y `diseno-ui-odontologico` (C-9, C-10) | Stitch: `create_project`, `create_design_system` + `update_design_system`, `generate_screen_from_text`, `get_screen`, `list_screens`, `download_file` (ver D-9) |
| Definir tokens y jerarquía | `frontend-design` (plan de tokens y revisión) y `diseno-ui-odontologico` (C-3) | Edición de `styles.css` a mano, tomando la referencia de Stitch |
| Medir contraste | `diseno-ui-odontologico` (C-1, C-2) | `contrastRatio` en Vitest; `javascript_tool` para el color calculado en pantalla |
| Revisar anchos | `diseno-ui-odontologico` (C-4) | `resize_window` y `computer` `screenshot` |
| Revisar teclado y foco | `diseno-ui-odontologico` (C-6) | `computer` `key` y `read_page` |
| Confirmar que nada cambió | `diseno-ui-odontologico` (C-7) | Suite de Vitest, pytest `smoke` y matriz ruta × rol |
| Código React | `vercel-react-best-practices` (solo React) y `tdd` | Vitest |

### D-8 — Tests
Cada grupo con código sigue RED → GREEN → TRIANGULATE → REFACTOR. Tests nuevos: tokens y contraste de toda la tabla de D-1 (D-2), marco de navegación por rol con `aria-current` y "Saltar al contenido", retención del foco en diálogos, contenedor de tablas con nombre accesible y motivo dental (D-10). Los 392 tests previos son la red de seguridad de cada grupo y no se cambian sus aserciones.

### D-9 — Referencias de diseño en Stitch (P-2)
Stitch da **referencias visuales**, no código. La implementación se hace a mano en React y CSS; no se importa el HTML generado ni se agrega ninguna dependencia.

| Paso | Herramienta de Stitch (nombre exacto) | Qué se manda |
|---|---|---|
| Crear el proyecto propio | `create_project` con `title: "Sistema Odontologico"` | Solo el título |
| Sistema de diseño con la paleta nueva | `create_design_system` (con el `projectId` del paso anterior) y enseguida `update_design_system`, como indica su descripción | `colorMode: LIGHT`, `customColor` y `overridePrimaryColor` `#0a7368`, `overrideSecondaryColor` `#2a7148`, `overrideNeutralColor` `#f3faf8`, `roundness: ROUND_EIGHT`, una fuente de la lista solo para la referencia (P-4) y un `designMd` corto con las reglas de este design (minimalista, tema claro, motivo dental sutil) |
| Ubicar el sistema de diseño | `list_design_systems` con el `projectId` propio | — |
| Una pantalla de referencia por grupo | `generate_screen_from_text` con `projectId` propio, `designSystem` del paso anterior y `deviceType` `DESKTOP` (y `MOBILE` para login y agenda) | Descripción en texto de la pantalla con datos ficticios del seed (por ejemplo "Dra. A", pacientes "@example.com"). Grupos: login; agenda día y semana; detalle y diálogos de turno; pacientes; profesionales; usuarios |
| Revisar lo generado | `get_project`, `list_screens`, `get_screen` | — |
| Ajustes tras la revisión del equipo | `edit_screens` (y `generate_variants` con `creativeRange: REFINE` solo si el equipo lo pide); `apply_design_system` si cambia la paleta | Texto del ajuste |
| Ver la imagen | `download_file` con el `screenshot.name` de la pantalla | — (se baja la imagen; el HTML no se usa) |

Reglas de datos hacia Stitch: solo descripciones de pantallas con datos ficticios; **nunca** código del repositorio, rutas internas, nombres de archivos, claves, `.env` ni datos de pacientes reales. Solo se trabaja dentro del proyecto propio: los demás proyectos de la cuenta no se listan, abren, editan ni borran, y no se usa `delete_project`. Tampoco se usan `upload_design_md` ni `create_design_system_from_design_md` (no hace falta subir archivos). Qué queda y dónde: el proyecto, su sistema de diseño y sus pantallas quedan guardados en la cuenta de Google de Stitch del usuario; en el repo solo queda, en la evidencia, el título del proyecto, la lista de pantallas y lo que decidió el equipo; las capturas se guardan en `docs/skills-mcp/evidencias/` solo si el usuario lo aprueba.

### D-10 — Motivo dental sutil
Un componente de marca (`ToothMark`) con un SVG en línea de un diente simple (contorno de una sola ruta), sin imágenes ni librerías. Lleva `aria-hidden="true"` y `focusable="false"`, usa `--color-accent` y `--color-primary`, y aparece solo en: la barra (junto al nombre del sistema), el login, el aviso de carga y los avisos de listado vacío. Nunca dentro de tablas, de la grilla de la agenda ni de diálogos. Mientras se carga, el diente tiene un pulso o brillo suave (opacidad entre 0,6 y 1, unos 1,6 s); `@media (prefers-reduced-motion: reduce)` apaga la animación. Los textos y roles accesibles de cada aviso no cambian.

## Risks / Trade-offs

- [Un test previo busca un texto que ahora aparece dos veces, por ejemplo "Agenda" en la barra y en el título] → se buscó en los tests y hoy ninguno consulta "Agenda", "Pacientes", "Profesionales" o "Usuarios" por texto suelto; si aparece un caso, se ajusta el marcado, no la aserción.
- [Mover `AppNav` al marco cambia el orden del DOM] → los tests montan la app entera (`renderApp`); el grupo del marco corre todo `agenda/`, `users/` y `App.test.tsx` como red.
- [Un color nuevo baja el contraste en un lugar no listado] → la lista de pares del test se arma desde el inventario de usos de cada token; la revisión con el navegador mide los casos reales.
- [La verificación visual depende de que el usuario inicie sesión] → sin sesión se verifican login, aviso y tests; la lista de verificación queda con sus casillas sin marcar hasta que se recorra.
- [Retener el foco en diálogos cambia el comportamiento del teclado] → es un arreglo de accesibilidad; queda como P-11 para que el equipo lo apruebe.
- [Crecer el CSS] → se borran duplicados y valores sueltos; `npm run build` y `check:bundle` lo controlan.
- [Stitch: datos que salen a Google, cuenta externa y cuotas sin verificar (aceptado por el usuario)] → solo descripciones con datos ficticios (D-9); si se acaba el cupo, se sigue con la paleta de D-1 y el navegador integrado, sin bloquear el change.
- [Tocar por error un proyecto ajeno de la cuenta de Stitch] → solo se usa el `projectId` que devuelve `create_project`; nada de `list_projects` ni `delete_project` en el apply.
- [La referencia de Stitch trae algo que la app no tiene (pantallas, campos, fuentes externas)] → es solo referencia: se implementa lo que dicen las specs funcionales, con la tipografía del sistema.
- [El pulso del diente distrae o molesta] → solo en carga, suave, nunca en la agenda densa, y apagado con `prefers-reduced-motion`.
- [Cambiar la identidad de color antes de la prueba de adopción (R-8)] → decisión del usuario (P-10); la paleta nueva conserva la diferencia entre estados por texto, no solo por color.

## Migration Plan

Solo frontend. Se despliega reconstruyendo el contenedor `frontend` (o el modo demo). Volver atrás es revertir los commits del change: no hay datos, migraciones ni variables que deshacer.

## Open Questions

Ninguna fuera de P-1 a P-11.
