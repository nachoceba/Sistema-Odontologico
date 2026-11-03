# clinic-settings-repository Specification

## Purpose
Definir el contrato de solo lectura para obtener la duración del slot, la zona horaria y la anticipación mínima del consultorio, de modo que los casos de uso pasen esos valores a las reglas de agenda en lugar de repetir los valores por defecto.

## Requirements

### Requirement: Leer la configuración de agenda del consultorio

Leer la configuración SHALL devolver `slot_minutes`, `timezone` y `min_notice_hours` del consultorio. Una implementación sin datos cargados (en PostgreSQL: sin la fila de configuración) MUST devolver los valores por defecto del modelo de datos: 30 minutos, `America/Argentina/Buenos_Aires` y 6 horas (DD-03, SU-01, DD-14). La batería de contrato MUST ejecutarse contra cada implementación registrada (la de memoria y la de PostgreSQL). Los datos del consultorio para los emails (nombre, dirección, teléfono, hora del recordatorio) no forman parte de este requisito (C-11/C-12).

#### Scenario: Valores por defecto (esperado)
- **DADO** una configuración sin valores cargados
- **CUANDO** se lee la configuración
- **ENTONCES** se obtiene slot de 30 minutos, zona `America/Argentina/Buenos_Aires` y anticipación mínima de 6 horas

#### Scenario: Valores configurados (esperado)
- **DADO** una configuración cargada con slot de 20 minutos y anticipación mínima de 12 horas
- **CUANDO** se lee la configuración
- **ENTONCES** se obtienen 20 minutos, 12 horas y la zona por defecto

#### Scenario: La configuración leída cambia las franjas calculadas (borde)
- **DADO** una configuración con slot de 20 minutos y la Dra. A con tramo lunes 09:00–10:00
- **CUANDO** el slot y la zona leídos se pasan al cálculo de franjas del lunes 5 de octubre
- **ENTONCES** el tramo se divide en tres franjas `FREE` de 20 minutos (09:00, 09:20 y 09:40)

#### Scenario: PostgreSQL sin la fila de configuración (borde)
- **DADO** la base con la migración aplicada y sin fila de configuración
- **CUANDO** se lee la configuración con el repositorio de PostgreSQL
- **ENTONCES** se obtienen los valores por defecto, sin error y sin crear la fila
