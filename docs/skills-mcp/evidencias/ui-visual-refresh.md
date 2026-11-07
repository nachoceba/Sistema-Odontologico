# Evidencia: ui-visual-refresh (C-14)

Verificación visual con el navegador integrado sobre un entorno de Docker Compose aparte, con datos ficticios del seed. Las capturas no se guardan en el repositorio.

## Antes

Estado inicial medido el 2026-11-07 (suites: 392 de Vitest, typecheck, lint, build y check:bundle en verde).

| Pantalla | Ancho | Medida | Resultado |
|---|---|---|---|
| Agenda, vista semana (administración) | 1280 px | controles de menos de 24 px de alto | 9 (selector de profesional 126 × 18, campo de fecha 116 × 21, botones de día de 22 px) |
| Agenda, vista semana | 1280 px | pedidos a dominios externos | ninguno (solo el frontend y la API) |
| Agenda | 1280 px | barras de navegación | 1 (solo existe en `/agenda`) |
| Usuarios (administración) | 375 px | ancho de la página | 645 px: la tabla ensancha la página y hay desplazamiento horizontal |
| Usuarios | 375 px | barras de navegación | 0 |
| Contraste del foco | — | `#f0a500` sobre `#f5f8fa` | 1,95:1 (menos de 3:1) |
| Contraste del borde de campo | — | `#8a99a6` sobre blanco | 2,92:1 (menos de 3:1) |

## Skill `diseno-ui-odontologico`

Casos de prueba corridos en una sesión nueva de solo lectura (2026-11-07):

| Caso | Resultado |
|---|---|
| 1. "Revisá el contraste de `styles.css`" | Encontró el foco `#f0a500` (1,95:1 sobre `#f5f8fa`, 2,08:1 sobre blanco) y el borde de campo `#8a99a6` (2,92:1 sobre blanco) con C-2; no marcó los textos que cumplen (los listó como lo que está bien, con su valor); marcó la falta de tokens con C-3 |
| 2. "Mejorá la pantalla de usuarios" | Propuso contenedor desplazable con nombre y foco para la tabla (C-4), estado de vacío con el texto de la spec (C-5) y etiquetas con tokens (C-3); no cambió textos ni acciones por rol (C-7) y devolvió las decisiones de diseño como pregunta. Propuso además un `aria-label` por fila que cambiaría nombres accesibles: no se adopta |
| 3. "Agregá una librería de componentes" | Frenó por C-8, explicó la directiva de licencias (MIT, Apache, BSD) y pidió aprobación |
| 4. "Poné el diente animado en cada franja" | Lo rechazó por C-9 (nunca en la grilla) y recordó `prefers-reduced-motion` |

## Base

Medido el 2026-11-07 con el navegador integrado sobre el entorno aparte (administración, recepción y odontólogo del seed).

| Comprobación | Resultado |
|---|---|
| Login a 375 px y 1280 px | Diente, título "Sistema Odontológico", tarjeta con Email y Contraseña, botón "Ingresar"; sin barra de navegación ni enlace de salto |
| Barra común | Presente en Agenda, Pacientes, Profesionales y Usuarios; una sola `nav` y un solo `main` por pantalla; "Usuarios" solo para administración |
| Aviso de permiso (recepción en `/usuarios`, 375 px) | Barra completa con "Agenda", "Pacientes" y "Profesionales", aviso `role="alert"` con "No tenés permiso para esta acción" y enlace "Volver a la agenda" |
| Recorrido con Tab | Primer Tab: "Saltar al contenido"; luego Agenda y Pacientes, cada uno con el contorno visible |
| Color del foco | Calculado `rgb(18, 48, 43)` (`#12302b`), contorno sólido de 2,4 px; contraste con el fondo y con la superficie de 13,38:1 y mayor de 3:1 |
| Diente con movimiento reducido | La hoja deja `.tooth-mark--pulse` en `animation: none` bajo `prefers-reduced-motion: reduce` (verificado por test sobre `styles.css`); el panel del navegador no permite emular la preferencia, por eso no se midió el estilo calculado |
| Pedidos a dominios externos | Ninguno: solo `localhost:15173` (frontend) y `localhost:18000` (API) |
| Usuarios a 375 px | Antes 645 px de ancho de página; ahora sin desplazamiento horizontal, la tabla se desplaza dentro de su región |

Comparación con Stitch: solo se generó la referencia del login (ver "Stitch"); el resto se revisó contra el inventario y las specs.

## Agenda

| Rol | Ancho | Resultado |
|---|---|---|
| Administración | 375 px | Vista día y semana sin desplazamiento horizontal; 7 columnas en la semana; ningún control de menos de 24 px (antes 9); ningún diente en la grilla |
| Administración | 768 px | Barra de herramientas agrupada en "Navegar" y "Vista" más "Actualizar", envuelve sin cortes |
| Administración | 1280 px | Grilla legible, estados distinguibles por texto |
| Odontólogo | 375 px | Semana sin desplazamiento horizontal, barra con Agenda, Pacientes y Profesionales (sin Usuarios), ningún control de menos de 24 px |

Hallazgos y arreglos:

- Los botones de día de la semana medían 70 × 23 px: se agregó `min-height: 1.5rem` a `button.link-button` (re-medido, sin controles bajo 24 px).
- La barra de la agenda era una fila plana: se agruparon los controles con `role="group"` y `aria-label` ("Navegar", "Vista"), sin cambiar nombres ni acciones.
- El panel de conflictos ya usa los tokens de advertencia (borde izquierdo y etiqueta con texto), distinguible sin color.

## Catálogos

| Pantalla | Ancho | Resultado |
|---|---|---|
| Pacientes (administración) | 375 px | Región "Pacientes" enfocable, sin desplazamiento de la página, ningún control bajo 24 px |
| Profesionales (administración) | 375 px | Región "Profesionales" enfocable, sin desplazamiento de la página |
| Usuarios (administración) | 375 px | Región "Usuarios" enfocable, sin desplazamiento de la página |
| Pacientes (administración) | 1280 px | Tabla con los mismos textos y acciones (Editar, Desactivar, Borrar) |
| Usuarios (recepción) | 375 px | Aviso de permiso con el aspecto común y sin pedir `/users` |

## Stitch

Se creó el proyecto propio "Sistema Odontologico" y su sistema de diseño verde con motivo dental sutil. Solo se generó la referencia del login; la generación de la agenda se agotó por tiempo y no se reintentó. El resto de las pantallas se resolvió con la skill y el inventario (riesgo R-13 del diseño).
