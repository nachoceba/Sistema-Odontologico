# Spec Delta

## Purpose

Decidir, sin base de datos ni pantalla, si el conjunto de tramos de horario de un profesional y cada una de sus licencias son válidos antes de guardarlos (RN-HO-01, RN-HO-02, constraints de `04_modelo_de_datos.md`), y responder si una fecha local cae dentro de una licencia (RN-HO-03).

## ADDED Requirements

> Datos comunes de los escenarios (salvo que el escenario diga otra cosa): los días de la semana se numeran 0 = lunes … 6 = domingo; las horas son locales del consultorio; los tramos se interpretan como intervalos semiabiertos `[inicio, fin)`. Todos los datos son ficticios. Las decisiones de dominio P-1 a P-10 fueron confirmadas por el usuario (ver `design.md` y DD-21 a DD-30 en la KB).

### Requirement: Resultado de la validación de tramos

La validación SHALL recibir el conjunto completo de tramos de un profesional y devolver un resultado, sin lanzar excepciones por motivos de negocio. El resultado MUST indicar si el conjunto es válido y, si no lo es, MUST listar todos los problemas encontrados (no solo el primero), cada uno con un código y la identificación de los tramos involucrados. Un conjunto vacío (profesional sin horario) MUST ser válido. La validación MUST ser determinista y no depender del orden en que llegan los tramos.

#### Scenario: Horario semanal válido (funcionamiento esperado)
- **DADO** que la Dra. A tiene los tramos lunes 09:00–13:00, lunes 14:00–18:00 y miércoles 09:00–13:00
- **CUANDO** se validan sus tramos
- **ENTONCES** el resultado es válido y no lista ningún problema (RN-HO-01, RN-HO-02)

#### Scenario: Profesional sin tramos
- **DADO** un conjunto de tramos vacío
- **CUANDO** se validan los tramos
- **ENTONCES** el resultado es válido y no lista ningún problema

#### Scenario: Varios problemas a la vez se informan todos
- **DADO** los tramos lunes 10:00–09:00, martes 09:00–12:00 y martes 11:00–13:00
- **CUANDO** se validan los tramos
- **ENTONCES** el resultado es inválido
- **Y** lista un problema de inicio no anterior al fin para el tramo del lunes
- **Y** lista un problema de superposición entre los dos tramos del martes

### Requirement: Inicio anterior al fin (RN-HO-02)

Cada tramo MUST tener `start_time` estrictamente anterior a `end_time`. Un tramo con inicio igual o posterior al fin SHALL informarse con el código `START_NOT_BEFORE_END`. En consecuencia un tramo no puede cruzar la medianoche ni terminar a las 24:00.

#### Scenario: Inicio posterior al fin (error de negocio)
- **DADO** el tramo lunes 13:00–09:00
- **CUANDO** se validan los tramos
- **ENTONCES** el resultado es inválido con el código `START_NOT_BEFORE_END` para ese tramo

#### Scenario: Tramo de duración cero (borde)
- **DADO** el tramo lunes 09:00–09:00
- **CUANDO** se validan los tramos
- **ENTONCES** el resultado es inválido con el código `START_NOT_BEFORE_END` para ese tramo

#### Scenario: Tramo que intenta cruzar la medianoche (borde)
- **DADO** el tramo viernes 20:00–00:00
- **CUANDO** se validan los tramos
- **ENTONCES** el resultado es inválido con el código `START_NOT_BEFORE_END` para ese tramo

#### Scenario: Tramo más corto que un slot (borde)
- **DADO** el tramo lunes 09:00–09:15 y `slot_minutes = 30`
- **CUANDO** se validan los tramos
- **ENTONCES** el resultado es válido: la validación de tramos no depende de `slot_minutes` y `slot-availability` muestra ese tramo como `OUTSIDE_HOURS`

### Requirement: Día de la semana dentro de rango (RN-HO-01)

Cada tramo MUST tener un día de la semana entre 0 y 6 inclusive (`weekday smallint (0-6)` en `04_modelo_de_datos.md`). Un valor fuera de ese rango SHALL informarse con el código `INVALID_WEEKDAY`.

#### Scenario: Día de la semana 7 (error de negocio)
- **DADO** un tramo con día de la semana 7, de 09:00 a 13:00
- **CUANDO** se validan los tramos
- **ENTONCES** el resultado es inválido con el código `INVALID_WEEKDAY` para ese tramo

#### Scenario: Domingo y día negativo (borde)
- **DADO** un tramo con día de la semana 6 (domingo) de 09:00 a 12:00 y otro con día de la semana -1 de 09:00 a 12:00
- **CUANDO** se validan los tramos
- **ENTONCES** solo el tramo con día -1 se informa con el código `INVALID_WEEKDAY`

### Requirement: Tramos del mismo día sin superposición (RN-HO-02)

Dos tramos válidos del mismo día de la semana MUST NOT superponerse. Se superponen cuando sus intervalos semiabiertos `[inicio, fin)` comparten algún instante. Dos tramos que solo se tocan en el borde (uno termina cuando empieza el otro) NO se superponen, coherente con el escenario "Tramos contiguos con anclas distintas" de `slot-availability`. Cada par superpuesto SHALL informarse una vez con el código `OVERLAPPING_BLOCKS` y los dos tramos involucrados. Tramos de días distintos nunca se superponen. Un tramo que ya tiene `START_NOT_BEFORE_END` o `INVALID_WEEKDAY` MUST NOT participar del chequeo de superposición.

#### Scenario: Tramos superpuestos el mismo día (error de negocio)
- **DADO** los tramos lunes 09:00–13:00 y lunes 12:00–15:00
- **CUANDO** se validan los tramos
- **ENTONCES** el resultado es inválido con el código `OVERLAPPING_BLOCKS` para ese par

#### Scenario: Tramos contiguos (borde)
- **DADO** los tramos lunes 09:00–13:00 y lunes 13:00–17:00
- **CUANDO** se validan los tramos
- **ENTONCES** el resultado es válido

#### Scenario: Tramo contenido en otro (borde)
- **DADO** los tramos lunes 09:00–18:00 y lunes 10:00–11:00
- **CUANDO** se validan los tramos
- **ENTONCES** el resultado es inválido con el código `OVERLAPPING_BLOCKS` para ese par

#### Scenario: Tramo duplicado (borde)
- **DADO** dos tramos idénticos lunes 09:00–13:00
- **CUANDO** se validan los tramos
- **ENTONCES** el resultado es inválido con un único problema `OVERLAPPING_BLOCKS` para ese par

#### Scenario: Mismo horario en días distintos
- **DADO** los tramos lunes 09:00–13:00 y martes 09:00–13:00
- **CUANDO** se validan los tramos
- **ENTONCES** el resultado es válido

#### Scenario: Tres tramos superpuestos entre sí
- **DADO** los tramos lunes 09:00–12:00, lunes 10:00–13:00 y lunes 11:00–14:00
- **CUANDO** se validan los tramos
- **ENTONCES** el resultado lista tres problemas `OVERLAPPING_BLOCKS`, uno por cada par

#### Scenario: El orden de entrada no cambia el resultado
- **DADO** los tramos lunes 12:00–15:00 y lunes 09:00–13:00 (en ese orden)
- **CUANDO** se validan los tramos
- **ENTONCES** el resultado es el mismo que si llegaran en el orden inverso: un problema `OVERLAPPING_BLOCKS` para ese par

#### Scenario: Un tramo inválido no genera superposiciones extra
- **DADO** los tramos lunes 15:00–08:00 y lunes 09:00–13:00
- **CUANDO** se validan los tramos
- **ENTONCES** el resultado lista solo `START_NOT_BEFORE_END` para el primer tramo y ningún `OVERLAPPING_BLOCKS`

### Requirement: Horas en minutos exactos

Cada tramo MUST tener inicio y fin en minutos exactos (sin segundos ni fracciones), porque la grilla de slots se cuenta en minutos (RN-TU-02). Un tramo con segundos o fracciones SHALL informarse con el código `SUB_MINUTE_PRECISION`.

#### Scenario: Tramo con segundos (borde)
- **DADO** el tramo lunes 09:00:30–13:00
- **CUANDO** se validan los tramos
- **ENTONCES** el resultado es inválido con el código `SUB_MINUTE_PRECISION` para ese tramo

### Requirement: Validez de una licencia

Una licencia SHALL ser válida cuando `starts_on <= ends_on` (constraint de `time_off` en `04_modelo_de_datos.md`). Si `starts_on > ends_on`, la validación MUST devolver un resultado inválido con el código `END_BEFORE_START`, sin lanzar excepción. La validación de una licencia MUST NOT depender de otras licencias ni de la fecha actual.

#### Scenario: Licencia de varios días (funcionamiento esperado)
- **DADO** una licencia del 12 al 16 de octubre de 2026
- **CUANDO** se valida la licencia
- **ENTONCES** el resultado es válido

#### Scenario: Licencia de un solo día (borde)
- **DADO** una licencia del 12 al 12 de octubre de 2026
- **CUANDO** se valida la licencia
- **ENTONCES** el resultado es válido

#### Scenario: Fin anterior al inicio (error de negocio)
- **DADO** una licencia del 16 al 12 de octubre de 2026
- **CUANDO** se valida la licencia
- **ENTONCES** el resultado es inválido con el código `END_BEFORE_START`

### Requirement: Fecha local dentro de una licencia (RN-HO-03)

El sistema SHALL responder si una fecha local cae dentro de alguna de las licencias dadas, con ambos extremos inclusivos. Con una lista de licencias vacía la respuesta MUST ser negativa. Licencias superpuestas entre sí MUST NOT cambiar la respuesta. Esta consulta MUST dar la misma respuesta que la regla de licencias que ya usan `appointment-creation` y `slot-availability` (una sola fuente).

#### Scenario: Fecha dentro de la licencia
- **DADO** una licencia del 12 al 16 de octubre de 2026
- **CUANDO** se consulta el 14 de octubre de 2026
- **ENTONCES** la respuesta es afirmativa

#### Scenario: Primer y último día de la licencia (borde)
- **DADO** una licencia del 12 al 16 de octubre de 2026
- **CUANDO** se consultan el 12 y el 16 de octubre de 2026
- **ENTONCES** ambas respuestas son afirmativas

#### Scenario: Día siguiente al fin de la licencia (borde)
- **DADO** una licencia del 12 al 16 de octubre de 2026
- **CUANDO** se consulta el 17 de octubre de 2026
- **ENTONCES** la respuesta es negativa

#### Scenario: Sin licencias
- **DADO** una lista de licencias vacía
- **CUANDO** se consulta cualquier fecha
- **ENTONCES** la respuesta es negativa
