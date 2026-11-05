# Evidencia de uso real del MCP Postgres MCP Pro (`postgres-odonto`)

Fecha: 2026-11-05. Base: la de desarrollo del `docker compose` (PostgreSQL 16.15, base `odonto`). Modo `--access-mode=restricted` (solo lectura). `claude mcp get postgres-odonto` devolvió `Status: ✔ Connected`, tipo `stdio`, ejecutado con `docker run` dentro de la red `sistema-odontologico_default`.

Todo lo de abajo es lo que devolvió la herramienta en esta sesión. Datos del consultorio: solo ficticios.

## Solicitudes y resultados

| # | Herramienta | Qué se pidió | Resultado |
|---|---|---|---|
| 1 | `list_schemas`, `list_objects` | Esquemas y tablas | Esquema de usuario `public` con 9 tablas: `alembic_version`, `appointments`, `clinic_settings`, `email_notifications`, `patients`, `professionals`, `time_off`, `users`, `working_hours` |
| 2 | `get_object_details` | Detalle de `appointments` | 10 columnas (`starts_at` y `ends_at` son `timestamptz`, `status` es el enum `appointment_status`) y el índice `ex_appointments_no_overlap` de tipo GiST sobre `(professional_id, tstzrange(starts_at, ends_at, '[)'))` con `WHERE status = 'scheduled'` |
| 3 | `execute_sql` sobre `pg_constraint` | Constraints de `appointments`, `time_off` y `working_hours` | `ex_appointments_no_overlap` figura como `EXCLUDE USING gist (professional_id WITH =, tstzrange(starts_at, ends_at, '[)') WITH &&) WHERE (status = 'scheduled')`; también `ck_appointments_starts_before_ends`, checks de `working_hours` (día 0–6, sin segundos, inicio < fin) y `ck_time_off_starts_before_or_on_ends`. Las claves foráneas son `ON DELETE RESTRICT` |
| 4 | `execute_sql` | Versión, extensiones y conteos | PostgreSQL 16.15; extensiones `plpgsql` y `btree_gist 1.7`; 2 turnos, 10 pacientes, 2 profesionales, 4 usuarios |
| 5 | `execute_sql` | Estado de los turnos | Los 2 turnos están en `cancelled` (quedaron de las pruebas manuales de C-08) |
| 6 | `execute_sql` | Control de superposición en los datos: turnos `scheduled` del mismo profesional que se pisen (autounión con `a.starts_at < b.ends_at AND b.starts_at < a.ends_at`) | Sin filas. Con 0 turnos `scheduled` el resultado es trivial y **no prueba** la regla; solo confirma que no hay datos inconsistentes |
| 7 | `execute_sql` | Profesionales con usuario, tramos de horario y turnos | 2 profesionales, ambos con usuario: uno con 5 tramos y 0 turnos, otro con 10 tramos y 2 turnos |
| 8 | `explain_query` (sin `analyze`) | La consulta de la agenda de C-09: turnos de un profesional en una semana, unidos con `patients` | Plan: Nested Loop con Index Scan sobre `appointments` y sobre `patients`, costo 0.29..16.38. Usa índice, no recorre toda la tabla. Con 2 filas el planificador puede elegir cualquier plan; no es una medición de rendimiento |
| 9 | `analyze_db_health` | Chequeo completo | Sin índices inválidos, duplicados ni inflados; sin constraints inválidos; sin riesgo de wraparound; 9 conexiones sanas. Marca como "poco usados" 8 índices con 0 escaneos y 0 MB, incluido `ex_appointments_no_overlap`. Con esta base casi vacía y sin tráfico ese aviso no es una recomendación válida |

## Pruebas del límite de solo lectura y del validador

| # | Consulta | Resultado | Lectura |
|---|---|---|---|
| 10 | `DELETE FROM appointments WHERE false` | `Error validating query` | El modo restringido rechazó una escritura. La condición `WHERE false` garantizaba que, de ejecutarse, no tocaba filas |
| 11 | Autounión de turnos usando `tstzrange(...) && tstzrange(...)` | `Error validating query` | El validador no acepta esa expresión aunque sea de lectura |
| 12 | `SELECT tstzrange(starts_at, ends_at, '[)') FROM appointments LIMIT 1` | `Error validating query` | Aislando la causa: el validador del modo restringido rechaza la función `tstzrange`. La misma consulta reescrita con comparaciones simples (solicitud 6) sí pasó |

Sin verificar: la causa exacta (lista de funciones permitidas del modo restringido). Sale de comparar las tres consultas, no de la documentación del proyecto.

## Qué aportó al proyecto

- Confirma, mirando la base real y no la migración, que la regla de no superposición (regla dura 6) está bloqueada por la base: constraint de exclusión sobre el rango del turno, solo para `scheduled`, con `btree_gist` instalada.
- Confirma que la agenda de C-09 consulta por `professional_id` y rango de `starts_at` usando índice.
- Detectó una incoherencia en los docs: se había anotado compatibilidad con PostgreSQL 18 como pendiente; el entorno real es 16.15.
- Límite práctico: como el modo restringido rechaza `tstzrange`, la superposición no se puede auditar con el operador `&&`; hay que usar comparaciones de `starts_at` y `ends_at`.

## Qué no hizo

- No modificó datos ni esquema: ninguna consulta de escritura se ejecutó.
- Los análisis de índices (`analyze_workload_indexes`, `analyze_query_indexes`) y `get_top_queries` no se corrieron: la base casi no tiene datos ni historial, y `pg_stat_statements` no figura entre las extensiones instaladas.
