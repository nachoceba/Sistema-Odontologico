# Spec Delta

## ADDED Requirements

### Requirement: Listar los turnos agendados de todos los profesionales que empiezan en un rango (DD-66)

Listar SHALL recibir un rango `[desde, hasta)` de instantes con zona horaria, ambos obligatorios, y MUST devolver los turnos en estado `scheduled` de todos los profesionales cuyo **inicio** cae dentro del rango, ordenados por inicio y, a igual inicio, por identificador. A diferencia de los listados por profesional o por paciente, el criterio es el inicio y no la superposición: un turno que empieza antes de `desde` MUST NOT incluirse aunque termine dentro del rango, y uno que empieza exactamente en `hasta` tampoco. Los turnos `cancelled`, `completed` y `no_show` MUST NOT incluirse. No filtra por profesional ni paciente activos. Lo usa la pasada de recordatorios (spec `reminder-scheduling`). Instantes sin zona horaria, o `desde` no anterior a `hasta`, MUST lanzar `ValueError`.

#### Scenario: Turnos agendados de un día de todos los profesionales (esperado)
- **DADO** turnos `scheduled` el lunes a las 10:00 con la Dra. A y a las 09:00 con el Dr. B, y un turno `cancelled` el lunes a las 11:00 con la Dra. A
- **CUANDO** se listan los turnos agendados que empiezan entre el inicio y el fin del lunes local (convertidos a UTC)
- **ENTONCES** se devuelven el del Dr. B de las 09:00 y el de la Dra. A de las 10:00, en ese orden, sin el cancelado

#### Scenario: Solo cuenta el inicio (borde)
- **DADO** un turno `scheduled` de la Dra. A del domingo 23:45 al lunes 00:15 hora local y otro del lunes 00:00 a 00:30
- **CUANDO** se listan los turnos agendados que empiezan el lunes local
- **ENTONCES** se devuelve solo el del lunes 00:00

#### Scenario: Límite superior excluido (borde)
- **DADO** un turno `scheduled` que empieza el martes 00:00 hora local
- **CUANDO** se listan los turnos agendados que empiezan el lunes local
- **ENTONCES** no se devuelve

#### Scenario: Estados que no cuentan (error de negocio)
- **DADO** turnos del lunes en estado `completed`, `no_show` y `cancelled`
- **CUANDO** se listan los turnos agendados que empiezan el lunes local
- **ENTONCES** se devuelve una lista vacía

#### Scenario: Mismo inicio con profesionales distintos (borde)
- **DADO** dos turnos `scheduled` el lunes a las 10:00, uno de la Dra. A y otro del Dr. B
- **CUANDO** se listan los turnos agendados del lunes
- **ENTONCES** se devuelven los dos, siempre en el mismo orden entre ejecuciones

#### Scenario: Rango inválido (borde)
- **DADO** un repositorio cualquiera
- **CUANDO** se listan turnos agendados con `desde` o `hasta` sin zona horaria, o con `desde` igual o posterior a `hasta`
- **ENTONCES** se lanza `ValueError`
