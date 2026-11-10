# frontend-public-booking Specification

## Purpose
Páginas públicas del frontend donde el paciente, sin iniciar sesión, elige profesional y franja libre, deja sus datos y después confirma la reserva desde el enlace que le llega por email.

## Requirements

### Requirement: Páginas públicas sin sesión (P-8)

El frontend SHALL ofrecer las páginas `/turnos` y `/turnos/confirmar`. Las dos se abren con o sin sesión y nunca redirigen a `/login`. Nunca MUST enviar el encabezado `Authorization` ni leer el token guardado. Un 401 o 403 de la API MUST NOT cerrar la sesión de la recepción si estuviera abierta en el mismo navegador. Las páginas MUST usar solo `VITE_API_URL` como configuración y los tokens visuales de `frontend-visual-system`: contraste, foco, y anchos de 375, 768 y 1280 px sin desplazamiento horizontal.

#### Scenario: Paciente sin sesión abre la página (esperado)
- **WHEN** alguien sin token abre `/turnos`
- **THEN** ve la lista de profesionales para reservar, sin la barra de navegación interna

#### Scenario: Pedidos sin token (borde)
- **WHEN** la recepción tiene sesión en el navegador y abre `/turnos`
- **THEN** ningún pedido de la página lleva `Authorization`

#### Scenario: Ancho de teléfono (borde)
- **WHEN** las páginas se ven a 375 px
- **THEN** no hay desplazamiento horizontal y cada control mide al menos 24 × 24 px

### Requirement: Elegir profesional, día y franja

La página `/turnos` SHALL mostrar los profesionales ofrecidos. Al elegir uno, MUST mostrar un selector de día limitado a hoy y los 13 días siguientes, y las franjas reservables de ese día como botones con la hora local del consultorio. Sin franjas MUST mostrar "No hay horarios libres para este día. Pruebe con otro." Cada pedido MUST mostrar su estado de carga y de error.

#### Scenario: Franjas de un día (esperado)
- **WHEN** el paciente elige a la Dra. A y el día de mañana
- **THEN** ve las franjas reservables como botones con la hora local, por ejemplo "10:30"

#### Scenario: Día sin franjas (borde)
- **WHEN** el día elegido no tiene franjas reservables
- **THEN** ve "No hay horarios libres para este día. Pruebe con otro."

#### Scenario: Error al cargar (error)
- **WHEN** la API no responde al pedir franjas
- **THEN** ve un aviso de error con la opción de reintentar

### Requirement: Datos del paciente y envío de la reserva (DD-129, DD-130)

Después de elegir la franja, la página SHALL pedir siempre DNI, nombre, apellido y email (obligatorios) y teléfono (opcional), sin consultar antes si el DNI existe y sin mostrar nunca ningún dato de una ficha. El formulario MUST incluir el campo trampa `website`, oculto para personas y para lectores de pantalla y fuera del orden de Tab. El botón de enviar MUST quedar deshabilitado mientras se envía. Los rechazos MUST mostrar estos textos:

- `BOOKING_NOT_POSSIBLE`: "Verifique sus datos ingresados.", con los datos todavía en el formulario.
- `SLOT_TAKEN` y `SLOT_UNAVAILABLE`: "Ese horario ya no está disponible. Elija otro.", con las franjas del día recargadas.
- `TOO_MANY_REQUESTS`: "Hizo muchos intentos. Espere un rato y vuelva a probar."
- Cualquier otro: "No pudimos registrar el turno. Pruebe de nuevo más tarde."

#### Scenario: Datos que no coinciden (error de negocio)
- **WHEN** la API responde 409 `BOOKING_NOT_POSSIBLE`
- **THEN** ve "Verifique sus datos ingresados." y ningún dato que no haya escrito

#### Scenario: Otra persona tomó la franja (error de negocio, regla dura 6)
- **WHEN** la API responde 409 `SLOT_TAKEN`
- **THEN** ve "Ese horario ya no está disponible. Elija otro." y las franjas del día recargadas

#### Scenario: Demasiados intentos (error)
- **WHEN** la API responde 429
- **THEN** ve "Hizo muchos intentos. Espere un rato y vuelva a probar."

#### Scenario: Campo trampa invisible (borde)
- **WHEN** se recorre el formulario con Tab
- **THEN** el foco nunca llega al campo `website`

#### Scenario: Doble clic en enviar (borde)
- **WHEN** el paciente hace doble clic en "Reservar turno"
- **THEN** sale un solo pedido de reserva

### Requirement: Pantalla de turno registrado (DD-130, DD-137)

Cuando la API responde 202, la página SHALL reemplazar el formulario por un aviso de éxito con:

- el título "Turno registrado exitosamente";
- debajo, "Está pendiente de confirmación. Revise su email: tiene que confirmarlo con el enlace que le enviamos antes de las HH:MM.", con la hora local de `confirm_before`;
- el profesional, el día y la hora local del turno que el propio paciente eligió;
- "Si no lo confirma a tiempo, el horario se libera. Para cambiarlo o cancelarlo, comuníquese con el consultorio." (P-9).

El aviso MUST ser exactamente el mismo, texto por texto, para un DNI nuevo y para uno existente, y MUST NOT mostrar el email, el nombre ni ningún dato de la ficha. El foco MUST pasar al título para que lo anuncie el lector de pantalla.

#### Scenario: Turno registrado (esperado)
- **WHEN** la paciente elige a la Dra. A el lunes 09/11 a las 10:30 y la API responde 202 con `confirm_before` a las 13:00 locales
- **THEN** ve "Turno registrado exitosamente", "Está pendiente de confirmación. Revise su email: tiene que confirmarlo con el enlace que le enviamos antes de las 13:00.", "Dra. A" y "lunes 09/11/2026, 10:30"

#### Scenario: Mismo aviso para DNI nuevo y existente (borde)
- **WHEN** se compara el texto del aviso después de una reserva con DNI nuevo y el de una con DNI existente, para el mismo profesional, horario y vencimiento
- **THEN** los dos textos son idénticos

#### Scenario: Sin datos del paciente (borde)
- **WHEN** se muestra el aviso de turno registrado
- **THEN** no aparece el email, el nombre ni el documento escritos

#### Scenario: Foco en el título (borde)
- **WHEN** aparece el aviso
- **THEN** el foco queda en "Turno registrado exitosamente"

### Requirement: Confirmar desde el enlace del email (DD-131, DD-137)

La página `/turnos/confirmar` SHALL leer el token del fragmento de la dirección (`#token=...`) y mostrar el título "Confirmar su turno" con el botón "Confirmar mi turno". Al abrirse MUST NOT hacer ningún pedido con efectos. Solo al tocar el botón MUST enviar el `POST` de confirmación, y después MUST borrar el fragmento de la dirección. Según la respuesta:

- **Éxito:** el título "Turno confirmado" y "Su turno quedó confirmado. Le enviamos la confirmación por email.", con profesional, día y hora local.
- **`CONFIRMATION_LINK_INVALID` o sin token:** el título "Enlace no válido" y "El enlace no es válido, ya se usó o venció. Si todavía quiere el turno, vuelva a reservarlo.", con el enlace "Reservar un turno" a `/turnos`.
- **429:** el texto de muchos intentos.
- **Otro error:** "No pudimos confirmar el turno. Pruebe de nuevo más tarde.", con el botón todavía disponible.

#### Scenario: Abrir el enlace no confirma (borde)
- **WHEN** un previsualizador de email o el paciente abre `/turnos/confirmar#token=abc`
- **THEN** no sale ningún `POST` hasta tocar "Confirmar mi turno"

#### Scenario: Confirmación exitosa (esperado)
- **WHEN** el paciente toca "Confirmar mi turno" y la API responde 200 con la Dra. A el lunes 09/11 a las 10:30
- **THEN** ve "Turno confirmado", "Su turno quedó confirmado. Le enviamos la confirmación por email.", "Dra. A" y "lunes 09/11/2026, 10:30", y la dirección ya no tiene el token

#### Scenario: Enlace vencido o usado (error)
- **WHEN** la API responde 410 `CONFIRMATION_LINK_INVALID`
- **THEN** ve "Enlace no válido" y "El enlace no es válido, ya se usó o venció. Si todavía quiere el turno, vuelva a reservarlo." con el enlace a `/turnos`

#### Scenario: Sin token en la dirección (borde)
- **WHEN** alguien abre `/turnos/confirmar` sin fragmento
- **THEN** ve el mismo aviso de enlace no válido y no sale ningún pedido

#### Scenario: Error del servidor (error)
- **WHEN** la API responde 500 al confirmar
- **THEN** ve "No pudimos confirmar el turno. Pruebe de nuevo más tarde." y puede volver a tocar el botón

### Requirement: Elegir el tratamiento después del profesional (C-17)

En `/turnos`, después de elegir el profesional, la página SHALL mostrar el paso "Tratamiento" con los tratamientos públicos de ese profesional como botones (`aria-pressed`), y recién con un tratamiento elegido MUST mostrar el día y las franjas. Cambiar de profesional MUST borrar el tratamiento y la franja elegidos. Cambiar de tratamiento MUST conservar el día y borrar la franja. La reserva MUST enviar `treatment_id`. El texto "Turno elegido" del formulario MUST incluir el tratamiento. Ante `TREATMENT_NOT_AVAILABLE`, la página MUST mostrar "El tratamiento elegido ya no está disponible. Elija otro.", volver a pedir los tratamientos, borrar el tratamiento elegido y conservar los datos escritos del formulario. La lista de tratamientos MUST mostrar su carga y su error con reintento, como los profesionales.

#### Scenario: Elegir tratamiento (esperado)
- **WHEN** el paciente elige a la Dra. A
- **THEN** ve "Consulta", "Limpieza dental" y los demás que ofrece, y todavía no ve los días ni las franjas

#### Scenario: Franjas después del tratamiento (esperado)
- **WHEN** el paciente elige "Limpieza dental"
- **THEN** ve el selector de día y las franjas, y el turno elegido dice "Dra. Ana Alvarez, Limpieza dental, <día y hora>"

#### Scenario: Cambiar de profesional (borde)
- **WHEN** el paciente eligió a la Dra. A y "Blanqueamiento" y después elige al Dr. B
- **THEN** no queda ningún tratamiento ni franja elegidos y ve los tratamientos del Dr. B

#### Scenario: Tratamiento que dejó de estar disponible (error de negocio)
- **WHEN** el paciente envía la reserva y la API responde `TREATMENT_NOT_AVAILABLE`
- **THEN** ve "El tratamiento elegido ya no está disponible. Elija otro.", la lista se vuelve a pedir y sus datos siguen escritos

#### Scenario: Error al cargar tratamientos (error)
- **WHEN** la API no responde al pedir los tratamientos
- **THEN** ve un aviso de error con la opción de reintentar

### Requirement: Tratamiento en las pantallas de resultado (C-17)

La pantalla "Turno registrado exitosamente" y la de "Turno confirmado" SHALL mostrar la fila "Tratamiento" con el nombre que devolvió la API, junto al profesional y al día y hora. En "Turno registrado" el texto MUST seguir siendo idéntico para un DNI nuevo y uno existente. En "Turno confirmado" la fila MUST omitirse si la API devuelve `treatment_name` nulo.

#### Scenario: Turno registrado con tratamiento (esperado)
- **WHEN** la reserva de "Limpieza dental" con la Dra. A responde 202
- **THEN** la pantalla muestra "Tratamiento: Limpieza dental" y no muestra email, nombre ni documento del paciente

#### Scenario: Turno confirmado con tratamiento (esperado)
- **WHEN** el paciente confirma desde el enlace
- **THEN** la pantalla "Turno confirmado" muestra el tratamiento

#### Scenario: Confirmación de una reserva sin tratamiento (borde)
- **WHEN** se confirma una reserva hecha antes de C-17
- **THEN** la pantalla "Turno confirmado" no muestra la fila de tratamiento
