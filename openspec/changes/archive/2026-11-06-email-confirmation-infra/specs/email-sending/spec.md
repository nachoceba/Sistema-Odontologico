# Spec Delta

## Purpose

Definir cómo el sistema entrega un email ya armado a un servidor SMTP (Mailpit en desarrollo y en la demo), cómo clasifica los fallos y qué datos nunca pueden quedar en errores ni registros, de modo que cambiar de servidor SMTP no toque el dominio (DD-12, SU-02).

## ADDED Requirements

### Requirement: Envío por SMTP configurable sin tocar el código (DD-12, SU-02)

El sistema SHALL enviar cada email por SMTP al servidor indicado por `SMTP_HOST` y `SMTP_PORT`, con remitente `EMAIL_FROM`, un solo destinatario, asunto y cuerpo en texto plano UTF-8. Si `SMTP_USE_TLS` es verdadero MUST negociar STARTTLS antes de autenticarse; si `SMTP_USER` no está vacío MUST autenticarse con `SMTP_USER` y `SMTP_PASSWORD`; con `SMTP_USER` vacío MUST NOT intentar autenticarse. Cada conexión MUST tener un timeout de a lo sumo 10 segundos, de modo que un servidor colgado no deje al worker esperando sin límite. Apuntar a otro servidor SMTP MUST requerir solo cambiar variables de entorno.

#### Scenario: Envío a Mailpit en desarrollo (esperado)
- **WHEN** con `SMTP_HOST = mailpit`, `SMTP_PORT = 1025`, `SMTP_USE_TLS = false` y `SMTP_USER` vacío se envía un email a `juan.perez@example.com`
- **THEN** Mailpit recibe un mensaje de `EMAIL_FROM` para `juan.perez@example.com` con el asunto y el cuerpo pedidos, y no hubo intento de autenticación

#### Scenario: Servidor con STARTTLS y usuario (esperado)
- **WHEN** con `SMTP_USE_TLS = true` y `SMTP_USER` completo se envía un email
- **THEN** la conexión negocia STARTTLS, después se autentica con `SMTP_USER` y `SMTP_PASSWORD`, y recién entonces entrega el mensaje

#### Scenario: Acentos y eñes (borde)
- **WHEN** el cuerpo contiene "Peña", "Gómez" y "miércoles"
- **THEN** el mensaje recibido muestra esos textos sin caracteres corruptos

#### Scenario: Servidor que no responde (borde)
- **WHEN** el servidor SMTP acepta la conexión pero no responde
- **THEN** el envío termina con un fallo temporal en a lo sumo 10 segundos por intento de conexión

### Requirement: Fallos clasificados en temporales y permanentes

Un envío que no se completa SHALL terminar en un fallo clasificado como **temporal** (no se pudo conectar, timeout, conexión cortada, respuesta SMTP 4xx) o **permanente** (respuesta SMTP 5xx, destinatario o remitente rechazado, autenticación rechazada). La clasificación MUST estar disponible para quien decide si reintentar (spec `notification-sending`).

#### Scenario: Servidor caído (esperado)
- **WHEN** no hay ningún servidor escuchando en `SMTP_HOST:SMTP_PORT`
- **THEN** el envío termina con un fallo temporal

#### Scenario: Destinatario rechazado (error de negocio)
- **WHEN** el servidor responde 550 al destinatario
- **THEN** el envío termina con un fallo permanente

#### Scenario: Credenciales rechazadas (error de negocio)
- **WHEN** el servidor responde 535 a la autenticación
- **THEN** el envío termina con un fallo permanente

#### Scenario: Servidor ocupado (borde)
- **WHEN** el servidor responde 451 al mensaje
- **THEN** el envío termina con un fallo temporal

### Requirement: Errores y registros sin datos personales ni secretos (DD-77, RN-PR-03, regla dura 5)

El texto de error de un fallo de envío SHALL ser un código corto del sistema más, si existe, el código numérico SMTP (por ejemplo `SMTP_PERMANENT 550` o `SMTP_TEMPORARY CONNECTION`), de a lo sumo 200 caracteres. MUST NOT contener la dirección del destinatario, nombres del paciente, el texto devuelto por el servidor, `SMTP_USER` ni `SMTP_PASSWORD`. Los registros del worker sobre envíos MUST llevar solo identificadores de notificación y de turno, el tipo y el resultado.

#### Scenario: Rechazo que repite la dirección (borde)
- **WHEN** el servidor responde `550 5.1.1 <juan.perez@example.com>: Recipient address rejected`
- **THEN** el error guardado es `SMTP_PERMANENT 550` y no contiene `juan.perez@example.com`

#### Scenario: Fallo de autenticación (borde)
- **WHEN** la autenticación falla con una contraseña configurada
- **THEN** ni el error guardado ni el registro del worker contienen la contraseña ni el usuario SMTP

#### Scenario: Envío correcto en el registro (esperado)
- **WHEN** un envío sale bien
- **THEN** el registro del worker indica el id de la notificación, el id del turno, el tipo y "enviado", sin email ni nombre del paciente

### Requirement: Redirección de destinatarios para la demo (P-2)

Si la variable opcional `EMAIL_REDIRECT_TO` tiene una dirección, el sistema SHALL enviar todos los emails a esa dirección en lugar de al paciente, y el cuerpo MUST empezar con la línea "Email de demostración: en producción se enviaría al paciente del turno." sin incluir la dirección original. Vacía (valor por defecto) MUST enviar al email del paciente. Una dirección mal formada en `EMAIL_REDIRECT_TO` MUST impedir que la configuración arranque, nombrando la variable y sin repetir el valor. Así ninguna demo escribe a buzones de terceros (`11_recordatorios_email.md` §Límites y riesgos).

#### Scenario: Demo con redirección (esperado)
- **WHEN** `EMAIL_REDIRECT_TO = equipo.demo@example.org` y se envía la confirmación de un turno de Juan Perez (`juan.perez@example.com`)
- **THEN** el mensaje llega a `equipo.demo@example.org`, empieza con la línea de demostración y no contiene `juan.perez@example.com`

#### Scenario: Sin redirección (esperado)
- **WHEN** `EMAIL_REDIRECT_TO` está vacía y se envía la misma confirmación
- **THEN** el mensaje llega a `juan.perez@example.com` y no tiene la línea de demostración

#### Scenario: Dirección de redirección inválida (error)
- **WHEN** `EMAIL_REDIRECT_TO = no-es-un-email` al arrancar
- **THEN** la configuración falla con un error que nombra `EMAIL_REDIRECT_TO` y no repite el valor
