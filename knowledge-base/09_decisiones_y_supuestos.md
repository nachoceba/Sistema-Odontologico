# Decisiones y Supuestos

## Decisiones documentadas

### DD-01 — Stack impuesto por la cátedra
**Decisión**: backend Python + FastAPI, JWT, SQLAlchemy, PostgreSQL, Redis (funciones asincrónicas) y Docker / Docker Compose; frontend React + TypeScript + Vite.
**Contexto**: el stack lo definió el profesor de la cátedra. La primera versión de esta KB usaba Next.js + Supabase + Resend + Vercel y se reemplazó por completo.
**Alternativas consideradas**: Next.js + Supabase (descartada: fuera del stack pedido).
**Justificación**: cumple la consigna del trabajo y es 100 % gratuito (PostgreSQL, Redis y Mailpit corren en contenedores).
**Trade-offs aceptados**: hay que construir autenticación, autorización y migraciones que Supabase daba hechas; no hay RLS como segunda barrera de seguridad.

### DD-02 — Reglas en dominio, refuerzo en base de datos
**Decisión**: las reglas viven en `domain/` como funciones puras; PostgreSQL las refuerza con constraints. La autorización por rol se hace solo en la capa de aplicación.
**Contexto**: la prioridad de calidad elegida es la mantenibilidad.
**Alternativas consideradas**: dejar la lógica en funciones SQL y políticas de fila (RLS) de PostgreSQL.
**Justificación**: la lógica en Python (funciones puras de `domain/`) se testea con pytest y evoluciona mejor que en SQL.
**Trade-offs aceptados**: hay que mantener coherentes dominio y constraints (mitigado con tests de integración); sin RLS, cada endpoint necesita un test de permisos por rol.

### DD-03 — Slots fijos de duración única
**Decisión**: todos los turnos duran `slot_minutes` (30 por defecto).
**Contexto**: bloquea el modelo de datos y el algoritmo de disponibilidad.
**Alternativas consideradas**: duración por tipo de tratamiento; duración libre.
**Justificación**: menor complejidad para el MVP y sin catálogo de prestaciones.
**Trade-offs aceptados**: los tratamientos largos requieren varios turnos consecutivos.

### DD-04 — Constraint de exclusión para no superposición
**Decisión**: `EXCLUDE USING gist` sobre `(professional_id, tstzrange)` para turnos `scheduled`.
**Justificación**: es la única garantía sólida ante concurrencia entre recepcionistas.
**Trade-offs aceptados**: requiere la extensión `btree_gist`.

### DD-05 — Cancelar no borra
**Decisión**: cancelar es un cambio de estado (`cancelled`).
**Justificación**: conserva el historial y libera el slot al salir del constraint.

### DD-06 — Emails al agendar y recordatorio previo
**Decisión**: confirmación inmediata y un recordatorio antes del turno, ambos informativos.
**Alternativas consideradas**: recordatorio con confirmar/cancelar mediante token.
**Trade-offs aceptados**: el paciente no puede actuar desde el email; se consume más cuota de email.

### DD-07 — El MVP se aparta del MVP recomendado por el informe de Discovery
**Decisión**: v1 incluye pacientes, agenda por profesional, login con roles y recordatorios por email. El informe de Discovery (sección D.3) recomendaba como imprescindibles, además: agenda multi-sillón con duración por prestación, reserva online por enlace, recordatorios por WhatsApp, ficha con odontograma, exportación de datos y registro de auditoría de accesos.
**Contexto**: presupuesto cero, plazo de cursada y alcance de un único ciclo de desarrollo por change.
**Alternativas consideradas**: seguir el MVP del informe completo.
**Justificación**: el producto queda enfocado en el caso de uso principal (agendar sin superposiciones) y se puede terminar y defender. Los sistemas competidores relevados con precio publicado cobran desde ARS 32.800 por profesional al mes hasta ARS 222.999 (plan de hasta 10 profesionales); un sistema gratuito y acotado ocupa el hueco de consultorios chicos.
**Trade-offs aceptados**: v1 no alcanza la paridad de mercado en ficha clínica, reserva online ni WhatsApp. Ver `10_preguntas_abiertas.md`.

### DD-08 — Sillones o boxes y duración por prestación quedan fuera de v1
**Decisión**: se agenda por profesional con slot único (RN-TU-09, RN-TU-10).
**Contexto**: el informe marca la agenda real por sillón, con duración por prestación y sobreturnos controlados, como una oportunidad de innovación poco evidenciada en el mercado argentino.
**Justificación**: modelar sillones y prestaciones cambia el esquema, el algoritmo de disponibilidad y el roadmap. Se deja como primera mejora posterior.
**Trade-offs aceptados**: no se detectan conflictos de sillón entre profesionales.

### DD-09 — Recordatorios por email en lugar de WhatsApp
**Decisión**: v1 envía recordatorios por email (servidor SMTP) y no por WhatsApp.
**Contexto**: el informe muestra que el recordatorio por WhatsApp ya es estándar en el mercado argentino (Bilog, ClinIA, Livio, iAsistemas, DrApp, Dentalink, Dentiqa y otros). La API oficial de WhatsApp Business cobra por conversación y exige aprobación de plantillas.
**Justificación**: la restricción de costo cero descarta la API oficial.
**Trade-offs aceptados**: menor alcance que los competidores. Se evalúa un enlace `wa.me` manual como complemento posterior.

### DD-10 — Celery + Redis para las tareas asincrónicas
**Decisión**: Redis como broker y Celery (worker + Beat) para enviar emails y programar el recordatorio diario.
**Contexto**: la cátedra pide Redis "para las funcionalidades asincrónicas que correspondan".
**Alternativas consideradas**: ARQ o RQ (más livianos); tareas en segundo plano de FastAPI (no sobreviven a un reinicio ni programan en el tiempo).
**Justificación**: Celery es el estándar más documentado y trae programación (Beat) sin agregar otro servicio.
**Trade-offs aceptados**: dos contenedores más (`worker` y `beat`). La elección de Celery es una propuesta a confirmar con la cátedra.

### DD-11 — JWT de acceso con expiración corta
**Decisión**: login en `POST /api/v1/auth/login` que devuelve un JWT firmado (HS256) con el rol; contraseñas con hash argon2 o bcrypt.
**Justificación**: pedido por la cátedra; simple y sin estado en el servidor.
**Trade-offs aceptados**: no se puede revocar un token antes de que venza; se mitiga con una vida corta. El refresh token queda como decisión abierta (SU-07).

### DD-12 — Email por SMTP con Mailpit en desarrollo
**Decisión**: el adaptador de email usa SMTP estándar detrás del puerto `EmailSender`; en desarrollo, Mailpit recibe todos los correos.
**Justificación**: sin cuentas ni costos durante el desarrollo; el proveedor de producción se puede cambiar sin tocar el dominio.
**Trade-offs aceptados**: el proveedor SMTP gratuito de demo queda por definir (SU-02).

### DD-13 — SQLAlchemy 2.0 síncrono y Alembic
**Decisión**: acceso síncrono a la base (endpoints `def`) y migraciones con Alembic.
**Justificación**: menos complejidad que async para un MVP; FastAPI ejecuta los endpoints síncronos en un pool de hilos.
**Trade-offs aceptados**: menor rendimiento con mucha concurrencia, irrelevante para un consultorio.

### DD-14 — Anticipación mínima de 6 horas, configurable
**Decisión**: un turno solo se puede crear si empieza al menos `min_notice_hours` después del momento actual (RN-TU-12); el valor por defecto es 6 horas y se guarda en `clinic_settings.min_notice_hours`. El límite exacto se acepta. Reemplaza en la práctica a "no en el pasado" (RN-TU-04).
**Contexto**: el doctor y el consultorio necesitan tiempo para organizarse antes de cada turno. Surgió al proponer el change `crear-turno-sin-solapamientos`.
**Alternativas consideradas**: solo prohibir el pasado (sin margen); 12 horas fijas.
**Justificación**: 6 horas alcanzan para un consultorio con agenda tranquila; uno con la agenda muy llena puede subirlo a 12 horas sin tocar código.
**Trade-offs aceptados**: no se pueden cargar turnos urgentes del mismo día con menos margen; queda como pregunta abierta quién podría saltar la regla.

## Supuestos inferidos

### SU-01 — Zona horaria única
**Supuesto**: el consultorio opera en `America/Argentina/Buenos_Aires`.
**Origen**: contexto de la cursada y mención de normativa de datos personales; no fue confirmado.
**Riesgo si es falso**: horarios y recordatorios corridos.
**Cómo validar**: confirmar la zona con el usuario.

### SU-02 — Proveedor SMTP gratuito para producción o demo
**Supuesto**: existe un servidor SMTP gratuito (por ejemplo una cuenta de correo con contraseña de aplicación, o el plan gratuito de un servicio de email) con cupo suficiente para un consultorio.
**Origen**: conocimiento general; no verificado. En desarrollo no hace falta: Mailpit cubre todo.
**Riesgo si es falso**: el envío real no funciona en la demo; se mostraría con Mailpit.
**Cómo validar**: elegir el proveedor y revisar su cupo antes del change de email.

### SU-03 — Un recordatorio diario alcanza
**Supuesto**: Celery Beat dispara la tarea cada hora y esta actúa solo a la hora configurada; el recordatorio sale una vez al día, el día anterior, no exactamente 24 h antes.
**Origen**: decisión de simplicidad para v1; Beat permite cualquier frecuencia sin costo.
**Riesgo si es falso**: si se exige envío exacto a 24 h, se pasa a una tarea horaria con ventana de tiempo.
**Cómo validar**: preguntar al dueño del consultorio.

### SU-04 — Un solo consultorio
**Supuesto**: no hay multi-tenant; una sola sede.
**Origen**: Discovery (escala de un consultorio).
**Riesgo si es falso**: rediseño del modelo y de los permisos.

### SU-05 — Varios turnos por paciente el mismo día
**Supuesto**: se permiten (RN-TU-08).
**Riesgo si es falso**: agregar una regla y una validación más.
**Cómo validar**: preguntar al usuario.

### SU-06 — Solo el administrador edita horarios
**Supuesto**: recepción solo consulta horarios.
**Riesgo si es falso**: cambiar la matriz RBAC.
**Cómo validar**: preguntar al usuario.

### SU-07 — Sin refresh token en v1
**Supuesto**: alcanza con un token de acceso de 30 minutos; al vencer, el usuario vuelve a iniciar sesión.
**Origen**: simplicidad del MVP.
**Riesgo si es falso**: la recepción se molesta por reingresar; se agrega un refresh token.
**Cómo validar**: probar con una recepcionista real.
