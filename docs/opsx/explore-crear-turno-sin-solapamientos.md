# Explore: `crear-turno-sin-solapamientos`

Fase EXPLORE del ciclo OPSX. Solo lectura sobre el código; este archivo es lo único que se escribió.
Origen: C-05 `domain-scheduling-core` (`CHANGES.md`), acotado a "validar si se puede crear un turno para un profesional, sin solapamientos".

## 1. Problema

Hoy la recepción agenda en planilla o WhatsApp y es fácil darle a un odontólogo dos pacientes a la misma hora. Este change resuelve una sola pregunta de negocio: **"¿puedo crear este turno para este profesional?"**. La respuesta es "sí" o "no, y por este motivo". Es una función de dominio pura: recibe datos, devuelve una decisión. No guarda nada, no tiene pantalla ni endpoint.

La no superposición es la regla central de la agenda (AGENTS.md regla dura 6, RN-TU-01). Más adelante la base de datos la reforzará con el constraint de exclusión (C-02), pero el dominio tiene que decirlo primero y con un mensaje claro.

## 2. Estado actual del código

Evidencia (Glob y `ls` del repo):

- NO existe `backend/`, ni `pyproject.toml`, ni ningún `.py`, ni `tests/`. Glob de `{backend,pyproject.toml,docs/opsx}/**` devolvió vacío.
- Sí existen: `AGENTS.md`, `CLAUDE.md`, `CHANGES.md`, `knowledge-base/` (01 a 11), `docs/discovery/informe-discovery.md`, `openspec/` (con `config.yaml` sin contexto cargado, `specs/.gitkeep`, `changes/archive/.gitkeep`; sin changes activos), `.claude/commands/opsx/*`, `.claude/skills/tdd`, `.atl/`.
- `CHANGES.md`: todos los changes figuran `[ ]` pendiente, incluido C-01.
- La KB no fija versión de Python, ni linter concreto (solo "ruff" aparece en CHANGES.md C-01). No inventar: es una decisión a tomar.

Conclusión: empezamos de cero; todo el código es nuevo.

## 3. Reglas de negocio

### Entran

- **RN-TU-01**: "Un profesional no puede tener dos turnos `scheduled` superpuestos. Se valida en el dominio y se garantiza con el constraint de exclusión." (núcleo del change)
- **RN-TU-02**: "La duración de un turno es siempre `slot_minutes` (30 por defecto) y el inicio cae en la grilla de slots del horario del profesional." (el fin lo calcula el dominio; el inicio debe caer en la grilla)
- **RN-TU-03**: "Un turno debe quedar completo dentro de un tramo de `working_hours` del profesional y fuera de sus licencias."
- **RN-TU-04**: "No se puede agendar un turno con inicio en el pasado."
- **RN-HO-03**: "Los días cubiertos por una licencia (`time_off`) no admiten turnos." (se usa como insumo de RN-TU-03)
- **RN-TU-08**: "Un paciente puede tener varios turnos el mismo día" (SU-05, a validar): entra como NO-regla; la función no valida nada por paciente.
- **RN-TU-09, RN-TU-10, RN-TU-11**: entran como restricciones de diseño: se agenda por profesional, duración fija `slot_minutes`, sin sobreturnos (sin parámetro de excepción).
- **RN-GL-01**: "Todas las fechas se guardan en UTC (`timestamptz`) y se muestran en la zona horaria del consultorio". Entra porque `working_hours` está en hora local y `starts_at` en UTC: hay que convertir para comparar.
- Del modelo (`04_modelo_de_datos.md`): `appointments.status = scheduled` es lo que cuenta como ocupado (el constraint tiene `WHERE (status = 'scheduled')`); `working_hours` (`weekday`, `start_time`, `end_time`), `time_off` (`starts_on`, `ends_on`), `clinic_settings` (`slot_minutes`, `timezone`).

### Quedan afuera (con justificación)

- RN-TU-05 y RN-TU-07 (cancelar, transiciones de estado): no son "crear". Quedan en el resto de C-05 / C-08. Solo se usa de ellas que `cancelled` libera el slot.
- RN-TU-06 (reprogramar): reutiliza la misma validación después, pero la atomicidad es de C-08. Ojo: al reprogramar, el turno original no debe chocar consigo mismo; no entra ahora (ver pregunta 5, es un punto de extensión).
- RN-PA-04 (paciente inactivo): involucra al paciente y su dominio; se valida en el caso de uso o en `domain/patients`. Fuera por ser otra funcionalidad.
- RN-HO-02 (validar tramos de un día sin superposición, `start < end`): se asume ya validado al cargar horarios (C-07); acá se tratan como dato de confianza.
- RN-HO-04 (conflictos al cambiar horarios), `compute_slots` (disponibilidad para la UI), RN-NO-xx (emails), RN-AU/RN-PR: no tienen que ver con la decisión de crear.
- Constraint de exclusión en PostgreSQL y concurrencia (Flujo 2 paso 4, US-007 "dos recepcionistas"): es de C-02/C-08; el dominio no puede garantizar concurrencia. Documentar que esta función es la primera línea, no la única.

## 4. Entradas y salidas propuestas (sin código final)

Nombre tentativo: `validate_appointment` en `backend/app/domain/appointments/` (el nombre ya figura en CHANGES.md C-05).

**Entradas** (todo como datos inmutables simples: dataclasses o tipos básicos de Python; sin ORM):

- `starts_at`: instante de inicio en UTC, "aware" (con zona). Se rechaza un datetime "naive" como error de programación, no de negocio.
- `professional_id`: identifica al profesional del turno.
- `working_hours` del profesional: lista de (día de semana, hora desde, hora hasta), en hora local del consultorio.
- `time_off` del profesional: lista de (fecha desde, fecha hasta), días locales, ambos inclusivos (`starts_on <= ends_on`).
- `existing_appointments`: turnos existentes de ESE profesional (o todos, y el dominio filtra por `professional_id`) con `starts_at`, `ends_at`, `status`.
- `slot_minutes` (de `clinic_settings`, 30 por defecto).
- `timezone` (de `clinic_settings`, p. ej. `America/Argentina/Buenos_Aires`).
- `now`: instante actual en UTC, INYECTADO como parámetro para no depender del reloj (hace testeable RN-TU-04).

**Salida**: un resultado explícito (no excepción para el caso de negocio), por ejemplo "aceptado" con el `ends_at` calculado, o "rechazado" con un motivo de un conjunto cerrado (enum):

- `IN_THE_PAST` (RN-TU-04)
- `OFF_GRID` (RN-TU-02: el inicio no cae en la grilla)
- `OUTSIDE_WORKING_HOURS` (RN-TU-03: no entra completo en un tramo, o día sin tramos)
- `PROFESSIONAL_TIME_OFF` (RN-TU-03 / RN-HO-03)
- `OVERLAPS_EXISTING` (RN-TU-01), opcionalmente con el id del turno con el que choca para que la UI/mensaje lo muestre

Decisión de diseño sugerida: devolver el primer motivo según un orden fijo documentado, o todos los motivos juntos (ver pregunta 4). Los errores tipados de `app/core/errors.py` (C-01) llegarán después; el dominio devuelve el resultado y el caso de uso decide si lo convierte en excepción.

Regla de solapamiento: rangos semiabiertos `[inicio, fin)`, igual que `tstzrange` y el constraint de exclusión. Dos turnos chocan si `a.start < b.end` y `b.start < a.end`. Solo cuentan los turnos con `status = scheduled` y del mismo `professional_id`.

## 5. Escenarios candidatos (dado / cuando / entonces)

Supuesto común: zona Buenos Aires (UTC-3, sin horario de verano vigente), `slot_minutes = 30`, Dr. A atiende lunes de 09:00 a 13:00 y 14:00 a 18:00 locales, `now` anterior a la fecha del turno.

**Felices y de negocio**

1. Feliz: dado un lunes 10:00 local sin turnos, cuando se crea un turno a las 10:00, entonces se acepta con `ends_at` 10:30.
2. Error de negocio, pisa a otro turno: dado un turno `scheduled` del Dr. A de 10:00 a 10:30, cuando se crea otro para el Dr. A a las 10:00, entonces se rechaza `OVERLAPS_EXISTING`.
3. Pisado parcial: con turno de 10:00 a 10:30, un intento a las 10:15 se rechaza (por grilla y por solape; define el orden de motivos).
4. Borde, turno pegado (semiabierto): dado un turno de 10:00 a 10:30, cuando se crea otro a las 10:30, entonces se acepta (`[10:00,10:30)` y `[10:30,11:00)` no se pisan). Y el simétrico: un turno nuevo 09:30 a 10:00 con el existente a las 10:00, se acepta.
5. Mismo horario, otro profesional: dado un turno del Dr. A a las 10:00, cuando se crea uno del Dr. B a las 10:00 (B atiende ese horario), entonces se acepta (RN-TU-09).
6. Turno cancelado no cuenta: dado un turno `cancelled` del Dr. A a las 10:00, cuando se crea otro a las 10:00, entonces se acepta (RN-TU-05, constraint con `WHERE status = 'scheduled'`).
7. Mismo paciente, varios turnos: dado un paciente con turno a las 10:00 con el Dr. A, cuando se le crea otro a las 11:00 el mismo día (con A o con B), entonces se acepta (RN-TU-08). Si se mantiene que la función no recibe paciente, este escenario documenta que NO se valida.

**Horario, licencia, pasado, grilla**

8. Fuera de horario: lunes 08:30 local, se rechaza `OUTSIDE_WORKING_HOURS`; el hueco del almuerzo (13:00 a 14:00) también.
9. Borde de tramo: 12:30 (termina 13:00 justo) se acepta; 13:00 se rechaza (cae en el hueco); 17:30 se acepta; 18:00 se rechaza. Con `slot_minutes` que no divide el tramo (p. ej. 45), un turno que no entra completo se rechaza.
10. Día sin horario: un domingo, o un día de la semana sin tramos, se rechaza.
11. Dentro de licencia: `time_off` del 10 al 12 inclusive; un turno el 12 se rechaza `PROFESSIONAL_TIME_OFF`, el 13 se acepta. Licencia de un solo día (`starts_on == ends_on`).
12. Licencia de otro profesional no afecta al Dr. A.
13. Fecha pasada: `now` posterior al `starts_at` se rechaza `IN_THE_PAST`. Borde: `starts_at == now` (ver pregunta 3).
14. Fuera de la grilla: 10:10 con slot 30 se rechaza `OFF_GRID`. La grilla se mide desde el inicio del tramo (RN-TU-02 "grilla del horario del profesional"): con tramo 14:00-18:00, 14:30 es válido y 14:15 no; con un tramo que arranca 09:15 la grilla es 09:15, 09:45, etc.
15. Zona horaria: un `starts_at` de 13:00 UTC es 10:00 local (se acepta); el mismo instante evaluado como si fuera hora local (error clásico) daría otro resultado. Un instante cerca de la medianoche UTC (p. ej. 02:00 UTC = 23:00 local del día anterior) cae en el día local anterior para elegir `weekday` y licencia.
16. Datetime sin zona: se rechaza con error de programación (no resultado de negocio).

## 6. Dependencia de C-01 (mínimo de arranque)

C-01 completo incluye Docker Compose, frontend, Celery, SMTP, `.env.example`, health endpoint, etc.; nada de eso se necesita para una función pura. `CHANGES.md` ya marca C-05 como "puro, sin BD" y paralelo a C-02.

Mínimo para implementar sin hacer todo C-01:

- `backend/pyproject.toml` con Python (versión a decidir; la KB no la fija) y pytest como dependencia de desarrollo; configuración de `pytest` con `testpaths` y `pythonpath` apuntando a `backend`.
- Árbol vacío con paquetes: `backend/app/__init__.py`, `backend/app/domain/__init__.py`, `backend/app/domain/appointments/__init__.py`, `backend/tests/unit/domain/appointments/`.
- Sin FastAPI, SQLAlchemy, Celery ni Redis en las dependencias de este change. Zona horaria con `zoneinfo` de la librería estándar (evita dependencias; en Windows puede hacer falta el paquete `tzdata`, a verificar).
- Opcional (podría dejarse para C-01): ruff.

Cómo documentarlo como decisión: en el `design.md` del change, una decisión tipo "DD: arranque mínimo de `backend/` para C-05 sin ejecutar C-01"; agregar una línea en `CHANGES.md` (o en la nota del change) diciendo que C-01 absorbe y extiende ese esqueleto (no lo rehace ni lo contradice: misma ruta `backend/`, mismo `pyproject.toml`, mismos paquetes). Riesgo: conflictos de merge si C-01 se hace en paralelo (CHANGES.md GATE 0 propone dos agentes); mitigación: C-01 debería partir del esqueleto ya existente. Dejar la decisión explícita para que el profesor la vea.

## 7. Riesgos, ambigüedades e inconsistencias

1. **Tamaño de C-05 vs este change.** C-05 completo (timezone, schedules, compute_slots, validate_appointment, transiciones, patients, puertos, repos en memoria) es mucho más grande que lo pedido. Este change es solo una porción (`validate_appointment` sin transiciones ni `compute_slots`). Hay que decidir cómo queda reflejado en `CHANGES.md` (subdividir C-05 en C-05a / C-05b, o marcar el scope recortado) para que C-07, C-08 y C-09 no asuman que C-05 está completo.
2. **KB vs informe de Discovery (sección D.3).** El informe recomienda agenda "multi-sillón/box, con duración por prestación, bloqueos"; la KB lo recorta a "por profesional" (DD-08, RN-TU-09/10). No es contradicción oculta (DD-07/DD-08 lo explican), pero hay que decir en el change que cubre la parte "multi-profesional con prevención de solapamientos", no sillones ni duración. Coincide con la tabla de cobertura de `CHANGES.md` ("Parcial").
3. **Zona horaria.** `working_hours` (hora local, `time`) y `time_off` (fecha local) no llevan zona; `appointments` está en UTC. Hay que pasar `timezone` como dato. SU-01 (Buenos Aires) está sin confirmar; `clinic_settings.timezone` es la fuente de verdad en ejecución. En el dominio no se debe fijar Buenos Aires a mano. Argentina no usa horario de verano hoy, pero la solución general (zoneinfo) cubre zonas con DST: horas inexistentes o repetidas (a investigar solo si se quiere soportar otras zonas; con la zona por defecto no ocurre).
4. **"No en el pasado" depende del reloj.** Si la función llama a "ahora" adentro, los tests se vuelven frágiles. Recomendación: inyectar `now`. Falta definir si `starts_at == now` es pasado (ver pregunta 3).
5. **Convención de `weekday`.** El modelo dice `smallint (0-6)` pero no dice si 0 es lunes o domingo. Python usa 0 = lunes (`datetime.weekday()`); `isoweekday` usa 1 a 7. Hay que fijarlo antes de escribir tests.
6. **Licencias.** `time_off` es por días completos (RN-HO-03, y CHANGES.md "solo bloqueos por día completo"). Falta decir qué día usa para comparar: el día local de `starts_at` (y de `ends_at` si cruza medianoche, no pasa en horarios razonables). Fechas inclusivas en ambos extremos, según el CHECK `starts_on <= ends_on`.
7. **Estados que ocupan.** El constraint y RN-TU-01 solo consideran `scheduled`. `completed` y `no_show` no bloquean según la letra, aunque normalmente son turnos pasados y `IN_THE_PAST` ya los cubre. Hay que dejarlo escrito para que no haya duda.
8. **Duplicidad de validación y concurrencia.** La validación del dominio no previene la carrera entre dos recepcionistas (US-007). Solo el constraint de C-02 lo hace. Debe quedar explícito en el change que este módulo no cierra ese criterio de aceptación.
9. **Orden de validaciones.** KB y CHANGES.md lista "grilla, dentro de tramo, fuera de licencia, no pasado, sin solape" pero no fijan qué motivo gana si fallan varios. Hay que decidirlo (pregunta 4).
10. **Grilla.** RN-TU-02 dice "grilla de slots del horario del profesional" sin definir el ancla (inicio del tramo vs. hora en punto). Con tramos que arrancan en múltiplos de `slot_minutes` da lo mismo, pero hay que definirlo.
11. **AGENTS.md vs trailers de commit.** AGENTS.md regla 8 prohíbe `Co-Authored-By` en commits, mientras otras instrucciones de sesión piden agregarlo. No afecta a explore (no se hace commit), pero conviene resolverlo antes de apply.
12. **Gobernanza.** CHANGES.md marca C-05 como MEDIO: implementar con checkpoints y mostrar decisiones no obvias al usuario.

## 8. Preguntas abiertas (máximo 5, priorizadas)

1. **Alcance: ¿el change hace solo la validación de crear (y se subdivide C-05 en CHANGES.md), o la validación completa RN-TU-01 a RN-TU-04 con zona horaria, y qué se deja afuera?**
   Recomendación: función única `validate_appointment` con los cuatro chequeos de crear (grilla, tramo, licencia, pasado, solape), con zona horaria resuelta adentro; fuera `compute_slots`, transiciones, patients y repos en memoria. Subdividir C-05 en `CHANGES.md`.

2. **Convención de `weekday` y ancla de la grilla.** ¿0 = lunes (como `datetime.weekday()`)? ¿La grilla arranca en el inicio de cada tramo?
   Recomendación: 0 = lunes (coincide con Python); grilla anclada al inicio del tramo; documentarlo en el spec.

3. **"Pasado": ¿`starts_at == now` es válido? ¿Se compara con minuto exacto o con margen?**
   Recomendación: `starts_at < now` es pasado (igual a ahora se acepta); `now` inyectado; sin margen en v1.

4. **¿La función devuelve el primer motivo o todos los motivos?**
   Recomendación: devolver un único motivo con orden fijo documentado (pasado, grilla, horario, licencia, solape), más simple de testear y de explicar; la lista completa queda como mejora futura.

5. **Arranque mínimo sin C-01 y forma del resultado.** ¿Se aprueba crear `backend/pyproject.toml` + esqueleto de paquetes + pytest como arranque mínimo (y que C-01 lo extienda), y devolver un resultado/enum en vez de lanzar excepción?
   Recomendación: sí a ambos; registrarlo como decisión en `design.md` y como nota en `CHANGES.md`; las excepciones tipadas de `app/core/errors.py` se envuelven en C-08. Alternativa de menor riesgo si el profesor prefiere seguir el orden: hacer primero C-01 recortado.

(La zona horaria SU-01 y la validez de varios turnos por paciente SU-05 ya tienen suposición en la KB; se usan tal cual y no se vuelven a preguntar.)

## 9. Verificación de los 3 criterios del profesor

1. **Pertenece al MVP de la sección D del informe: SÍ, con matiz.** D.3 incluye "Agenda multi-profesional y multi-sillón/box ... y prevención de solapamientos"; este change cubre la parte multi-profesional y de prevención de solapamientos. Sillón/box y duración por prestación quedan afuera por decisión DD-08.
2. **Tiene reglas de negocio verificables: SÍ.** RN-TU-01 a RN-TU-04 (más RN-HO-03) son deterministas y se expresan como escenarios dado/cuando/entonces con entradas y salidas concretas, probables con pytest sin base ni red.
3. **Es lo bastante chico: SÍ, si se acota como está definido.** Una sola función de dominio sin interfaz, base ni endpoint; pero solo si se subdivide C-05 (que completo es más grande) y se resuelve la pregunta 1.
