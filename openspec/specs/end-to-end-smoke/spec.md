# end-to-end-smoke Specification

## Purpose
Comprobar con un solo comando que el sistema levantado funciona de punta a punta para los tres roles: login, agenda, cancelación, reprogramación y emails de confirmación y recordatorio visibles en Mailpit, usando solo datos ficticios y sin servicios externos.

## Requirements

### Requirement: Smoke test del flujo principal contra el entorno levantado

El proyecto SHALL tener un smoke test que se ejecuta con un comando documentado contra el entorno levantado (desarrollo o demo), por HTTP contra la API y contra la API HTTP de Mailpit, y que no corre en la batería de tests por defecto ni en la de integración. Las contraseñas de las cuentas del seed MUST leerse de `SEED_DEMO_PASSWORD` del entorno del contenedor, nunca del código. El test MUST usar dos pacientes ficticios propios, creados por el mismo test con email del dominio `example.com`, y al terminar MUST dejarlos desactivados y con sus turnos `scheduled` cancelados. Los pasos, en orden, son:

1. Login de las cuentas `admin`, `receptionist` y `dentist` del seed: cada una recibe un token y `GET /api/v1/auth/me` devuelve su rol.
2. La recepcionista agenda el turno A en una franja libre de mañana (zona del consultorio) y la API responde 201; un segundo intento en la misma franja y con el mismo profesional, para el otro paciente del test, responde 409 con `SLOT_TAKEN` (regla dura 6); el odontólogo que intenta agendar recibe 403.
3. La confirmación del turno A aparece en Mailpit.
4. La recepcionista cancela el turno A con un motivo y la franja vuelve a figurar libre.
5. La recepcionista agenda el turno B y lo reprograma a otra franja libre de mañana; la confirmación del nuevo horario aparece en Mailpit.
6. Se ejecuta la pasada de recordatorios forzada (DD-101) y aparece en Mailpit un recordatorio con el horario nuevo del turno B y ninguno para el turno A ni para el horario anterior de B; una segunda pasada forzada no agrega mensajes.

Si mañana no hay franjas porque ningún profesional atiende ese día, el test MUST asegurarse un horario de atención para mañana sin tocar los datos del seed más allá de lo necesario y restaurarlo al terminar.

#### Scenario: Flujo completo (esperado)
- **WHEN** el entorno está levantado con el seed y se ejecuta el comando documentado del smoke test
- **THEN** los seis pasos pasan en orden y el comando termina con código 0

#### Scenario: Login por rol (esperado)
- **WHEN** el smoke test inicia sesión con las tres cuentas del seed
- **THEN** `GET /api/v1/auth/me` devuelve `admin`, `receptionist` y `dentist` respectivamente

#### Scenario: Franja ocupada (error de negocio)
- **WHEN** después de agendar el turno A se intenta agendar en la misma franja del mismo profesional un turno para el otro paciente del test
- **THEN** la respuesta es 409 con `error.code = "SLOT_TAKEN"`

#### Scenario: Cancelado sin recordatorio (borde)
- **WHEN** se ejecuta la pasada de recordatorios forzada con el turno A cancelado y el turno B reprogramado
- **THEN** Mailpit tiene un solo recordatorio nuevo, el del turno B con su horario nuevo

#### Scenario: Pasada repetida (borde)
- **WHEN** se ejecuta una segunda pasada forzada
- **THEN** la cantidad de recordatorios en Mailpit para los pacientes del test no cambia

#### Scenario: Entorno no levantado (error)
- **WHEN** se ejecuta el smoke test sin la API o sin Mailpit disponibles
- **THEN** falla en el primer paso con un mensaje que nombra el servicio que no responde

#### Scenario: Sin contraseña del seed (error)
- **WHEN** `SEED_DEMO_PASSWORD` no está definida en el entorno donde corre el smoke test
- **THEN** falla antes de cualquier pedido con un mensaje que nombra `SEED_DEMO_PASSWORD`

#### Scenario: Mañana sin horario de atención (borde)
- **WHEN** el smoke test corre un viernes o sábado y el seed no tiene tramos para el día siguiente
- **THEN** el test se asegura un horario de atención de mañana para un profesional, completa los seis pasos y al terminar ese profesional vuelve a tener exactamente los tramos que tenía

#### Scenario: Datos que deja el test (borde)
- **WHEN** el smoke test terminó, bien o con una falla en un paso
- **THEN** sus pacientes quedan desactivados, sus turnos `scheduled` quedan cancelados y los datos del seed no cambiaron

#### Scenario: Redirección de emails activa (borde)
- **WHEN** el `.env` local tiene `EMAIL_REDIRECT_TO` con una dirección
- **THEN** el smoke test busca los emails en esa dirección y los identifica por el asunto y el horario del turno
