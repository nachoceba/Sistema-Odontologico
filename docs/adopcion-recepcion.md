# Checklist de adopción para la recepción

Documento para la recepción y el dueño del consultorio (no para quien levanta el entorno: eso está en el [README](../README.md)). Cubre el riesgo R-8 de `CHANGES.md`: que la recepción siga usando la planilla y WhatsApp aunque el sistema funcione. La decisión de dejar la planilla es del dueño; este documento solo ordena cómo probarlo.

> Hoy el sistema corre en una sola computadora, con pacientes y emails ficticios (los mensajes llegan a una bandeja de prueba y no salen del equipo). Para trabajar con pacientes reales hacen falta antes un servidor de email de verdad y una revisión legal (ver "Preguntas abiertas").

## 1. Preparación (antes del primer día)

- [ ] Quien levanta el sistema siguió el README y el smoke test (`docker compose exec api pytest -m smoke`) terminó bien.
- [ ] El administrador creó una cuenta por persona (recepción, cada odontólogo) con su rol; nadie comparte cuenta ni contraseña.
- [ ] Los horarios de atención de cada profesional y sus licencias están cargados y coinciden con la agenda real (solo el administrador los edita).
- [ ] La duración del turno y la hora de los recordatorios (por defecto, 30 minutos y las 9:00) fueron revisadas con el dueño.
- [ ] Se probó el email: se agendó un turno de prueba y la confirmación apareció en la bandeja de prueba (http://localhost:8025).
- [ ] Cada recepcionista hizo en la pantalla, con un paciente de prueba: buscar un paciente, crear uno nuevo, agendar, cancelar con motivo y reprogramar un turno.
- [ ] Se acordó quién es la persona de contacto ante un problema (ver sección 4).

## 2. Primera semana en paralelo con la planilla

- Cada turno nuevo se carga en el sistema **y** en la planilla de siempre. Al final de cada día, la recepcionista compara los dos y anota las diferencias (turnos que faltan, horarios distintos, pacientes que no se encontraron).
- Los turnos que llegan por WhatsApp se cargan igual en el sistema; las respuestas al paciente siguen yendo por WhatsApp (el sistema no confirma ni cancela por el paciente).
- Cualquier cosa que cueste o confunda se anota con fecha y pantalla; esas notas son la lista de mejoras para el dueño.
- El sistema **no** reemplaza la revisión humana de la agenda del día: antes de abrir el consultorio se mira la pantalla de agenda de cada profesional.

## 3. Criterios para dejar la planilla

Salen de las métricas de éxito de `knowledge-base/01_vision_y_objetivos.md`. Se puede dejar la planilla cuando, durante al menos una semana completa, se cumplió todo esto:

- [ ] Cero turnos superpuestos para un mismo profesional (el sistema los rechaza solo; si la planilla mostraba uno, se resolvió a mano).
- [ ] La recepcionista agenda un turno en menos de 1 minuto.
- [ ] Los recordatorios salieron para todos los turnos activos del día siguiente (en esta etapa, se comprobó en la bandeja de prueba).
- [ ] No hubo diferencias sin explicar entre el sistema y la planilla.
- [ ] La recepción dejó de usar la planilla y WhatsApp para agendar, y el dueño lo confirmó.

Si algún punto falla, se sigue en paralelo otra semana y se anota la causa.

## 4. Si algo no funciona

| Qué pasa | Qué hacer |
|---|---|
| La pantalla de ingreso dice "API no disponible" | Avisar a quien administra el equipo. Mientras tanto, agendar en la planilla y cargar los turnos en el sistema cuando vuelva. Quien administra revisa `docker compose ps` y `docker compose logs api` y, si hace falta, ejecuta `docker compose up` otra vez |
| No se puede iniciar sesión | Verificar el email y la contraseña; si se olvidó, el administrador la restablece desde la pantalla de usuarios |
| Un horario aparece ocupado o fuera de horario | Es la regla de la agenda: elegir otro horario o pedir al administrador que revise los horarios del profesional |
| El paciente dice que no le llegó el email | En esta etapa los emails no salen del equipo; se ven en la bandeja de prueba. Con un servidor de email real, el turno igual queda guardado y el envío se reintenta solo |
| Dos personas agendaron el mismo horario | No puede pasar: la base de datos lo rechaza y la segunda persona ve un aviso de horario ocupado |

A quién avisar: la persona que administra el sistema y el dueño (completar nombres y teléfonos del consultorio en este punto antes del primer día).

## 5. Preguntas abiertas para el dueño

Resumen de `knowledge-base/10_preguntas_abiertas.md` y del README; ninguna bloquea la prueba en paralelo, pero las primeras bloquean el uso con pacientes reales.

1. **Servidor de email (SU-02)**: ¿qué servidor gratuito se usará para enviar los emails de verdad y qué cupo tiene? Hoy solo hay bandeja de prueba.
2. **Datos reales y revisión legal (R-10)**: antes de cargar pacientes reales hace falta una revisión legal (Ley 25.326); el sistema no declara cumplimiento.
3. **Sesión y login (DD-46, DD-47)**: ¿se necesita endurecer el ingreso (límite de intentos, sesión más estricta) antes de usar datos reales?
4. **Zona horaria (SU-01)**: confirmar que el consultorio usa `America/Argentina/Buenos_Aires`.
5. **Adopción**: ¿cómo se logra que la recepción abandone planilla y WhatsApp? Quién decide el momento y con qué criterio (sección 3).
6. **Agenda real**: ¿qué duración de turno usa el consultorio (15, 20 o 30 minutos)? ¿Hay sillones compartidos entre profesionales? ¿Se necesitan sobreturnos?
7. **Recordatorios por WhatsApp**: el sistema usa email porque WhatsApp tiene costo; ¿alcanza el email o se agrega un enlace manual?
