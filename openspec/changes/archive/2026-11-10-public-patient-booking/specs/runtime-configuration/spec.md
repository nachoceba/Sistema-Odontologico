# Spec Delta: runtime-configuration

## ADDED Requirements

### Requirement: Configuración de las reservas online (DD-132)

Los procesos del backend SHALL leer dos variables opcionales nuevas:

- `ONLINE_BOOKING_HOLD_MINUTES`: entero entre 5 y 1440; por defecto 60.
- `PUBLIC_APP_URL`: origen del frontend para armar el enlace del email; por defecto `http://localhost:5173`. Debe tener esquema `http://` o `https://` y no puede terminar en `/`.

Un valor inválido MUST impedir el arranque nombrando la variable. Las dos MUST figurar en `.env.example` con su valor por defecto y su descripción. Ninguna es sensible y ninguna llega al frontend como `VITE_`.

#### Scenario: Valores por defecto (esperado)
- **WHEN** el proceso arranca sin las dos variables
- **THEN** la configuración expone `ONLINE_BOOKING_HOLD_MINUTES = 60` y `PUBLIC_APP_URL = http://localhost:5173`

#### Scenario: Plazo fuera de rango (error)
- **WHEN** `ONLINE_BOOKING_HOLD_MINUTES = 0`
- **THEN** el proceso no arranca y el error menciona `ONLINE_BOOKING_HOLD_MINUTES`

#### Scenario: URL con barra final (borde)
- **WHEN** `PUBLIC_APP_URL = http://localhost:8080/`
- **THEN** el proceso no arranca y el error menciona `PUBLIC_APP_URL`
