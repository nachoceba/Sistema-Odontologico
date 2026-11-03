# Informe de aplicación: skill propia y MCP en el sistema odontológico

Metodología I, TUP. Trabajo individual: Ceballos. Fecha: 2026-11-03.

## 1. Qué se hizo

Se incorporaron dos herramientas de desarrollo para el agente (Claude Code) y se usaron para preparar un change pendiente, sin implementarlo:

- **Skill propia `revisor-escenarios-turnos`**, creada con `skill-creator` (Anthropic, Apache 2.0). Revisa escenarios de agenda contra la base de conocimiento y lista ambigüedades, contradicciones, bordes faltantes, reglas solapadas, preguntas abiertas, decisiones sin respaldo y contrato incompleto. Cada hallazgo cita su regla o dice "sin respaldo en la KB".
- **MCP Context7**, para consultar documentación vigente de librerías. Servidor local sin clave de API; solo lee documentación pública.
- **Change preparado: C-05b `calcular-slots-disponibles`** (segundo recorte de C-05): `compute_slots` y `app/core/timezone.py`. Solo se preparó: no está implementado, verificado ni archivado.

También se corrigió un faltante del trabajo anterior: C-05a `crear-turno-sin-solapamientos` no figuraba como change propio en el roadmap y ahora está registrado.

## 2. Resultados

| Resultado | Dato |
|---|---|
| Skill integrada | En `.claude/skills/`, registrada en `.atl/skill-registry.md` y descrita en `CLAUDE.md` y `AGENTS.md` (iguales entre sí). Una sesión nueva la encontró y la ejecutó sin que se la nombrara |
| MCP operativo | `claude mcp list` conectado; `resolve-library-id` y `query-docs` usados en tres consultas reales. Documentado en el README con configuración de ejemplo sin secretos |
| Change preparado | proposal, design, 2 specs con **31 escenarios** (24 + 7) y **41 tasks** sin ejecutar; `openspec validate --strict` válido |
| Código existente | Sin cambios: los 33 tests de C-05a siguen en verde |
| Decisiones de dominio | 9 decisiones resueltas por el usuario, registradas como DD-15 a DD-20 y ampliación de SU-01, marcando las que no tienen respaldo en la KB |

La spec incluye escenarios de funcionamiento esperado, de entrada inválida y de borde (tramo que no divide el slot, turnos pegados, licencia, medianoche local, día sin tramos). Cada tarea indica el test que lo verificará.

## 3. Evidencias

Índice completo en `docs/skills-mcp/evidencias/README.md`. Principales:

- Skill, pruebas con y sin la skill: `evidencias/skill-pruebas/`; en sesión nueva: `evidencias/prueba-sesion-nueva-1.png` a `-3.png`.
- Skill en la preparación: `evidencias/aplicacion/skill-revisor-c05b.md` y `skill-revisor-c05b-spec.md`.
- Context7: `evidencias/mcp-context7-uso.md`, `evidencias/aplicacion/context7-c05b-pytest.md` y `context7-c05b-propose.md`.
- Qué aportó Context7: confirmó cómo convertir UTC a hora del consultorio, dio el diseño de los tests con `pytest.param` y el de los tipos `Slot` y `SlotStatus`.

## 4. Archivos modificados y motivo

| Archivo | Motivo |
|---|---|
| `.claude/skills/revisor-escenarios-turnos/SKILL.md` (nuevo) | La skill propia |
| `.atl/skill-registry.md` | Registrar la skill (propósito, ubicación y usos) |
| `CLAUDE.md` y `AGENTS.md` | Explicar cuándo usar la skill y el MCP, qué necesitan, límites y cómo revisar el resultado; registrar C-05a y C-05b |
| `README.md` | Documentar el MCP (requisitos, variables, comprobación, límites) y las carpetas nuevas |
| `CHANGES.md` | Registrar C-05a y C-05b; actualizar la firma de `compute_slots` |
| `knowledge-base/09_decisiones_y_supuestos.md` | Agregar DD-15 a DD-20 y ampliar SU-01 con las decisiones de C-05b |
| `openspec/changes/calcular-slots-disponibles/` (nuevo) | Proposal, design, specs y tasks del change |
| `docs/opsx/explore-calcular-slots-disponibles.md` (nuevo) | Exploración del change |
| `docs/skills-mcp/` (nuevo) | Ficha de investigación, este informe, referencia de `skill-creator`, ejemplo del MCP y evidencias |

No se regeneró la fundación completa y no se marcó como ejecutada ninguna etapa que no se hizo.

## 5. Revisión crítica

**Defectos de la spec detectados por la skill (3), con antes y después** en `evidencias/aplicacion/revision-critica.md`: una precedencia entre estados que estaba implícita y chocaba con RN-HO-04; el borde de turnos consecutivos que faltaba (RN-TU-10); y un escenario rotulado "error de negocio" que en realidad no lo era (RN-HO-03). Se verificó que los textos corregidos están en la spec.

**Defectos de la propia skill (2), detectados al probarla:**
1. No leía `CHANGES.md` ni `04_modelo_de_datos.md`. Lo vi al comparar las respuestas con y sin la skill: el agente sin la skill notó que la firma de `compute_slots` no incluía la zona horaria. Se corrigió y una sesión nueva ya reportó ese hallazgo.
2. Le faltaba el tipo "contradicción" (un escenario que choca con una regla). Se vio en la prueba de la sesión nueva, donde el agente usó un rótulo que la skill no tenía. Se agregó.

## 6. Limitaciones

- En los casos de prueba el agente **sin** la skill también detectó los errores graves; la skill aportó orden y trazabilidad, no más detección en lo esencial, y respuestas unas 1,4 veces más largas.
- El "antes" de la spec no se puede contrastar con git (no estaba commiteada); el "después" sí se verificó.
- Tras ajustar la skill no se repitieron los tres casos de prueba.
- Las corridas con sub-agentes son su propio relato; se verificó que los archivos existen y que los tests y la validación pasan.
- Context7 no respondió una pregunta puntual (herencia de `datetime`); no se le atribuyó. Sus ejemplos usan otras zonas horarias.
- Sin verificar: límites de uso de Context7, compatibilidad de Postgres MCP Pro con PostgreSQL 18, y el comando exacto de instalación de `skill-creator` con `npx skills` (solo se probó el listado).
- El proyecto no tiene typecheck ni lint configurados, aunque las reglas del proyecto los piden; quedó registrado en las tasks.
- Quedan dos preguntas menores abiertas en el design (zona horaria inexistente y turnos existentes sin zona).
