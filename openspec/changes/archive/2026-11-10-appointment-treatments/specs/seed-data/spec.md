# Spec Delta: seed-data

## MODIFIED Requirements

### Requirement: El seed carga los datos ficticios de demostración

Ejecutar el seed sobre una base con la migración aplicada y sin datos SHALL dejar: un usuario `admin`, un usuario `receptionist`, dos profesionales ficticios, cada uno con su usuario `dentist` y tramos de horario de lunes a viernes, la fila de configuración del consultorio (nombre, dirección y teléfono ficticios, slot de 30 minutos, zona tomada de `CLINIC_TIMEZONE`, recordatorio a las 9 y anticipación de 6 horas), 10 pacientes activos con emails del dominio `example.com` y exactamente 5 tratamientos activos de ejemplo (C-17, DD-151): "Consulta" (solo consulta, sin procedimiento), "Limpieza dental", "Extracción", "Arreglo de caries" y "Blanqueamiento". La Dra. Ana Alvarez MUST ofrecer los 5; el Dr. Bruno Benitez MUST ofrecer "Consulta", "Limpieza dental", "Extracción" y "Arreglo de caries", sin "Blanqueamiento", para que la demo muestre que el selector filtra por profesional. El seed MUST NOT crear turnos ni notificaciones. Los tramos cargados MUST cumplir las reglas de `schedule-validation` (sin superposición, inicio anterior al fin, sin segundos), y los nombres de los tratamientos, las reglas de `treatment-management`.

#### Scenario: Seed sobre una base vacía (esperado)
- **DADO** una base con la migración aplicada y sin datos
- **CUANDO** se ejecuta el seed
- **ENTONCES** hay 1 administrador, 1 recepcionista, 2 profesionales con su usuario odontólogo, 1 fila de configuración, 10 pacientes y 5 tratamientos activos ("Consulta", "Limpieza dental", "Extracción", "Arreglo de caries" y "Blanqueamiento")
- **Y** cada profesional tiene tramos de lunes (0) a viernes (4) y ninguno en sábado ni domingo
- **Y** la Dra. Ana Alvarez ofrece los 5 y el Dr. Bruno Benitez ofrece 4, todos menos "Blanqueamiento"
- **Y** no hay turnos ni notificaciones

#### Scenario: Los tramos del seed son válidos para el dominio (esperado)
- **DADO** la base cargada con el seed
- **CUANDO** se leen los tramos de cada profesional y se validan con las reglas de horarios
- **ENTONCES** la validación los acepta

#### Scenario: Los profesionales del seed se ofrecen online (esperado)
- **DADO** la base cargada con el seed
- **CUANDO** se piden los profesionales de la reserva pública
- **ENTONCES** figuran los dos, porque tienen horario y tratamientos activos

#### Scenario: El selector filtra por profesional (borde)
- **DADO** la base cargada con el seed
- **CUANDO** se piden los tratamientos públicos de cada profesional
- **ENTONCES** la Dra. Ana Alvarez devuelve los 5 y el Dr. Bruno Benitez devuelve 4, sin "Blanqueamiento"

#### Scenario: La zona del consultorio sale de la configuración del entorno (borde)
- **DADO** `CLINIC_TIMEZONE=America/Argentina/Cordoba`
- **CUANDO** se ejecuta el seed sobre una base vacía
- **ENTONCES** la configuración del consultorio queda con la zona `America/Argentina/Cordoba`

### Requirement: El seed es idempotente

Ejecutar el seed más de una vez SHALL dejar exactamente los mismos datos que una sola ejecución: MUST NOT duplicar filas ni fallar. Una segunda ejecución MUST NOT pisar los cambios que se hicieron después sobre datos ya cargados (por ejemplo, la configuración, un paciente desactivado, un tratamiento desactivado o renombrado, o la asignación de tratamientos de un profesional) y MUST NOT cambiar las contraseñas de los usuarios existentes. Un tratamiento del seed se busca por su nombre normalizado; la asignación de tratamientos de un profesional se carga solo si ese profesional no tiene ninguna.

#### Scenario: Ejecutar el seed dos veces (esperado)
- **DADO** una base cargada con el seed
- **CUANDO** se ejecuta el seed otra vez
- **ENTONCES** termina sin error y la cantidad de filas de cada tabla es la misma

#### Scenario: Un cambio posterior se conserva (borde)
- **DADO** una base cargada con el seed en la que después se cambió el slot a 20 minutos, se desactivó un paciente, se desactivó "Blanqueamiento" y se le quitó "Extracción" al Dr. Bruno Benitez
- **CUANDO** se ejecuta el seed otra vez
- **ENTONCES** el slot sigue en 20 minutos, el paciente sigue inactivo, "Blanqueamiento" sigue inactivo y el Dr. Bruno Benitez sigue sin "Extracción"

#### Scenario: Seed sobre una base de una versión anterior (borde)
- **DADO** una base cargada con el seed antes de C-17 y migrada a `0005`
- **CUANDO** se ejecuta el seed
- **ENTONCES** se agregan los 5 tratamientos y la asignación de cada profesional, sin tocar usuarios, pacientes ni turnos

#### Scenario: Seed sin la migración aplicada (error)
- **DADO** una base sin las tablas del sistema
- **CUANDO** se ejecuta el seed
- **ENTONCES** termina con un error que indica aplicar antes la migración y no crea nada
