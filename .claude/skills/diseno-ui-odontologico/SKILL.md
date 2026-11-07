---
name: diseno-ui-odontologico
description: Guía y revisa cambios visuales del frontend del sistema odontológico con criterios fijos del proyecto (tokens de la paleta verde y verde agua, contraste WCAG 2.2 AA, anchos de 375, 768 y 1280 px, estados de carga, vacío y error, foco y teclado, motivo dental discreto) sin cambiar comportamiento. Usala siempre que propongas, implementes o revises un cambio en frontend/src/**/*.tsx o frontend/src/styles.css que afecte cómo se ve una pantalla (C-14 y changes visuales posteriores), y cuando te pidan "revisá cómo se ve", "mejorá el diseño", "chequeá el contraste", "agregá una librería de componentes" o "poné un ícono animado", aunque no mencionen la skill.
---

# Diseño de interfaz del sistema odontológico

Esta skill es una herramienta de desarrollo para el agente. No forma parte del producto: el consultorio nunca la ve.

## Para qué sirve

Las pantallas se armaron de a una y la revisión visual "a ojo" cambia en cada change. La skill fija qué mirar, en qué orden y cuándo algo falla, y obliga a devolver los hallazgos siempre con el mismo formato y con un valor medido. Guía y revisa; no inventa pantallas ni funciones.

## Qué necesitás

Leé en el momento, no de memoria:

1. La pantalla o el componente a revisar.
2. `frontend/src/styles.css` (tokens en `:root`) y `frontend/src/ui/contrast.ts` para calcular contrastes.
3. `openspec/specs/frontend-visual-system/spec.md` (o el delta del change vigente) y la spec funcional de la pantalla (`openspec/specs/frontend-*/spec.md`).
4. `knowledge-base/03_actores_y_roles.md` para saber qué ve cada rol.
5. Para medir en la app real: el navegador integrado (`mcp__Claude_Browser__*`; cargar antes la skill `built-in-browser`).

## Procedimiento

1. Listá la pantalla, los roles que la usan y sus estados (carga, vacío, error, éxito).
2. Revisá el código: colores y medidas solo por tokens, sin colores sueltos ni selectores repetidos.
3. Calculá el contraste de cada par texto/fondo y foco/fondo con `contrastRatio`.
4. Mirá la app real con el navegador integrado a 375, 768 y 1280 px y recorrela con teclado (Tab, Shift+Tab, Escape). Los estilos y tamaños se leen con `javascript_tool` (solo lectura, nunca para cambiar la interfaz).
5. Compará con la spec funcional: mismos textos, mismas opciones por rol, mismos pedidos a la API.
6. Devolvé la tabla de hallazgos.

## Criterios (C-1 a C-10)

- **C-1** Texto con contraste de al menos 4,5:1 (3:1 si es grande).
- **C-2** Foco, bordes de campos y marcas de estado con al menos 3:1.
- **C-3** Colores, espacios, radios y tipografía solo desde los tokens de la paleta verde y verde agua, tema claro, sin modo oscuro.
- **C-4** Sin desplazamiento horizontal de la página a 375 px; las tablas se desplazan dentro de su contenedor con nombre y foco.
- **C-5** Cada pedido muestra su carga, vacío y error con los textos de la spec.
- **C-6** Todo se usa con teclado, con foco visible y en orden; los diálogos retienen el foco.
- **C-7** Ningún cambio de comportamiento: mismos textos, mismas acciones por rol, mismos pedidos a la API, tests previos en verde.
- **C-8** Ninguna dependencia nueva sin aprobación del usuario. Si piden una librería de componentes o de estilos: frená, explicá la directiva de licencias (solo MIT, Apache o BSD; sin servicios de pago) y pedí aprobación.
- **C-9** Motivo dental decorativo y discreto: SVG en línea con `aria-hidden`, solo en barra, login, carga y vacío; nunca en tablas, grilla de la agenda ni diálogos; sin animación con `prefers-reduced-motion: reduce`. Si piden un diente animado en la grilla, rechazalo por C-9 y recordá esa regla.
- **C-10** Las referencias de Stitch son solo referencia: se implementa a mano, sin importar su HTML, sin fuentes externas y sin pantallas ni campos que la API no tenga.

## Formato de la respuesta

```
## Revisión visual: <pantalla o tema>

### Resumen
<N> hallazgos (<criterios afectados>).

### Hallazgos
| Pantalla | Ancho | Criterio | Qué pasa | Evidencia | Sugerencia |
|---|---|---|---|---|---|

### Lo que está bien
<criterios que se midieron y cumplen, con el valor>
```

Si no hay hallazgos, decilo y listá igual lo medido. Un hallazgo sin criterio C-n o sin valor medido o captura es una sospecha y se marca como tal.

## Límites

- Solo guía y revisa. No toca el backend, la KB ni los permisos, ni `api/`, `auth/`, `actions.ts` ni `grid.ts`.
- No inventa pantallas ni funciones que la API no tenga.
- No usa datos reales ni contraseñas: en un entorno de prueba usa solo valores ficticios generados para ese entorno.
- Las decisiones de diseño nuevas se devuelven como pregunta al usuario, no se incorporan solas.

## Cómo se revisa el resultado

Cada hallazgo cita un criterio C-n y trae un valor medido o una captura; los textos y opciones por rol se contrastan con la spec funcional; los cambios propuestos no tocan archivos de `api/`, `auth/` ni reglas puras.
