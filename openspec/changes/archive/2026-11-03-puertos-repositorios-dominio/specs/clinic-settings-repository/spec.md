# Spec Delta

## Purpose

Definir el contrato de solo lectura para obtener la duración del slot, la zona horaria y la anticipación mínima del consultorio, de modo que los casos de uso pasen esos valores a las reglas de agenda en lugar de repetir los valores por defecto.

## ADDED Requirements

> Datos ficticios. Fuente de verdad en ejecución: la fila única de `clinic_settings` (`04_modelo_de_datos.md`). Este requisito depende de la pregunta de `design.md`.

### Requirement: Leer la configuración de agenda del consultorio

Leer la configuración SHALL devolver `slot_minutes`, `timezone` y `min_notice_hours` del consultorio. Una implementación sin datos cargados MUST devolver los valores por defecto del modelo de datos: 30 minutos, `America/Argentina/Buenos_Aires` y 6 horas (DD-03, SU-01, DD-14). La batería de contrato MUST poder ejecutarse sin cambios contra cada implementación registrada. Los datos del consultorio para los emails (nombre, dirección, teléfono, hora del recordatorio) no forman parte de este requisito (C-11/C-12).

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
