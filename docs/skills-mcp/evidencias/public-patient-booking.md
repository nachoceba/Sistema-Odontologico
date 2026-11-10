# Evidencia de C-15 `public-patient-booking`

## Consulta con Context7 (task 6.1)

- Biblioteca: `redis-py` (`/redis/redis-py`), consultada con `resolve-library-id` y después `query-docs`.
- Pregunta: cómo agrupar `INCR` y `EXPIRE` en una tubería y qué devuelve `execute()`.
- Respuesta: `pipeline(transaction=True)` encola los comandos, los ejecuta juntos con `execute()` y devuelve una lista con el resultado de cada uno; se usa como administrador de contexto.
- Efecto en el diseño: `RedisRateLimiter` hace `incr(clave)` y `expire(clave, ventana)` en una tubería transaccional y toma el primer resultado como contador. La consulta no incluyó código propio ni datos de pacientes.

## Revisión visual de las páginas públicas (task 8.9)

Skill `diseno-ui-odontologico`, navegador integrado en `localhost` con la base de desarrollo (datos ficticios). Sin pedidos a dominios externos: solo `localhost:5173` y `localhost:8000`.

| Pantalla | Ancho | Criterio | Medida |
|---|---|---|---|
| `/turnos` (profesional, día, franjas, formulario) | 375 px | C-4 | `scrollWidth` 375 sobre un ancho de 375: sin desplazamiento horizontal |
| `/turnos` | 375 px | C-2 | Controles medidos (botones, campos y selector): el menor mide 39 px de alto o ancho, por encima de 24 px |
| `/turnos` | 375 px | C-1 | Botón "Reservar turno" 5,73:1; texto de ayuda 6,19:1 |
| `/turnos` | 375 px | C-6 | El campo trampa está a -10000 px del borde izquierdo y fuera del orden de Tab |
| `/turnos` | 768 px | C-4 | `scrollWidth` 753 con ventana de 768: sin desplazamiento horizontal; columna de 672 px |
| `/turnos` | 1280 px | C-4 | `scrollWidth` 1265 con ventana de 1280: sin desplazamiento horizontal; columna de 672 px |
| `/turnos/confirmar` | 1280 px | C-2 | Botón "Confirmar mi turno" 169 × 39 px; el enlace "Reservar un turno" medía 125 × 22 px, por debajo de 24 px: se corrigió con `min-height: 1.5rem` y relleno vertical |
| `/turnos/confirmar` | 1280 px | C-5 y C-6 | Con un enlace inexistente sale "Enlace no válido", el foco queda en el título, el enlace apunta a `/turnos` y la dirección ya no tiene el fragmento |

Los pares de color nuevos (etiquetas "Online" y "Pendiente de confirmación") usan los tokens `--color-primary` / `--color-primary-soft` y `--color-pending` / `--color-pending-bg`, que ya están cubiertos por los pares de `ui/tokens.ts`. Al terminar se volvió a `preset: "desktop"`.
