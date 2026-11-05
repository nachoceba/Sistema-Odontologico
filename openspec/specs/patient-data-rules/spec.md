# patient-data-rules Specification

## Purpose
Reglas puras (sin base de datos ni framework) para normalizar y validar los datos de un paciente antes de guardarlos, de modo que el documento sea único sin importar cómo se escriba (RN-PA-01) y el email del recordatorio sea siempre válido (RN-PA-02).

## Requirements

### Requirement: Normalizar el número de documento (RN-PA-01, P-1 confirmada)

El sistema SHALL normalizar el documento quitando espacios, puntos y guiones y pasando las letras a mayúsculas. El documento normalizado MUST tener entre 6 y 20 caracteres y MUST contener solo letras A-Z y dígitos; si no, MUST rechazarse como inválido. Dos documentos que normalizados son iguales MUST considerarse el mismo documento. La regla MUST ser una función pura de la capa de dominio, usada tanto al guardar como al buscar.

#### Scenario: Documento con puntos (esperado)
- **WHEN** se normaliza `30.111.222`
- **THEN** el resultado es `30111222`

#### Scenario: Pasaporte con letras y espacios (esperado)
- **WHEN** se normaliza ` aa 123-456 `
- **THEN** el resultado es `AA123456`

#### Scenario: Muy corto tras normalizar (error de negocio)
- **WHEN** se normaliza `12.345`
- **THEN** se rechaza como documento inválido (5 caracteres)

#### Scenario: Carácter no permitido (error de negocio)
- **WHEN** se normaliza `30111222/1`
- **THEN** se rechaza como documento inválido

#### Scenario: Largo máximo (borde)
- **WHEN** se normalizan un documento de 20 caracteres válidos y otro de 21
- **THEN** el primero se acepta y el segundo se rechaza

### Requirement: Nombre, apellido y email obligatorios (US-003, RN-PA-02, P-2 confirmada)

Nombre y apellido SHALL guardarse recortados y MUST tener entre 1 y 100 caracteres tras recortar. El email SHALL guardarse recortado y en minúsculas y MUST cumplir la misma regla de formato que el email de las cuentas (3 a 254 caracteres, un único `@`, sin espacios, texto a ambos lados). El email MUST NOT ser único: dos pacientes pueden compartirlo (por ejemplo, una familia).

#### Scenario: Datos válidos (esperado)
- **WHEN** se validan nombre ` Juan `, apellido `Pérez` y email ` Juan.Perez@Example.com `
- **THEN** se aceptan como `Juan`, `Pérez` y `juan.perez@example.com`

#### Scenario: Apellido en blanco (error de negocio)
- **WHEN** se valida un apellido formado solo por espacios
- **THEN** se rechaza

#### Scenario: Email sin arroba (error de negocio)
- **WHEN** se valida el email `juan.example.com`
- **THEN** se rechaza

#### Scenario: Nombre de 101 caracteres (borde)
- **WHEN** se validan nombres de 100 y de 101 caracteres
- **THEN** el de 100 se acepta y el de 101 se rechaza

### Requirement: Teléfono y fecha de nacimiento opcionales (P-2 confirmada)

El teléfono SHALL ser opcional; si se informa, MUST guardarse recortado, MUST tener como máximo 30 caracteres, MUST contener solo dígitos, espacios, `+`, `-` y paréntesis, y MUST incluir al menos 6 dígitos. Un teléfono en blanco MUST tratarse como "sin teléfono". La fecha de nacimiento SHALL ser opcional; si se informa, MUST NOT ser posterior al día de hoy en la zona del consultorio y MUST NOT ser anterior al 1900-01-01.

#### Scenario: Teléfono con formato local (esperado)
- **WHEN** se valida el teléfono `011-5550-0001`
- **THEN** se acepta tal cual

#### Scenario: Teléfono con letras (error de negocio)
- **WHEN** se valida el teléfono `llamar tarde`
- **THEN** se rechaza

#### Scenario: Teléfono en blanco (borde)
- **WHEN** se valida un teléfono formado solo por espacios
- **THEN** el resultado es "sin teléfono", sin error

#### Scenario: Fecha de nacimiento futura (error de negocio)
- **WHEN** hoy es 2026-11-04 en la zona del consultorio y se valida la fecha 2026-11-05
- **THEN** se rechaza como dato del paciente inválido

#### Scenario: Nacido hoy (borde)
- **WHEN** hoy es 2026-11-04 en la zona del consultorio y se valida la fecha 2026-11-04
- **THEN** se acepta

#### Scenario: Cambio de día por zona horaria (borde)
- **WHEN** el reloj marca 2026-11-05T01:00Z (22:00 del 2026-11-04 en Buenos Aires) y se valida la fecha 2026-11-05
- **THEN** se rechaza, porque en el consultorio todavía es 2026-11-04

#### Scenario: Fecha anterior a 1900 (borde)
- **WHEN** se valida la fecha 1899-12-31
- **THEN** se rechaza
