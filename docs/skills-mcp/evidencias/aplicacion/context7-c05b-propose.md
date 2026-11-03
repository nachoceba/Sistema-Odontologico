# Evidencia: uso del MCP Context7 en la fase PROPOSE de C-05b

Fecha: 2026-11-03. Change: C-05b `calcular-slots-disponibles`. Consulta distinta de las ya documentadas (`zoneinfo` en `../mcp-context7-uso.md` y `pytest.mark.parametrize` en `context7-c05b-pytest.md`).

Objetivo de la consulta: decidir, con documentación oficial y no de memoria, (a) cómo representar la salida de `compute_slots` (tipo `Slot` inmutable con un estado enumerado) y (b) qué garantiza Python al comparar los `datetime` con zona que devuelve la función contra los esperados de los tests.

## Solicitudes (respondieron de verdad, sin simular)

1. `mcp__context7__resolve-library-id` con `libraryName: "Python"` y la consulta "Python 3.12 standard library dataclasses frozen with enum field, and comparing timezone-aware datetime objects (equality across different tzinfo)". Devolvió como primer candidato `/python/cpython` (reputación alta, 50 407 fragmentos, versiones v3.9.22, v3.11.14, v3.13.9, v2.7). Se eligió `/python/cpython`. No hay una versión 3.12 exacta en el índice; la documentación consultada es la de la rama principal (`Doc/library/datetime.rst`, `Doc/library/dataclasses.rst`, `Lib/dataclasses.py`).
2. `mcp__context7__query-docs` sobre `/python/cpython`: "datetime: how are timezone-aware datetime objects compared for equality and ordering when they have different tzinfo (UTC vs ZoneInfo)? What happens comparing naive and aware datetimes? Is datetime a subclass of date, and how does isinstance behave?"
3. `mcp__context7__query-docs` sobre `/python/cpython`: "dataclasses frozen=True: immutability, FrozenInstanceError, generated __eq__ and __hash__, order=True comparison; using an Enum member as a field of a frozen dataclass".

No se enviaron datos de pacientes, claves ni código del proyecto.

## Resultado resumido (fuente: documentación de CPython)

Comparación de `datetime` (`datetime.rst`):

- Dos `datetime` con zona son iguales si representan el mismo instante; si tienen `tzinfo` distinto, la comparación actúa como si ambos se pasaran antes a UTC.
- Un `datetime` sin zona (naive) y uno con zona nunca son iguales (`==` da `False`, no lanza error desde Python 3.3).
- Comparar con `<`, `>`, `<=`, `>=` un naive contra uno con zona lanza `TypeError`.
- Un `date` siempre es naive; un `datetime` es "aware" si `utcoffset()` no devuelve `None`.

Dataclasses congeladas (`dataclasses.rst`, `dataclasses.py`):

- `frozen=True` agrega `__setattr__` y `__delattr__` que lanzan `FrozenInstanceError` (subclase de `AttributeError`) al asignar un campo.
- Con `eq=True` (por defecto) y `frozen=True`, el decorador genera `__hash__`: las instancias se pueden usar en sets y como claves.
- El `__eq__` generado compara campo por campo con `==`, después de comprobar que ambas instancias son de la misma clase. Por eso la igualdad de dos `Slot` delega en la igualdad de `datetime` (instante, no representación) y en la de los miembros del enum.

Lo que la documentación devuelta NO respondió: la parte de la pregunta 2 sobre si `datetime` es subclase de `date` (y cómo se comporta `isinstance`) no apareció en los fragmentos. No se la atribuye a Context7.

## Qué aportó al change

- **Tipo de salida**: `Slot` como `@dataclass(frozen=True)` con `starts_at`, `ends_at` y `status: SlotStatus`, y `SlotStatus(Enum)` con `FREE`, `BUSY`, `OUTSIDE_HOURS`. Es la misma convención de `types.py` (C-05a) y la doc confirma que da inmutabilidad, igualdad por valor y hash sin código extra. Se registra en `design.md` (decisión D-T1).
- **Comparación en los tests**: como la igualdad de `datetime` con zona compara instantes, los tests pueden comparar `slot.starts_at == local(2026, 10, 5, 9, 0)` (UTC) aunque la implementación construya el instante desde la hora local de Buenos Aires. Pero la spec exige igual que las horas salgan en UTC (`tzinfo` = UTC), porque eso no lo garantiza la igualdad: se agrega un test que verifica `utcoffset() == timedelta(0)` en cada franja.
- **Turnos existentes naive**: comparar con `<` un `ExistingAppointment` naive contra una franja con zona lanzaría `TypeError`, no `ValueError`. El design lo deja como contrato heredado de C-05a (los turnos existentes llegan en UTC con zona) y no agrega una validación nueva, para no ampliar el alcance.
- **Límite**: la doc no fija cómo nombrar ni agrupar los tipos; ubicar `Slot` en `types.py` es una decisión del equipo.
