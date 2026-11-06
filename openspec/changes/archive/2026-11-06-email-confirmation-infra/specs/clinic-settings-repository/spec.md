# Spec Delta

## MODIFIED Requirements

### Requirement: Leer la configuración de agenda del consultorio

Leer la configuración SHALL devolver `slot_minutes`, `timezone` y `min_notice_hours` del consultorio y, desde C-11, también los datos del consultorio para los emails: `clinic_name`, `address`, `phone` (puede no tener) y `reminder_send_hour` (0 a 23). Una implementación sin datos cargados (en PostgreSQL: sin la fila de configuración) MUST devolver los valores por defecto del modelo de datos: 30 minutos, `America/Argentina/Buenos_Aires`, 6 horas y recordatorio a las 9 (DD-03, SU-01, DD-14), con nombre `Consultorio`, dirección vacía y sin teléfono. La batería de contrato MUST ejecutarse contra cada implementación registrada (la de memoria y la de PostgreSQL).

#### Scenario: Valores por defecto (esperado)
- **DADO** una configuración sin valores cargados
- **CUANDO** se lee la configuración
- **ENTONCES** se obtiene slot de 30 minutos, zona `America/Argentina/Buenos_Aires`, anticipación mínima de 6 horas, recordatorio a las 9, nombre `Consultorio`, dirección vacía y sin teléfono

#### Scenario: Valores configurados (esperado)
- **DADO** una configuración cargada con slot de 20 minutos y anticipación mínima de 12 horas
- **CUANDO** se lee la configuración
- **ENTONCES** se obtienen 20 minutos, 12 horas y la zona por defecto

#### Scenario: Datos del consultorio para los emails (esperado)
- **DADO** la fila de configuración con nombre "Consultorio Demo", dirección "Av. Siempre Viva 742", teléfono "011 4000-0000" y recordatorio a las 8
- **CUANDO** se lee la configuración con el repositorio de PostgreSQL
- **ENTONCES** se obtienen esos cuatro valores además de los de agenda

#### Scenario: Consultorio sin teléfono (borde)
- **DADO** la fila de configuración con `phone` nulo
- **CUANDO** se lee la configuración
- **ENTONCES** el teléfono viene vacío (sin valor), sin error

#### Scenario: La configuración leída cambia las franjas calculadas (borde)
- **DADO** una configuración con slot de 20 minutos y la Dra. A con tramo lunes 09:00–10:00
- **CUANDO** el slot y la zona leídos se pasan al cálculo de franjas del lunes 5 de octubre
- **ENTONCES** el tramo se divide en tres franjas `FREE` de 20 minutos (09:00, 09:20 y 09:40)

#### Scenario: PostgreSQL sin la fila de configuración (borde)
- **DADO** la base con la migración aplicada y sin fila de configuración
- **CUANDO** se lee la configuración con el repositorio de PostgreSQL
- **ENTONCES** se obtienen los valores por defecto, sin error y sin crear la fila
