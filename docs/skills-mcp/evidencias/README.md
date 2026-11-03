# Índice de evidencias (TP Skills + MCP, etapa 8)

Cada fila indica la solicitud realizada, el resultado y lo que aportó al change C-05b `calcular-slots-disponibles`. Una lista de herramientas instaladas no cuenta como evidencia: acá está lo que se pidió y lo que respondió cada herramienta.

## Uso de la skill `revisor-escenarios-turnos`

| Qué se hizo | Solicitud y resultado | Aporte | Archivo |
|---|---|---|---|
| Tres casos de prueba, cada uno con y sin la skill | Revisar escenarios de `compute_slots`, la spec archivada de C-05a y escenarios con reglas solapadas | La skill dio orden y trazabilidad (tabla, respaldo por hallazgo, decisiones para el usuario). En lo esencial el agente sin la skill también detectó los errores graves | `skill-pruebas/` |
| Prueba en una sesión nueva | Escenario de la franja 15:30 sin nombrar la skill; el agente la encontró y la ejecutó | Confirma que el registro y `CLAUDE.md` alcanzan para que el agente la use | `prueba-sesion-nueva-1.png` a `-3.png` |
| Explore del change | Borrador de 13 escenarios de `compute_slots` revisado como skill | Base de las decisiones de dominio que resolvió el usuario | `aplicacion/skill-revisor-c05b.md` |
| Revisión de la spec | 29 escenarios del borrador de la spec: 8 hallazgos | 3 defectos reales corregidos | `aplicacion/skill-revisor-c05b-spec.md` |

## Uso del MCP Context7

| Qué se hizo | Solicitud y resultado | Aporte | Archivo |
|---|---|---|---|
| Conexión y zona horaria | `claude mcp list` conectado; `resolve-library-id` y `query-docs` sobre `zoneinfo` y `astimezone` | Forma de convertir UTC a hora del consultorio y alcance del horario de verano | `mcp-context7-uso.md` |
| Tests de bordes | `/pytest-dev/pytest`, `parametrize` con ids legibles | Diseño de los tests, uno por escenario con `pytest.param(..., id=...)` | `aplicacion/context7-c05b-pytest.md` |
| Tipos de salida | `/python/cpython`, dataclasses `frozen` y comparación de datetimes con zona | Diseño de `Slot` y `SlotStatus`; test de `utcoffset() == 0` | `aplicacion/context7-c05b-propose.md` |

## Revisión crítica: omisiones y errores detectados

### A. Defectos de la spec del change (detectados por la skill)

Tres defectos, con el antes y el después y la regla de la KB que permitió corregirlos: precedencia implícita que chocaba con RN-HO-04, borde de turnos consecutivos faltante (RN-TU-10) y un escenario rotulado "error de negocio" que no lo era (RN-HO-03). Detalle en `aplicacion/revision-critica.md`. Se comprobó que los textos corregidos están en la spec vigente.

### B. Defectos de la propia skill (detectados al probarla)

| # | Qué se detectó | Cómo | Antes | Después |
|---|---|---|---|---|
| 1 | Omisión: la skill no leía `CHANGES.md` ni `04_modelo_de_datos.md` | Comparando las respuestas con y sin la skill: el agente sin la skill vio que la firma de `compute_slots` no incluía la zona horaria; con la skill quedaron sospechas sin confirmar sobre los datos | Fuentes obligatorias: `05`, `10` y `09` | Se suman `04` y la entrada del change en `CHANGES.md`, y un tipo de hallazgo "contrato incompleto" |
| 2 | Faltaba un tipo de hallazgo: el escenario que contradice una regla | En la prueba de la sesión nueva el agente rotuló "contradice una regla", un tipo que la skill no tenía; los agentes de prueba lo habían llamado "ambigüedad" | Seis tipos de problema | Siete: se agrega "contradicción" |

La corrección 1 se verificó en la sesión nueva: el agente reportó el hallazgo "contrato incompleto" sobre la firma de `compute_slots`. Ambas correcciones están en `.claude/skills/revisor-escenarios-turnos/SKILL.md`.

## Limitaciones de las evidencias

- El "antes" de la spec no se puede contrastar con git: la spec no estaba commiteada antes de las correcciones. Se tomó de lo que documentó el sub-agente; sí se verificó que el "después" está en la spec.
- Tras ajustar la skill no se repitieron los tres casos de prueba, solo la prueba en la sesión nueva.
- Las corridas con y sin la skill y las revisiones las hicieron sub-agentes; sus informes son su propio relato. Se verificó que los archivos existen, que `openspec validate --strict` da válido y que los 33 tests de C-05a siguen en verde.
- Context7 no devolvió respuesta a una pregunta (si `datetime` hereda de `date`); no se le atribuyó. Los ejemplos de su documentación usan zonas como Nueva York, no Buenos Aires.
- Con la skill, las respuestas son más largas (unas 1,4 veces en total: 3.575 palabras contra 2.528 en los tres casos) sin detectar más errores graves en lo esencial.
