# Proposal: C-15 `public-patient-booking` — turnos online para pacientes, sin login, con confirmación por email

## Why

Hoy solo la recepción y el administrador pueden sacar un turno: el paciente tiene que llamar o escribir al consultorio. Con la agenda sin superposiciones, el cálculo de franjas, los emails y los recordatorios ya funcionando (C-05 a C-14), se puede abrir una página pública para que el paciente reserve solo, sin cuenta y sin servicios externos nuevos. Para que nadie reserve con el DNI de otro ni llene la agenda con reservas falsas, la reserva queda pendiente hasta que se confirma desde el email del dueño del DNI.

## What Changes

- **Página pública nueva** (`/turnos`): el paciente elige profesional, día y franja libre, completa DNI, nombre, apellido, email y teléfono opcional, y envía. No usa token ni variables `VITE_` con secretos. La respuesta es siempre "Te enviamos un email para confirmar el turno", sea un DNI nuevo o uno existente con nombre coincidente.
- **Identificación por DNI y nombre (DD-129)**: si el DNI ya existe, el nombre y el apellido escritos tienen que coincidir con la ficha (sin distinguir mayúsculas, tildes ni espacios de más). Si coinciden, el turno se vincula a esa ficha sin modificar ningún dato. Si no coinciden, no se escribe nada, no se muestra ningún dato de la ficha y se responde "Verifique sus datos ingresados" con el mismo rechazo genérico que los demás. Se quita el paso "¿Es usted J*** P***?" (DD-128, reemplazada).
- **Reserva pendiente de confirmación (DD-130)**: toda reserva online se crea pendiente, retiene la franja (el constraint `ex_appointments_no_overlap` la cubre igual) y manda un email con un enlace de un solo uso al email de la ficha (DNI existente) o al escrito (DNI nuevo). Recién al confirmar se envía la confirmación de C-11 y el turno entra en los recordatorios de C-12.
- **Enlace de confirmación (DD-131)**: token impredecible del que solo se guarda el hash, de un solo uso y con vencimiento. El enlace abre `/turnos/confirmar`, que hace un `POST` público (nunca un `GET` con efectos).
- **Plazo (DD-132, DD-134)**: la reserva se puede confirmar durante 60 minutos (`ONLINE_BOOKING_HOLD_MINUTES`). El vencimiento automático, que cancela el turno, libera la franja y avisa por email, va en C-16 `online-booking-expiry` (DD-139), que depende de este change. Hasta C-16, un pendiente vencido ya no se puede confirmar, la recepción lo cancela a mano y no sale ningún email de cancelación.
- **Pantallas claras (DD-137)**: "Turno registrado exitosamente" (pendiente de confirmación, con el plazo), con un texto idéntico para un DNI nuevo y uno existente; "Turno confirmado"; y "Enlace no válido".
- **Recepción (DD-133)**: ve los pendientes con la etiqueta "Pendiente de confirmación" y los puede cancelar; los turnos online confirmados llevan "Online". La recepción y el administrador siguen agendando exactamente como hoy.
- **Endpoints públicos bajo `/api/v1/public/`** (profesionales, franjas, reservar, confirmar) sin JWT, con límite de pedidos por IP en el Redis existente, campo trampa y validación estricta. Se excepciona la regla dura 4 y se actualizan `CLAUDE.md`, `AGENTS.md`, la KB y la spec `access-control`.
- **KB**: los turnos online sin login pasan al alcance; el login de pacientes sigue afuera.

## Capabilities

### New Capabilities
- `public-booking`: reglas y casos de uso de la reserva online (profesionales y franjas ofrecidos, identificación por DNI y nombre, reserva pendiente, confirmación por enlace y vencimiento).
- `public-booking-api`: endpoints `/api/v1/public/*`, entrada y salida, límite de pedidos, campo trampa y errores.
- `frontend-public-booking`: páginas públicas `/turnos` y `/turnos/confirmar`, sin sesión.

### Modified Capabilities
- `access-control`: las rutas `/api/v1/public/*` se suman a las públicas en el inventario y en la matriz.
- `database-schema`: usuario creador opcional y datos de la reserva pendiente en el turno.
- `appointment-api`: las respuestas de turnos informan origen y si está pendiente de confirmación.
- `appointment-use-cases`: qué puede hacer la recepción con un turno pendiente.
- `reminder-scheduling`: un turno pendiente no recibe recordatorio.
- `notification-tasks`: tarea nueva del email de verificación.
- `email-templates`: email nuevo para confirmar la reserva.
- `runtime-configuration`: variables nuevas `ONLINE_BOOKING_HOLD_MINUTES` y `PUBLIC_APP_URL`.
- `frontend-auth`: las páginas públicas se abren sin sesión.
- `frontend-agenda`: etiquetas "Pendiente de confirmación" y "Online".
- `frontend-appointment-management`: acciones de la recepción sobre un pendiente.

## Impact

- **Backend**:
  - `app/application/public_booking.py` (nuevo), que reutiliza `validated_end`, la carga de contexto y `compute_slots`.
  - En el dominio: comparación de nombres, token y hash, y el puerto `RateLimiter`.
  - Las rutas en `app/api/public.py`.
  - En Celery: la tarea de verificación.
  - Migración `0003` y dos variables de entorno nuevas.
- **Frontend**: dos rutas públicas, un cliente de API sin token y las etiquetas en la agenda y el detalle.
- **Docs**:
  - `CLAUDE.md` y `AGENTS.md`.
  - `CHANGES.md`, con las entradas C-15 y C-16.
  - La KB: 01, 03, 04, 05, 06, 07, 08, 09 (DD-129 en adelante), 10 y 11.
- **Dependencias**: ninguna nueva (`secrets` y `hashlib` son de la biblioteca estándar; el cliente de Redis ya viene con `celery[redis]`). Sin cuentas ni proveedores de correo: Mailpit en desarrollo y demo.
- **Governance**: el acceso es ALTO/CRÍTICO, porque hay endpoints sin sesión que escriben pacientes y turnos. Las decisiones ya están todas tomadas (DD-129 a DD-139).
