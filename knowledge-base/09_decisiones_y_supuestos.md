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
**Trade-offs aceptados**: dos contenedores más (`worker` y `beat`). Confirmada por el usuario (no se consulta a la cátedra: son herramientas gratuitas dentro de la base del profesor); el esqueleto queda aislado en `infrastructure/tasks/`.

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

> DD-15 a DD-20 surgieron al preparar el change `calcular-slots-disponibles` (C-05b), que está preparado pero todavía no implementado. Detalle y alternativas descartadas en `openspec/changes/calcular-slots-disponibles/design.md`. Las decisiones marcadas "sin respaldo en la KB" son decisiones de diseño tomadas por el usuario en esa preparación.

### DD-15 — `compute_slots` devuelve el día local completo con tres estados
**Decisión**: la función recibe el profesional y la zona horaria del consultorio y devuelve las franjas del día local completo (00:00 a 24:00), con inicio y fin en UTC y estado `FREE`, `BUSY` u `OUTSIDE_HOURS`. Lo que no es un slot completo dentro de un tramo (incluido el resto de un tramo que no alcanza para un slot) y los días de licencia salen `OUTSIDE_HOURS`; no hay un cuarto estado. Dentro de un tramo la grilla se ancla al inicio del tramo; fuera de tramos las franjas se cuentan desde las 00:00 o desde el fin del tramo anterior y se recortan, de modo que solo las franjas `OUTSIDE_HOURS` pueden durar menos de `slot_minutes`.
**Contexto**: C-09 (vistas de agenda) necesita dibujar la grilla del día sin recalcular nada. Respaldo en la KB: RN-GL-01, RN-TU-03, RN-HO-03 y US-006 (tres estados). **Sin respaldo en la KB** sobre qué rango devuelve la función ni sobre la grilla fuera de tramos.
**Alternativas consideradas**: devolver solo del primer al último tramo; devolver solo las franjas dentro de tramos (lista vacía en un día sin horario); un estado `TIME_OFF` para la licencia.
**Justificación**: con el día completo, el día sin tramos y el de licencia tienen la misma forma que un día normal, y la lista es contigua, sin huecos ni solapes.
**Trade-offs aceptados**: hay franjas `OUTSIDE_HOURS` más cortas que un slot; la pantalla no distingue una licencia de un día sin atención.

### DD-16 — Solo `scheduled` ocupa una franja y la precedencia es `OUTSIDE_HOURS` > `BUSY` > `FREE`
**Decisión**: únicamente los turnos `scheduled` del mismo profesional marcan una franja `BUSY` (un turno cancelado la libera; `completed` y `no_show` no ocupan). Si una franja está fuera de horario o en licencia y además tiene un turno, sale `OUTSIDE_HOURS`. `compute_slots` no informa los conflictos de RN-HO-04: los lista C-07 y C-09 dibuja los turnos con su propia consulta.
**Contexto**: respaldo en RN-TU-01, RN-TU-05, DD-05 y el constraint de exclusión de `04_modelo_de_datos.md`. **La precedencia no tiene respaldo en la KB** (surgió de la revisión de escenarios, RN-HO-04).
**Alternativas consideradas**: que `completed` o `no_show` ocupen; que `BUSY` prevalezca sobre `OUTSIDE_HOURS`.
**Justificación**: el estado responde "¿se puede agendar acá?" y coincide con lo que la base permite agendar.
**Trade-offs aceptados**: un turno cargado antes de una licencia no se ve como ocupado en las franjas.

### DD-17 — `compute_slots` no aplica la anticipación mínima
**Decisión**: la función no recibe la hora actual ni `min_notice_hours`; la anticipación (RN-TU-12, DD-14) la sigue aplicando `validate_appointment`.
**Contexto**: complementa DD-14. Respaldo en RN-TU-12 y en el alcance de C-05 de `CHANGES.md`.
**Alternativas consideradas**: pasar la hora actual y marcar las franjas con poca anticipación como no libres; un cuarto estado.
**Justificación**: mezclar una regla de creación con la de ocupación haría que la vista cambie con el reloj.
**Trade-offs aceptados**: la pantalla puede mostrar `FREE` una franja que la creación rechaza con `INSUFFICIENT_NOTICE`; C-10 debe mostrar ese mensaje.

### DD-18 — Las entradas inválidas lanzan `ValueError`
**Decisión**: `slot_minutes <= 0`, un `day` que no es fecha y un `datetime` pasado como `day` lanzan `ValueError`.
**Contexto**: misma convención que C-05a (datetime sin zona lanza `ValueError`). **Sin respaldo en la KB**: la KB no trata los errores de programación.
**Alternativas consideradas**: devolver una lista vacía.
**Justificación**: son errores del llamador, no motivos de negocio; una lista vacía los escondería. Un `datetime` se rechaza porque ignorar su hora en silencio mostraría el día equivocado.
**Trade-offs aceptados**: el llamador debe validar su entrada o capturar la excepción.

### DD-19 — Un turno que cruza la medianoche cuenta por solapamiento de instantes
**Decisión**: un turno existente se compara como rango de instantes UTC con cada franja, sin recortarlo al día pedido; si toca una franja, la marca `BUSY`.
**Contexto**: es la misma regla de solapamiento de RN-TU-01 y la que aplica el constraint de exclusión. **Sin respaldo en la KB** sobre la medianoche.
**Alternativas consideradas**: ignorar la parte del turno fuera del día pedido.
**Justificación**: sin casos especiales y coherente con la base de datos.
**Trade-offs aceptados**: ninguno relevante.

### DD-20 — Refactor de `validation.py` con helpers compartidos y zona horaria en `app/core/timezone.py`
**Decisión**: los helpers de grilla, licencia y solapamiento pasan a un módulo común del dominio y la conversión de hora a `app/core/timezone.py`; `validate_appointment` no cambia de comportamiento y sus 33 tests son la red de seguridad.
**Contexto**: **sin respaldo en la KB** (decisión de diseño). Respaldo en la regla dura 2 y en los patrones de `08_arquitectura_propuesta.md`.
**Alternativas consideradas**: duplicar la lógica y confiar en un test de coherencia.
**Justificación**: con dos copias de la misma regla, `compute_slots` podría marcar `FREE` algo que `validate_appointment` rechaza.
**Trade-offs aceptados**: se toca código ya archivado (en la implementación posterior), mitigado con los 33 tests en verde antes y después de cada paso.

### DD-21 — Un turno ya iniciado no se cancela (P-1)
**Decisión**: `scheduled` → `cancelled` solo si `now < starts_at`; después corresponde `completed` o `no_show` (`ALREADY_STARTED`).
**Contexto**: RN-TU-05 no limita el tiempo: sin respaldo en la KB (decisión del usuario).
**Alternativas consideradas**: Cancelar sin límite de tiempo.
**Justificación**: Evita que un turno vencido se cancele y oculte una ausencia.
**Trade-offs aceptados**: ninguno relevante; se reconsidera si C-07/C-08 lo exigen.

### DD-22 — `completed` y `no_show` son finales en v1 (P-2)
**Decisión**: Una vez registrada la asistencia no se corrige (`ATTENDANCE_ALREADY_RECORDED`); la corrección queda para después junto con la auditoría.
**Contexto**: RN-TU-07 solo declara final a `cancelled`: sin respaldo en la KB (decisión del usuario).
**Alternativas consideradas**: Permitir `completed` ↔ `no_show`.
**Justificación**: Sin auditoría, corregir en silencio pierde trazabilidad.
**Trade-offs aceptados**: ninguno relevante; se reconsidera si C-07/C-08 lo exigen.

### DD-23 — "Iniciado" significa `now >= starts_at` (P-3)
**Decisión**: El instante exacto del inicio cuenta como iniciado; la comparación es entre instantes UTC.
**Contexto**: US-010 dice "ya iniciados"; el borde exacto no tiene respaldo en la KB (decisión del usuario).
**Alternativas consideradas**: `now >= ends_at`.
**Justificación**: Permite registrar la asistencia mientras el turno está en curso.
**Trade-offs aceptados**: ninguno relevante; se reconsidera si C-07/C-08 lo exigen.

### DD-24 — Solo se reprograman turnos `scheduled` que no empezaron (P-4)
**Decisión**: `validate_reschedule_eligibility` rechaza `cancelled`, `completed`, `no_show` y turnos iniciados.
**Contexto**: RN-TU-06 habla solo del nuevo horario: sin respaldo en la KB (decisión del usuario).
**Alternativas consideradas**: Reprogramar también turnos iniciados.
**Justificación**: Coherente con DD-21.
**Trade-offs aceptados**: ninguno relevante; se reconsidera si C-07/C-08 lo exigen.

### DD-25 — RN-PA-04 aplica también al reprogramar; desactivar un paciente no cancela sus turnos futuros (P-5)
**Decisión**: El caso de uso C-08 aplica `check_patient_can_book` al crear y al reprogramar; al desactivar a un paciente, sus turnos `scheduled` futuros se listan, no se cancelan (como RN-HO-04).
**Contexto**: RN-PA-03, RN-PA-04, RN-TU-06: sin respaldo en la KB (decisión del usuario).
**Alternativas consideradas**: Cancelar en cascada.
**Justificación**: La cancelación automática afecta al paciente sin aviso.
**Trade-offs aceptados**: ninguno relevante; se reconsidera si C-07/C-08 lo exigen.

### DD-26 — Un tramo no cruza la medianoche y no hay tope máximo de horario (P-6)
**Decisión**: `start_time < end_time` literal; el último fin posible es 23:59. El usuario descartó explícitamente un tope de horario configurable (por ejemplo un máximo en `clinic_settings`).
**Contexto**: RN-HO-02 y constraint de `working_hours`; 24:00 sin respaldo en la KB (decisión del usuario).
**Alternativas consideradas**: Tope máximo configurable de horario.
**Justificación**: Evita configuración extra sin necesidad demostrada en v1.
**Trade-offs aceptados**: ninguno relevante; se reconsidera si C-07/C-08 lo exigen.

### DD-27 — Tramos contiguos no se superponen (P-7)
**Decisión**: Intervalos semiabiertos `[inicio, fin)`: 09:00–13:00 y 13:00–17:00 son válidos.
**Contexto**: RN-HO-02 no define el borde; coherente con `slot-availability` (decisión del usuario).
**Alternativas consideradas**: Contiguos = superpuestos.
**Justificación**: Misma semántica que `ranges_overlap`.
**Trade-offs aceptados**: ninguno relevante; se reconsidera si C-07/C-08 lo exigen.

### DD-28 — Licencias superpuestas o pasadas se aceptan (P-8)
**Decisión**: La validación solo exige `starts_on <= ends_on` (`END_BEFORE_START`).
**Contexto**: Constraint de `time_off`; el resto sin respaldo en la KB (decisión del usuario).
**Alternativas consideradas**: Rechazar superposición o fechas pasadas.
**Justificación**: Superponerlas no cambia la disponibilidad.
**Trade-offs aceptados**: ninguno relevante; se reconsidera si C-07/C-08 lo exigen.

### DD-29 — Se rechazan tramos con segundos (P-9)
**Decisión**: `SUB_MINUTE_PRECISION` si `start_time` o `end_time` tienen segundos o microsegundos.
**Contexto**: Sin respaldo en la KB (decisión del usuario).
**Alternativas consideradas**: Ignorar los segundos.
**Justificación**: La grilla trabaja en minutos y `minutes_of_day` ignora los segundos.
**Trade-offs aceptados**: ninguno relevante; se reconsidera si C-07/C-08 lo exigen.

### DD-30 — Un tramo más corto que `slot_minutes` es válido (P-10)
**Decisión**: La validación de tramos no depende de `slot_minutes`; `compute_slots` lo muestra `OUTSIDE_HOURS`.
**Contexto**: RN-TU-02, DD-15; la validez del tramo sin respaldo en la KB (decisión del usuario).
**Alternativas consideradas**: Rechazar tramos más cortos que un slot.
**Justificación**: `slot_minutes` puede cambiar en `clinic_settings`.
**Trade-offs aceptados**: ninguno relevante; se reconsidera si C-07/C-08 lo exigen.

### DD-31 — Los listados de turnos se piden por rango desde/hasta (P-1 de C-05d)
**Decisión**: Los listados por profesional o paciente reciben un rango `[desde, hasta)` de instantes con zona; `hasta` es opcional. Quien necesita un día local lo convierte una vez con `local_day_bounds`.
**Contexto**: RN-GL-01; la forma del rango no tiene respaldo en la KB (decisión del usuario, change `puertos-repositorios-dominio`).
**Alternativas consideradas**: Pedir "el día tal" y que el repositorio convierta.
**Justificación**: La zona horaria queda en un solo lugar y sirve igual para el día, la semana (C-09) y "todos los futuros" (C-07). Un turno que cruza la medianoche aparece en ambos días (DD-19).
**Trade-offs aceptados**: el llamador convierte el día local; se reconsidera si C-09 lo vuelve incómodo.

### DD-32 — Errores del repositorio de turnos con nombre propio (P-2 de C-05d)
**Decisión**: El repositorio lanza `SlotTakenError` (`SLOT_TAKEN`, con profesional e inicio pedidos) si una escritura deja dos turnos `scheduled` superpuestos, y `AppointmentNotFoundError` (`APPOINTMENT_NOT_FOUND`) si se modifica un id inexistente. Viven en `domain/appointments/errors.py`.
**Contexto**: Flujo 2 y entrada C-08 ("traduce el error del constraint"); la forma del error no tiene respaldo en la KB (decisión del usuario).
**Alternativas consideradas**: Devolver un resultado aceptado/rechazado como `validate_appointment`.
**Justificación**: Es un caso raro que normalmente ya filtró `validate_appointment`; reproduce lo que hace la base al rechazar y C-08 lo traduce en un solo lugar.
**Trade-offs aceptados**: dos estilos de rechazo (resultado en las reglas puras, excepción en el repositorio).

### DD-33 — Formas de retorno de los repositorios (P-3 de C-05d)
**Decisión**: Guardar devuelve el objeto completo con su id nuevo; buscar un id inexistente devuelve "no encontrado" (`None`) sin error; modificar (cambiar estado, reprogramar) un id inexistente lanza `APPOINTMENT_NOT_FOUND`.
**Contexto**: Sin respaldo en la KB (decisión del usuario).
**Alternativas consideradas**: Devolver solo el id; lanzar error al buscar.
**Justificación**: Buscar y no encontrar es normal (un enlace viejo); modificar algo inexistente es un error del llamador; devolver el objeto evita una segunda consulta.
**Trade-offs aceptados**: ninguno relevante.

### DD-34 — El repositorio de pacientes de C-05d es solo lectura mínima (P-4 de C-05d)
**Decisión**: El puerto solo tiene `get(id)` (existe y activo). Alta, búsqueda por apellido/documento y unicidad del documento (RN-PA-01) las agrega C-06 al mismo puerto.
**Contexto**: Entradas C-06 y C-08 de `CHANGES.md`, RN-PA-04.
**Alternativas consideradas**: Definir ya todo el ABM.
**Justificación**: Definir el ABM ahora sería adivinar las firmas de C-06.
**Trade-offs aceptados**: C-06 extiende el puerto.

### DD-35 — Los listados de turnos devuelven todos los estados, ordenados por inicio (P-5 de C-05d)
**Decisión**: Los listados incluyen `scheduled`, `cancelled`, `completed` y `no_show`, ordenados por hora de inicio; cada pantalla o regla filtra lo que necesita.
**Contexto**: RN-TU-05, DD-16; el filtro no tiene respaldo en la KB (decisión del usuario).
**Alternativas consideradas**: Filtrar solo `scheduled` en el repositorio.
**Justificación**: `compute_slots` y `validate_appointment` ya ignoran los no agendados; la agenda (C-09) y el historial del paciente necesitan ver cancelados y atendidos.
**Trade-offs aceptados**: ninguno relevante.

### DD-36 — Sin unidad de trabajo en C-05d (P-6 de C-05d)
**Decisión**: Cada operación del repositorio es "todo o nada" por sí sola (incluida reprogramar, RN-TU-06). C-08 decide, con la base real, si agrupa turno y notificación en una transacción.
**Contexto**: RN-TU-06, RN-NO-04 (un fallo de email nunca impide agendar); la unidad de trabajo no tiene respaldo en la KB.
**Alternativas consideradas**: Definir un unit-of-work ahora.
**Justificación**: Diseñarlo sin base de datos sería adivinar.
**Trade-offs aceptados**: C-08 puede necesitar extender los puertos.

## Supuestos inferidos

### SU-01 — Zona horaria única
**Supuesto**: el consultorio opera en `America/Argentina/Buenos_Aires`.
**Origen**: contexto de la cursada y mención de normativa de datos personales; no fue confirmado.
**Riesgo si es falso**: horarios y recordatorios corridos.
**Cómo validar**: confirmar la zona con el usuario.
**Ampliación (C-05b)**: se asume además que la zona del consultorio no tiene horario de verano; por eso `compute_slots` no se prueba con días de 23 o 25 horas ni con horas repetidas o inexistentes. El código calcula el inicio y el fin del día con la zona y no depende de que el día dure 24 horas. Si la zona cambia, hay que agregar esos escenarios.

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
