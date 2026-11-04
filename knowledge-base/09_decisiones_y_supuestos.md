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
**Estado**: cerrado en C-08 (DD-62): la unidad de trabajo agrupa turno y notificación en una transacción, y los puertos se extendieron sin cambios de contrato para C-05d.

### DD-37 — Identificadores UUID generados por la base (P-1 de C-02)
**Decisión**: todas las tablas usan `uuid` como clave primaria con `DEFAULT gen_random_uuid()`; el dominio sigue tratando los ids como texto.
**Contexto**: `04_modelo_de_datos.md` ya decía `uuid PK`; el usuario confirmó la opción.
**Alternativas consideradas**: números correlativos (expone cantidades y es adivinable en una URL).
**Justificación**: no deja adivinar ids; para el tamaño de un consultorio la diferencia de rendimiento no se nota.
**Trade-offs aceptados**: la batería de contrato deja de usar ids inventados (`"dra-a"`): las referencias las entrega la fábrica de cada implementación; un id con otro formato se trata como "no encontrado".

### DD-38 — Todo profesional tiene cuenta; email de usuario único sin distinguir mayúsculas (P-2 de C-02)
**Decisión**: `users` y `professionals` van unidas: `professionals.user_id` es `NOT NULL UNIQUE` (cada profesional tiene exactamente una cuenta; una cuenta, como mucho una ficha). El email de `users` es único sobre `lower(email)` (índice `uq_users_email_lower`).
**Contexto**: la KB decía "`UNIQUE`" sin hablar de mayúsculas ni de profesionales sin cuenta.
**Alternativas consideradas**: profesionales sin cuenta; una sola tabla.
**Justificación**: evita dos cuentas para la misma persona y errores al iniciar sesión.
**Trade-offs aceptados**: un odontólogo que no use el sistema igual necesita una cuenta (puede quedar inactiva). C-03/C-04 deben comparar emails sin distinguir mayúsculas.

### DD-39 — Nada se borra en cadena: las claves foráneas son `ON DELETE RESTRICT` (P-3 de C-02)
**Decisión**: la base impide borrar pacientes, profesionales y usuarios con turnos, y turnos con notificaciones; un paciente sin turnos sí se puede borrar. Los tramos de horario y las licencias también bloquean el borrado de su profesional (se reemplazan o se borran antes).
**Contexto**: RN-PA-03 (paciente con turnos se desactiva) y DD-05 (cancelar no borra).
**Alternativas consideradas**: borrado en cadena (pierde el historial).
**Justificación**: conserva la historia; la baja es marcar `active = false`.
**Trade-offs aceptados**: para borrar un profesional creado por error hay que borrar antes sus tramos y licencias.

### DD-40 — Seed idempotente con contraseña de demo desde `SEED_DEMO_PASSWORD` (P-4 de C-02)
**Decisión**: `backend/scripts/seed.py` carga 1 admin, 1 recepcionista, 2 profesionales con su cuenta de odontólogo y horario de lunes a viernes, la configuración del consultorio (zona de `CLINIC_TIMEZONE`) y 10 pacientes, todo ficticio con emails `@example.com`. La contraseña sale de la variable `SEED_DEMO_PASSWORD` (nunca del código); si falta, el seed termina con error y no crea nada. Solo agrega lo que falta y no pisa cambios ni contraseñas.
**Contexto**: regla dura 5 y R-10; `04_modelo_de_datos.md` decía "contraseñas de prueba definidas en el script", lo que contradice la regla dura 5.
**Alternativas consideradas**: contraseña fija en el script.
**Justificación**: no deja una contraseña conocida en el repositorio; el seed corre en una sola transacción.
**Trade-offs aceptados**: C-13 debe definir una contraseña propia si usa el seed en la demo pública.

### DD-41 — C-02 agrega solo `hash_password` (argon2); el resto de la seguridad es de C-03 (P-5 de C-02)
**Decisión**: `app/core/security.py` expone `hash_password` con `argon2-cffi` (parámetros por defecto, sal aleatoria). La verificación y el JWT se hacen en C-03.
**Contexto**: el seed necesita guardar contraseñas como hash desde ahora.
**Alternativas consideradas**: hash "imposible" y actualizarlo en C-03; mover los usuarios del seed a C-03.
**Justificación**: función pequeña y probada que deja el seed completo.
**Trade-offs aceptados**: la imagen del backend debe reconstruirse por la dependencia nueva.

### DD-42 — Horarios como `time`; la base rechaza segundos; la superposición de tramos queda en el dominio (P-6 de C-02)
**Decisión**: `working_hours.start_time` y `end_time` son `time` sin zona; CHECK `EXTRACT(SECOND FROM col) = 0` (DD-29 reforzado en la base), `weekday BETWEEN 0 AND 6` y `start_time < end_time`. La no superposición de tramos del mismo día NO la verifica la base: la valida `validate_working_hours` antes de guardar.
**Contexto**: RN-HO-02 y DD-29; una exclusión de rangos de horas haría que la base y el repositorio en memoria se comporten distinto.
**Alternativas consideradas**: minutos desde la medianoche; exclusión de rangos en la base.
**Justificación**: `time` es lo que ya usa el dominio y es legible.
**Trade-offs aceptados**: un caller que escriba tramos sin validar puede dejar tramos superpuestos en la base.

### DD-43 — Un solo change C-02 ejecutado por grupos (P-7 de C-02)
**Decisión**: tablas, migración, tests de la base, seed, hash, repositorios PostgreSQL y la fábrica `postgres` de la batería de contrato van en un solo change. El test con dos conexiones simultáneas y la unidad de trabajo quedaron para C-08 y se cerraron allí (DD-36, DD-62).
**Contexto**: la batería de contrato contra PostgreSQL es la mejor prueba de que el esquema sirve al dominio.
**Alternativas consideradas**: partirlo en C-02a/C-02b; dejar los repositorios para C-08.
**Justificación**: una sola revisión del esquema con su verificación principal.
**Trade-offs aceptados**: change grande.

### DD-44 — Rangos de `clinic_settings` verificados por la base (C-02)
**Decisión**: CHECK `slot_minutes > 0` (coherente con DD-18), `min_notice_hours >= 0` y `reminder_send_hour BETWEEN 0 AND 23`; fila única con `id smallint PRIMARY KEY DEFAULT 1 CHECK (id = 1)`. `reminder_send_hour` es `NOT NULL DEFAULT 9`.
**Contexto**: la KB solo pedía defaults; los rangos no tenían respaldo y el usuario aprobó estas tres reglas triviales. La KB marcaba `reminder_send_hour` como nulable; se hizo `NOT NULL` porque el recordatorio (C-11) necesita siempre una hora.
**Alternativas consideradas**: no validar en la base.
**Justificación**: valores sin sentido (0 minutos, hora 25) nunca deben llegar al cálculo de franjas ni al job de recordatorios.
**Trade-offs aceptados**: ninguno relevante.

### DD-45 — Sesión de 30 minutos sin refresh token; "Salir" solo borra el token del navegador (P-1 y P-11 de C-03)
**Decisión**: el token de acceso dura `ACCESS_TOKEN_EXPIRE_MINUTES` (30 por defecto) y no hay refresh token ni lista de tokens revocados. "Salir" borra el token del navegador; un token copiado antes sigue sirviendo hasta que venza.
**Contexto**: el servidor no guarda sesiones; revocar exigiría consultar Redis en cada request y un endpoint de logout.
**Alternativas consideradas**: 8 horas; refresh token; lista negra en Redis.
**Justificación**: vida corta limita el daño de un token robado y `current_user()` recarga la cuenta en cada request (desactivarla corta el acceso al instante). Resuelve SU-07.
**Trade-offs aceptados**: el usuario reingresa cada 30 minutos; el token no se puede anular antes de vencer.

### DD-46 — El token vive en `sessionStorage` (P-2 de C-03)
**Decisión**: el frontend guarda el token en `sessionStorage` (se pierde al cerrar la pestaña; sobrevive a recargar). Si el almacenamiento falla, la sesión vive en memoria. Nunca en `localStorage` ni en cookies creadas por el frontend; la contraseña no se guarda en ningún lado.
**Contexto**: una cookie httpOnly cambia el diseño de la API (CSRF, CORS con credenciales).
**Alternativas consideradas**: solo memoria; `localStorage`; cookie httpOnly.
**Justificación**: equilibrio entre comodidad (F5 no saca de la sesión) y exposición.
**Trade-offs aceptados**: un XSS podría leer el token (riesgo ya aceptado; la cookie httpOnly se evalúa en C-13).

### DD-47 — Sin límite de intentos fallidos en C-03 (P-3 de C-03)
**Decisión**: no hay bloqueo de cuenta ni límite por email/IP; se revisa en C-13. Para no revelar si una cuenta existe, el login verifica contra un hash ficticio cuando el email no existe.
**Alternativas consideradas**: límite con Redis (429); bloqueo hasta que el administrador desbloquee.
**Justificación**: datos ficticios; argon2 ya es lento; el bloqueo permitiría dejar fuera a otra persona a propósito.
**Trade-offs aceptados**: fuerza bruta posible hasta C-13.

### DD-48 — Matriz RBAC confirmada; solo el administrador edita horarios (P-4 de C-03)
**Decisión**: se confirma la matriz de `03_actores_y_roles.md` tal cual, incluido que solo el administrador edita horarios y licencias. Resuelve SU-06.
**Justificación**: los horarios cambian poco y concentrarlos en una persona evita conflictos.
**Trade-offs aceptados**: la recepción no puede corregir un horario sin el administrador.

### DD-49 — Errores de autenticación y autorización genéricos (P-5 de C-03)
**Decisión**: email inexistente, contraseña incorrecta y cuenta desactivada responden 401 `INVALID_CREDENTIALS` con el mismo mensaje ("Email o contraseña incorrectos"); sin sesión, vencida o inválida: 401 `NOT_AUTHENTICATED`; sin permiso: 403 `FORBIDDEN`. Toda respuesta 401 lleva `WWW-Authenticate: Bearer`. El 422 de validación mantiene el formato de FastAPI.
**Justificación**: un mensaje distinto para cuentas desactivadas permitiría averiguar qué emails existen (Flujo 1: mensaje genérico).

### DD-50 — Email normalizado en el login (P-6 de C-03)
**Decisión**: el email se recorta y se compara sin distinguir mayúsculas (coherente con DD-38); la contraseña se compara exacta, sin recortar. Máximos: email 254, contraseña 128 caracteres.

### DD-51 — Redirección, cambio de rol y datos de `/auth/me` (P-7, P-8 y P-9 de C-03)
**Decisión**: los tres roles van a `/agenda` (página provisoria con nombre y rol hasta C-10). Si cambia el rol de una cuenta o se la desactiva, la sesión abierta recibe 401 en la siguiente llamada. `GET /auth/me` devuelve id, email, nombre, rol y `professional_id` (nunca el hash ni el token).
**Justificación**: nunca conviven dos roles en una misma sesión; el frontend necesita `professional_id` para filtrar la agenda del odontólogo.

### DD-52 — Sin variables de entorno nuevas en C-03 (P-10 de C-03)
**Decisión**: se usan `JWT_SECRET_KEY`, `JWT_ALGORITHM` y `ACCESS_TOKEN_EXPIRE_MINUTES` ya validadas desde C-01; el frontend sigue usando solo `VITE_API_URL`.

### DD-53 — El odontólogo solo accede a lo propio; sin ficha no ve nada; 403 en lo ajeno (P-12 y P-13 de C-03)
**Decisión**: la regla pura `can_access_professional` y la dependencia `require_professional_access` entregan RN-AU-04. Un odontólogo sin ficha puede entrar pero no accede a datos de ningún profesional; con la ficha desactivada ve lo suyo (el ingreso lo decide solo `users.active`); un id ajeno o mal formado responde 403, no 404. Se prueba con una ruta registrada solo en los tests; el test de punta a punta contra el endpoint real de turnos es obligatorio en C-08.
**Justificación**: separa "puede entrar" (RN-AU-03) de "qué ve" (RN-AU-04); el personal del consultorio ya conoce a los demás profesionales.

### DD-54 — `react-router` y un solo change C-03 (P-14 y P-15 de C-03)
**Decisión**: el frontend usa `react-router` en modo librería (`BrowserRouter`, `Routes`, `Navigate`) y C-03 se ejecutó como un solo change por grupos (backend primero, frontend al final).

### DD-55 — Técnica de autenticación (C-03)
**Decisión**: PyJWT y argon2-cffi viven en `app/core/security.py`; el token lleva solo `sub`, `role`, `iat` y `exp`; la lista blanca de algoritmos y los claims obligatorios los fija el decode, y el vencimiento se compara contra un reloj inyectable. `current_user` usa `HTTPBearer(auto_error=False)` para responder con el cuerpo uniforme. Un test de inventario de rutas exige que toda ruta fuera de login y health dependa de `current_user`.
**Consultado con Context7**: `/jpadilla/pyjwt` (`algorithms` obligatorio, `require`), `/hynek/argon2-cffi` (`verify`, `check_needs_rehash`), `/websites/fastapi_tiangolo` (`HTTPBearer(auto_error=False)`).
**Hallazgo**: FastAPI 0.162 ya no aplana `app.routes` (los routers incluidos aparecen como `_IncludedRouter`); el inventario recorre las rutas con `fastapi.routing.iter_route_contexts`. Un inventario que solo mirara `app.routes` pasaría en vacío.
**Resuelto en C-04 (DD-61)**: rehash con `check_needs_rehash` al iniciar sesión (necesita escritura de usuarios).

### DD-56 — La administración define la contraseña inicial y puede asignar una nueva (P-1 y P-2 de C-04)
**Decisión**: al crear una cuenta, el administrador escribe la contraseña inicial (8 a 128 caracteres) y se la entrega a la persona; el sistema solo guarda su hash y nunca la devuelve. El administrador también puede asignar una contraseña nueva a cualquier cuenta (`PUT /users/{id}/password`).
**Alternativas consideradas**: contraseña generada y mostrada una vez; enlace por email para elegirla; no asignar contraseñas en C-04.
**Justificación**: ninguna respuesta debe contener una contraseña; el email depende de SU-02 y sumaría tokens de un solo uso; sin "olvidé mi contraseña" habría que tocar la base a mano.
**Trade-offs aceptados**: contraseñas iniciales posiblemente débiles; el cambio de la propia contraseña queda fuera.

### DD-57 — Email editable y reglas de cambio de rol (P-3 y P-4 de C-04)
**Decisión**: el email se puede editar con la validación del alta y sin repetir el de otra cuenta; la sesión abierta sigue. Cambio de rol: entre `admin` y `receptionist`, libre; de ellos a `dentist`, permitido y crea la ficha; de `dentist` a otro rol, no (`ROLE_CHANGE_NOT_ALLOWED`).
**Alternativas consideradas**: email fijo; rol solo entre admin y recepción; todo permitido con la ficha desactivada.
**Justificación**: corrige errores de carga sin dejar fichas huérfanas (DD-38) ni romper la historia de turnos (DD-39).

### DD-58 — El administrador no puede desactivarse ni cambiar su propio rol (P-5 de C-04)
**Decisión**: el administrador no puede desactivar su propia cuenta ni cambiar su propio rol (`SELF_MODIFICATION_NOT_ALLOWED`); sí puede desactivar a otro administrador. Garantiza que siempre quede un administrador activo.
**Alternativas consideradas**: permitirlo con advertencia; permitirlo verificando que quede otro administrador activo.
**Trade-offs aceptados**: dos administradores desactivándose mutuamente a la vez podrían dejar el sistema sin ninguno (se recupera con el seed o a mano).

### DD-59 — Desactivar y reactivar: ficha en conjunto, turnos intactos, sin borrado (P-6, P-7 y P-8 de C-04)
**Decisión**: desactivar un odontólogo no toca sus turnos (la pantalla avisa que recepción debe reprogramarlos o cancelarlos); la ficha se desactiva y reactiva junto con la cuenta; se puede desactivar y reactivar las veces que haga falta y no existe borrado definitivo.
**Alternativas consideradas**: bloquear la baja con turnos futuros; cancelar los turnos automáticamente; ficha independiente; borrado para cuentas sin historia.
**Justificación**: coherente con DD-25 y DD-39; la lógica de turnos y emails es de C-08 y C-11.

### DD-60 — Listado sin páginas, datos de la ficha en el alta y aviso de falta de permiso (P-9, P-10 y P-11 de C-04)
**Decisión**: `GET /users` devuelve todas las cuentas ordenadas por nombre, sin páginas ni filtros. El alta de odontólogo pide "Nombre a mostrar" (vacío: nombre completo) y "Matrícula" opcional; editarlos queda para C-07. Un no administrador en `/usuarios` ve "No tenés permiso para esta acción" con enlace a la agenda, sin cerrar sesión; el enlace "Usuarios" solo lo ve el administrador.

### DD-61 — Rehash al iniciar sesión, repositorio de profesionales y un solo change (P-12, P-13 y P-14 de C-04)
**Decisión**: tras un login correcto con hash de parámetros viejos se guarda un hash nuevo (si falla, el login igual funciona); C-04 define el repositorio de lectura de profesionales (listar y buscar por id) con batería de contrato, sin endpoints; C-04 se ejecuta como un solo change por grupos. Cierra el pendiente de DD-55.

### DD-62 — Notificaciones registradas por la agenda (P-1 y P-2 de C-08)
**Decisión**: al agendar o reprogramar, C-08 guarda en la misma transacción que el turno una fila `confirmation` `pending` en `email_notifications` y después avisa a un despachador que en C-08 no hace nada (C-11 lo reemplaza); al reprogramar o cancelar se borran las filas `pending` del horario anterior y se conservan las `sent` y `failed` como historial; si el turno vuelve a un horario que ya tiene confirmación no se duplica ni falla.
**Alternativas consideradas**: no anotar nada y dejar todo a C-11; estado `discarded` con migración; dejar las `pending` viejas sin borrar.
**Justificación**: cierra DD-36 con una prueba real contra PostgreSQL, no requiere migración y C-11 no filtra filas muertas. Consecuencia: quien vuelve a su horario original no recibe una segunda confirmación; antes de C-11 se acumulan filas `pending` que nadie envía (C-11 decide si las limpia).

### DD-63 — Un paciente no tiene dos turnos superpuestos (P-3 de C-08; cierra H-2)
**Decisión**: un paciente no puede tener dos turnos `scheduled` que se superpongan, aunque sean con profesionales distintos; se rechaza con `PATIENT_DOUBLE_BOOKED`. Varios turnos el mismo día en horarios distintos siguen permitidos (RN-TU-08).
**Alternativas consideradas**: permitirlo.
**Justificación**: una persona no está en dos sillones a la vez; casi siempre es un error de carga. Límite aceptado: la regla la garantiza la aplicación, no la base (dos pedidos simultáneos para el mismo paciente podrían colarse).

### DD-64 — Quién marca atención, profesional inactivo y reprogramar (P-4, P-5 y P-6 de C-08)
**Decisión**: marcar `completed` o `no_show` lo puede hacer el odontólogo (solo sus turnos) y recepción y administración (cualquier turno), siempre con el turno ya iniciado; a un profesional con ficha inactiva no se le agendan ni reprograman turnos nuevos, pero sus turnos se pueden ver, cancelar y marcar; reprogramar solo cambia día y hora, no el profesional (para eso se cancela y se agenda de nuevo).
**Alternativas consideradas**: solo el odontólogo; odontólogo y administración; permitir turnos a fichas inactivas; cambiar de profesional al reprogramar.
**Justificación**: sigue la matriz DD-48, DD-59 y el Flujo 3; evita cambiar el repositorio y sumar casos.

### DD-65 — Motivo obligatorio y sin excepción de urgencias (P-7 y P-8 de C-08)
**Decisión**: el motivo de cancelación es obligatorio (texto libre de 1 a 500 caracteres tras recortar espacios); la anticipación mínima se aplica a todos, sin excepción para urgencias (se puede bajar `min_notice_hours` en la configuración).
**Alternativas consideradas**: motivo opcional; permiso especial del administrador para urgencias.
**Justificación**: US-008 pide el motivo y no hay otra auditoría de cancelaciones; la excepción no fue pedida y queda como mejora posterior (RN-TU-12, DD-14).

### DD-66 — Consultas y franjas en C-08, listado global en C-12 y un solo change (P-9, P-10 y P-11 de C-08)
**Decisión**: C-08 incluye ver un turno, listar los de un profesional por rango y las franjas de un día; C-09 queda con las pantallas y pasa a depender de C-08; el listado de turnos de todos los profesionales por rango pasa a C-12, que es quien lo usa; C-08 se ejecuta como un solo change por grupos, con punto de corte seguro tras la concurrencia.
**Alternativas consideradas**: franjas en C-09; listado global en C-08; partir C-08 en dos changes.
**Justificación**: agendar y mostrar franjas libres usan los mismos datos y reglas; el listado global sin su usuario obliga a adivinar filtros.

### DD-67 — Tres bordes de horario (P-12 de C-08)
**Decisión**: reprogramar al mismo horario que ya tiene se rechaza con `RESCHEDULE_SAME_TIME`; un inicio con segundos o fracciones se rechaza como `OFF_GRID` (análogo a DD-29); al reprogramar un turno viejo se usa la duración `slot_minutes` vigente (RN-TU-02).
**Alternativas consideradas**: aceptar sin hacer nada; redondear el inicio; conservar la duración original.
**Justificación**: evita avisos duplicados, mantiene la grilla exacta y la duración es siempre la de la configuración.

### DD-68 — Conflictos calculados, solo aviso a recepción y qué turnos cuentan (P-1, P-2 y P-3 de C-07)
**Decisión**: los turnos en conflicto por un cambio de horario o una licencia no se marcan en la base: se calculan en el momento y se muestran al guardar y en una consulta `GET /professionals/{id}/conflicts`. Solo se avisa a recepción, en pantalla; no se manda email al paciente (cierra la pregunta abierta de RN-HO-04). Cuentan únicamente los turnos `scheduled` que todavía no empezaron y que ya no entran completos en un tramo del horario o caen en un día de licencia; un turno fuera de la grilla nueva pero dentro del horario no cuenta.
**Alternativas consideradas**: campo "en conflicto" en los turnos (migración); mostrarlos solo al guardar; email automático al paciente; contar los turnos fuera de grilla o ya iniciados.
**Justificación**: la lista siempre está al día, no hay migración ni marca desactualizada; el paciente recibe un solo mensaje claro (nuevo horario o cancelación) cuando exista C-11; un turno ya iniciado no se puede reprogramar (DD-21, DD-24).

### DD-69 — Guardar con conflictos y bordes de licencias (P-5 y P-10 de C-07)
**Decisión**: un cambio de horario o una licencia que deja turnos en conflicto se guarda igual y se devuelve la lista de afectados. El motivo de una licencia es opcional, de hasta 500 caracteres (vacío = sin motivo); no hay tope de duración y se siguen aceptando licencias superpuestas o pasadas (DD-28).
**Alternativas consideradas**: bloquear el guardado; guardar en dos pasos con confirmación; tope de duración o rechazo de licencias pasadas.
**Justificación**: es lo que piden RN-HO-04, US-004 y el Flujo 5; una licencia por enfermedad debe poder cargarse ya.

### DD-70 — Borrar licencias, solo el administrador (P-4 de C-07)
**Decisión**: se pueden cargar y borrar licencias (solo administración); no se editan: para corregir se borra y se vuelve a cargar. Una licencia inexistente o de otro profesional responde `TIME_OFF_NOT_FOUND`.
**Alternativas consideradas**: solo cargar; cargar, editar y borrar.
**Justificación**: un error de carga no puede bloquear días de agenda para siempre; la licencia no tiene nada colgado en la base.

### DD-71 — Profesional inactivo, listado y edición de la ficha (P-6, P-7 y P-8 de C-07)
**Decisión**: el administrador puede editar horario, licencias y ficha de un profesional inactivo. El listado muestra activos e inactivos con su estado, ordenados por nombre; el odontólogo ve solo su ficha (lista vacía si no tiene). Solo el administrador edita "nombre a mostrar" (1 a 200 caracteres) y "matrícula" (opcional, 1 a 50, se puede borrar).
**Alternativas consideradas**: bloquear la edición de inactivos; listar solo activos o dar 403 al odontólogo; que el odontólogo edite su ficha.
**Justificación**: permite preparar el horario antes de reactivar (C-08 ya bloquea turnos nuevos, DD-64); mismos límites que el alta de C-04 (DD-60); matriz RBAC DD-48.

### DD-72 — Pantalla en C-07 y un solo change (P-9 y P-11 de C-07)
**Decisión**: la pantalla `/profesionales` (listado, ficha, editor semanal, licencias y aviso de conflictos) entra en C-07, con recepción y odontólogo en modo lectura. C-07 se ejecuta como un solo change por grupos, con punto de corte seguro al terminar el backend (grupo 6).
**Alternativas consideradas**: solo backend y pantalla en C-09/C-10; partir en C-07a y C-07b.
**Justificación**: sin pantalla el administrador no puede usar lo construido; el contrato de la API y la pantalla se validan juntos, como en C-04.

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
**Ampliación (C-08, DD-63)**: confirmado para horarios distintos; a la misma hora con profesionales distintos se rechaza (`PATIENT_DOUBLE_BOOKED`).
**Riesgo si es falso**: agregar una regla y una validación más.
**Cómo validar**: preguntar al usuario.

### SU-06 — Solo el administrador edita horarios (RESUELTO en C-03, DD-48)
**Supuesto**: recepción solo consulta horarios.
**Resolución**: confirmado por el usuario el 2026-11-03 al aprobar la matriz RBAC de C-03 (DD-48).
**Riesgo si es falso**: cambiar la matriz RBAC.

### SU-07 — Sin refresh token en v1 (RESUELTO en C-03, DD-45)
**Supuesto**: alcanza con un token de acceso de 30 minutos; al vencer, el usuario vuelve a iniciar sesión.
**Resolución**: confirmado por el usuario el 2026-11-03 (DD-45). Si la recepción se queja, se sube `ACCESS_TOKEN_EXPIRE_MINUTES` sin tocar código.
**Origen**: simplicidad del MVP.
**Riesgo si es falso**: la recepción se molesta por reingresar; se agrega un refresh token.
