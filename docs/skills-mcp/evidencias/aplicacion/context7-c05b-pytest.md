# Evidencia: uso del MCP Context7 para los tests de bordes de C-05b con pytest

Fecha: 2026-11-03. Change: C-05b `calcular-slots-disponibles`. Tarea distinta de la ya documentada con `zoneinfo` (`../mcp-context7-uso.md`).

## Solicitudes (respondieron de verdad, sin simular)

1. `resolve-library-id`: librería `pytest`; consulta "pytest.mark.parametrize con ids legibles para tests de casos de borde de una función pura". Devolvió dos candidatos: `/pytest-dev/pytest` (reputación alta, 7742 fragmentos, versiones 9.0.0, 8.3.4, 9.1.1, 7.4.3, 8.4.2, 9.2.0, 8.3.5) y `/websites/pytest_en_stable`. Se eligió `/pytest-dev/pytest`.
2. `query-docs` sobre `/pytest-dev/pytest`: "pytest.mark.parametrize with readable ids (ids list, ids callable, pytest.param id) for edge-case boundary tests of a pure function".

No se enviaron datos de pacientes ni claves.

## Resultado resumido (fuente: documentación de pytest, `parametrize.rst` y `reference.rst`)

- `@pytest.mark.parametrize("a,b,expected", testdata)` genera ids automáticos poco legibles (`a0-b0-expected0`).
- Hay cuatro formas de dar nombre: ids por defecto, `ids=[...]` con una lista, `ids=idfn` con una función, y `pytest.param(..., id="nombre")`.
- `pytest.param(*values, id=..., marks=...)` permite además marcar un caso individual (`xfail`, marcas propias). Los ids sirven con `--collect-only` y con `-k`.

## Qué aportó al change

- Los escenarios de borde de C-05b (tramo que no divide, licencia de un día, turnos pegados, desalineado, cambio de día por zona) son una tabla de entradas y salidas sobre la misma función: se escriben con un `parametrize` y `pytest.param(..., id="turno_pegado_10_30_libre")`, uno por escenario de la spec.
- El id legible se traza a la spec: se puede correr un solo borde con `-k` y el fallo dice cuál escenario se rompió.
- `idfn` no conviene para datetimes (la doc misma avisa que perdería horas y minutos): se prefiere `pytest.param` con id explícito.
- Compatible con el estilo de C-05a (funciones `test_...` con helpers en `helpers.py`): los casos parametrizados reutilizan `local()` y `monday()`.
- Límite: la documentación muestra ejemplos genéricos; cómo agrupar los casos por regla es decisión del equipo.
