# seed-data Specification

## Purpose
Cargar en una base con el esquema aplicado un conjunto fijo de datos ficticios (usuarios, profesionales con horario, configuración del consultorio y pacientes) para desarrollar, probar y hacer la demo, sin datos reales ni secretos y sin duplicar nada si se vuelve a ejecutar.

## Requirements

### Requirement: El seed carga los datos ficticios de demostración

Ejecutar el seed sobre una base con la migración aplicada y sin datos SHALL dejar: un usuario `admin`, un usuario `receptionist`, dos profesionales ficticios, cada uno con su usuario `dentist` y tramos de horario de lunes a viernes, la fila de configuración del consultorio (nombre, dirección y teléfono ficticios, slot de 30 minutos, zona tomada de `CLINIC_TIMEZONE`, recordatorio a las 9 y anticipación de 6 horas) y 10 pacientes activos con emails del dominio `example.com`. El seed MUST NOT crear turnos ni notificaciones. Los tramos cargados MUST cumplir las reglas de `schedule-validation` (sin superposición, inicio anterior al fin, sin segundos).

#### Scenario: Seed sobre una base vacía (esperado)
- **DADO** una base con la migración aplicada y sin datos
- **CUANDO** se ejecuta el seed
- **ENTONCES** hay 1 administrador, 1 recepcionista, 2 profesionales con su usuario odontólogo, 1 fila de configuración y 10 pacientes
- **Y** cada profesional tiene tramos de lunes (0) a viernes (4) y ninguno en sábado ni domingo
- **Y** no hay turnos ni notificaciones

#### Scenario: Los tramos del seed son válidos para el dominio (esperado)
- **DADO** la base cargada con el seed
- **CUANDO** se leen los tramos de cada profesional y se validan con las reglas de horarios
- **ENTONCES** la validación los acepta

#### Scenario: La zona del consultorio sale de la configuración del entorno (borde)
- **DADO** `CLINIC_TIMEZONE=America/Argentina/Cordoba`
- **CUANDO** se ejecuta el seed sobre una base vacía
- **ENTONCES** la configuración del consultorio queda con la zona `America/Argentina/Cordoba`

### Requirement: El seed es idempotente

Ejecutar el seed más de una vez SHALL dejar exactamente los mismos datos que una sola ejecución: MUST NOT duplicar filas ni fallar. Una segunda ejecución MUST NOT pisar los cambios que se hicieron después sobre datos ya cargados (por ejemplo, la configuración o un paciente desactivado) y MUST NOT cambiar las contraseñas de los usuarios existentes.

#### Scenario: Ejecutar el seed dos veces (esperado)
- **DADO** una base cargada con el seed
- **CUANDO** se ejecuta el seed otra vez
- **ENTONCES** termina sin error y la cantidad de filas de cada tabla es la misma

#### Scenario: Un cambio posterior se conserva (borde)
- **DADO** una base cargada con el seed en la que después se cambió el slot a 20 minutos y se desactivó un paciente
- **CUANDO** se ejecuta el seed otra vez
- **ENTONCES** el slot sigue en 20 minutos y el paciente sigue inactivo

#### Scenario: Seed sin la migración aplicada (error)
- **DADO** una base sin las tablas del sistema
- **CUANDO** se ejecuta el seed
- **ENTONCES** termina con un error que indica aplicar antes la migración y no crea nada

### Requirement: El seed no contiene datos reales ni secretos (regla dura 5, R-10)

Las contraseñas de los usuarios del seed SHALL guardarse solo como hash, nunca en texto plano en la base. El código del seed MUST NOT contener contraseñas reales ni secretos; la contraseña de demostración MUST salir de una variable de entorno documentada en `.env.example` con un valor de ejemplo ficticio. Si esa variable falta, el seed MUST terminar con un error que la nombra, sin mostrar su valor, y sin crear usuarios. Los emails de usuarios y pacientes MUST usar el dominio `example.com`.

#### Scenario: Contraseña guardada como hash (esperado)
- **DADO** la base cargada con el seed
- **CUANDO** se lee el hash de contraseña del administrador
- **ENTONCES** no es igual a la contraseña de demostración y tiene el formato del algoritmo de hash elegido

#### Scenario: Falta la contraseña de demostración (error)
- **DADO** el entorno sin la variable de la contraseña de demostración
- **CUANDO** se ejecuta el seed
- **ENTONCES** termina con un error que nombra la variable, no crea usuarios y el mensaje no incluye ningún valor sensible

#### Scenario: Solo emails ficticios (borde)
- **DADO** la base cargada con el seed
- **CUANDO** se listan los emails de usuarios y pacientes
- **ENTONCES** todos terminan en `@example.com`
