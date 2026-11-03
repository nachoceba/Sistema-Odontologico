# quality-checks Specification

## Purpose
Definir los chequeos automáticos que todo change debe pasar antes de cerrarse (tests, lint, formato y tipos, en backend y frontend), cumpliendo la regla dura 9 y la exigencia de type hints y TypeScript sin `any` (regla dura 1).

## Requirements

### Requirement: Chequeos del backend en verde

El backend SHALL tener tres chequeos ejecutables con un comando cada uno: tests (pytest), lint y formato (ruff), y tipos en modo estricto (mypy `--strict`) sobre el código de la aplicación y sobre los tests. Sobre el código de este change los tres MUST terminar sin errores. Las únicas excepciones de lint MUST estar declaradas en la configuración con su justificación.

#### Scenario: Lint sin avisos (esperado)
- **WHEN** se corre el lint del backend
- **THEN** termina sin avisos, incluido el código de dominio previo

#### Scenario: Tipos estrictos sin errores en app y tests
- **WHEN** se corre el chequeo de tipos estricto sobre `app` y `tests`
- **THEN** termina sin errores

#### Scenario: Excepción justificada por DD-18 (borde)
- **WHEN** una función de dominio valida el tipo de su entrada y lanza `ValueError` (convención DD-18)
- **THEN** el lint no lo marca, porque la regla que pide `TypeError` está desactivada con una justificación que cita DD-18 en la configuración

#### Scenario: Función sin anotar (error)
- **WHEN** se agrega una función sin anotaciones de tipo en `app` o en `tests`
- **THEN** el chequeo de tipos falla señalando esa función

#### Scenario: Tests existentes conservados
- **WHEN** se corre la batería del backend después del cambio
- **THEN** pasan los 199 tests previos más los nuevos de este change

### Requirement: Chequeos del frontend en verde

El frontend SHALL tener tres chequeos ejecutables con un comando cada uno: tests (Vitest), chequeo de tipos de TypeScript en modo estricto y lint. El lint MUST tratar el uso de `any` explícito como error.

#### Scenario: Frontend en verde (esperado)
- **WHEN** se corren los tests, el chequeo de tipos y el lint del frontend
- **THEN** los tres terminan sin errores

#### Scenario: Uso de `any` (error)
- **WHEN** se agrega `const x: any = 1` en el código del frontend
- **THEN** el lint falla señalando esa línea

#### Scenario: Error de tipos (error)
- **WHEN** se asigna un número a una variable declarada como `string` en el frontend
- **THEN** el chequeo de tipos falla
