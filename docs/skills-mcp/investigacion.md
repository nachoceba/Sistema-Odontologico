# Ficha de investigación: skill propia y MCP para el sistema odontológico

Metodología I, TUP. Integrante: Ceballos (trabajo individual). Fecha de consulta de las fuentes: 2026-11-02.

## 1. Necesidad detectada

Al preparar un change, la revisión de los escenarios contra las reglas de la base de conocimiento se hace a mano y se repite en cada change. Es donde se escapan las reglas ambiguas y los casos de borde. Por ejemplo, la KB no dice qué pasa con un tramo de 9:00 a 9:45 cuando el slot dura 30 minutos, ni cómo se comporta un turno a las 23:30 hora local, que en UTC cae al día siguiente.

Además, el código de zona horaria y los tests dependen del detalle de `zoneinfo`, pytest y Pydantic, y conviene consultar su documentación vigente en lugar de responder de memoria.

Las dos incorporaciones son herramientas de desarrollo para el agente. No forman parte del producto.

## 2. Change elegido

**C-05b `calcular-slots-disponibles`**, segundo recorte de C-05 `domain-scheduling-core` (el primero, C-05a `crear-turno-sin-solapamientos`, ya está archivado).

- Alcance: `compute_slots` (cada franja del día como libre, ocupada o fuera de horario) y `app/core/timezone.py` (UTC y zona del consultorio, RN-GL-01).
- Son funciones puras, sin base de datos ni red. Depende solo de C-01, así que se puede preparar sin funcionalidades inexistentes.
- Es la base de la agenda (C-09) y, a futuro, de una reserva online, hoy fuera de v1 (DD-07).
- Descartados: C-02 (nivel CRÍTICO, requiere Docker), C-03 en adelante (dependen del login) y C-01 (infraestructura, la skill casi no aportaría).
- En esta entrega el change solo se prepara. No se implementa ni se archiva.

## 3. Skill creadora y diseño de la skill propia

**Skill creadora: `skill-creator`.** Fuente oficial: repositorio de Anthropic, `anthropics/skills`, carpeta `skills/skill-creator` (https://github.com/anthropics/skills/tree/main/skills/skill-creator). Licencia Apache 2.0, verificada en el `LICENSE.txt` instalado. Compatible con Claude Code, que carga skills desde una carpeta con `SKILL.md` (`~/.claude/skills/` o `.claude/skills/`). Está instalada de forma global en `~/.claude/skills/skill-creator/` y aparece disponible en la sesión del agente.

**Skill propia: `revisor-escenarios-turnos`.**

| Campo | Definición |
|---|---|
| Propósito | Encontrar reglas ambiguas y bordes faltantes en escenarios de agenda |
| Cuándo se activa | Al explorar o escribir la spec de un change de turnos o agenda |
| Entradas | Escenarios o spec borrador, y las reglas RN de la KB |
| Procedimiento | Comparar los escenarios con `05_reglas_de_negocio.md` y `10_preguntas_abiertas.md` y listar los huecos |
| Resultado | Lista de hallazgos, cada uno con la regla que lo respalda o "sin respaldo en la KB" |
| Criterios de revisión | Todo hallazgo cita una regla; las decisiones de dominio nuevas se marcan como tales y no se incorporan solas |

Ubicación: `.claude/skills/revisor-escenarios-turnos/SKILL.md`, dentro del repositorio y versionada. Se registra en `.atl/skill-registry.md`.

## 4. Comparación de dos MCP y elección

Context7 no entra en la comparación: ya venía instalado con el Active Stack y lo tienen todos los compañeros, así que no demuestra una elección propia. Se compara Postgres MCP Pro con DBHub, los dos servidores que sirven para el mismo trabajo (consultar y revisar la base PostgreSQL del proyecto). Datos tomados de los README de cada proyecto (ver fuentes).

| | Postgres MCP Pro | DBHub (Bytebase) |
|---|---|---|
| Propósito | Consultar y analizar una base PostgreSQL | Pasarela liviana para varias bases (PostgreSQL, MySQL, SQL Server, MariaDB, Oracle, SQLite) |
| Herramientas | `list_schemas`, `list_objects`, `get_object_details`, `execute_sql`, `explain_query`, `get_top_queries`, `analyze_workload_indexes`, `analyze_query_indexes`, `analyze_db_health` | `execute_sql` y `search_objects`; opcionales `explain_sql` y `health_check`; herramientas propias en `dbhub.toml` |
| Instalación | Docker, `pipx` o `uv`/`uvx` | `npx @bytebase/dbhub@latest`, Docker o plugin |
| Credenciales | `DATABASE_URI` obligatoria | `--dsn` obligatorio |
| Solo lectura | `--access-mode=restricted` (el valor por defecto en los ejemplos es `unrestricted`, que escribe) | El README declara un "modo solo lectura"; no pude confirmar el parámetro exacto en la página de línea de comandos |
| Licencia | MIT | MIT |
| Versiones de PostgreSQL | Probado en 15, 16 y 17 (el proyecto usa 16) | No declara versiones |

**Elegido: Postgres MCP Pro.** El riesgo central del sistema es la superposición de turnos, que la base bloquea con un constraint de exclusión (`btree_gist`). Postgres MCP Pro trae `explain_query` y el análisis de índices para revisar esa consulta, y un modo `restricted` verificado en su README. El proyecto usa solo PostgreSQL, así que la ventaja de DBHub (varios motores) no suma. DBHub sería mejor opción si hiciera falta una sola herramienta para varias bases o solo explorar el esquema de forma simple. Descartados: Stitch (diseño de interfaces, no aplica) y el servidor oficial de PostgreSQL (archivado el 2025-05-29).

**Límites de uso:** se conecta en modo `restricted` (solo lectura) y únicamente a la base de desarrollo con datos ficticios. La contraseña va en la configuración local del usuario, nunca en el repositorio. No se consulta ninguna base real.

## 5. Pasos de instalación y configuración

1. **Skill creadora:** ya instalada de forma global. Para reproducirla se documentará `npx skills add anthropics/skills@skill-creator -y -a claude-code` (el patrón que usa este proyecto) junto con una copia versionada de su fuente. *Pendiente de verificar el comando exacto.*
2. **Skill propia:** generarla con `skill-creator`, adaptarla al dominio y guardarla en `.claude/skills/`. Comprobar en una sesión nueva que el agente la encuentra.
3. **Postgres MCP Pro:** ejecutarlo en un contenedor Docker dentro de la red de `docker compose` (la base no publica puertos), con `--access-mode=restricted` y `DATABASE_URI` apuntando a la base de desarrollo. Verificar con `claude mcp list` y una consulta real. Configuración de ejemplo sin secretos en el README.
4. **Context7:** ya estaba instalado con el Active Stack. Queda como herramienta complementaria, sin formar parte de la comparación.

## 6. Archivos de la fundación a actualizar

- `.atl/skill-registry.md` (alta de la skill: nombre, propósito, ubicación y usos)
- `CLAUDE.md` y `AGENTS.md` (cuándo usar la skill y el MCP, qué necesitan, cómo revisar el resultado y los límites del MCP; ambos archivos se mantienen iguales)
- `README.md` (requisitos, variables, comprobación y solución de problemas del MCP)
- `CHANGES.md` (referencia a C-05b)
- `knowledge-base/` y `skills-lock.json`, solo si resultan afectados
- `openspec/changes/calcular-slots-disponibles/` (proposal, design, specs y tasks)

## 7. Pendientes no verificados

- Parámetro exacto del modo solo lectura de DBHub: no figura en su página de línea de comandos (se configuraría en el archivo TOML).
- Comando exacto de instalación de `skill-creator` con `npx skills`.
- Resuelto: el entorno local usa PostgreSQL 16 (`postgres:16-alpine` en `docker-compose.yml`), dentro del rango probado por Postgres MCP Pro. La nota anterior que decía 18 era incorrecta.

## 8. Fuentes (consultadas el 2026-11-02)

- skill-creator: https://github.com/anthropics/skills/tree/main/skills/skill-creator
- DBHub: https://github.com/bytebase/dbhub (README y https://dbhub.ai/config/command-line)
- Comparativas de terceros, con intereses propios: https://www.bytebase.com/blog/top-postgres-mcp-servers/ (la publica quien mantiene DBHub) y https://ai2sql.io/postgres-mcp-server-comparison
- Postgres MCP Pro: https://github.com/crystaldba/postgres-mcp (README: https://raw.githubusercontent.com/crystaldba/postgres-mcp/main/README.md)
- MCP oficial de PostgreSQL, archivado el 2025-05-29: https://github.com/modelcontextprotocol/servers-archived/tree/main/src/postgres
