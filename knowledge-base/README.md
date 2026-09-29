# Sistema Odontológico — Base de Conocimiento

Base de conocimiento generada a partir del Discovery y de la sesión interactiva de definición del proyecto.

## Índice de Archivos

| Archivo | Contenido |
|---------|-----------|
| [01_vision_y_objetivos.md](01_vision_y_objetivos.md) | Propósito, objetivos por actor, alcance y fuera de alcance de v1 |
| [02_descripcion_general.md](02_descripcion_general.md) | Stack (Next.js + Supabase + Resend), arquitectura general e integraciones |
| [03_actores_y_roles.md](03_actores_y_roles.md) | Actores, matriz RBAC y rutas públicas |
| [04_modelo_de_datos.md](04_modelo_de_datos.md) | Entidades, ERD, constraints y seed data |
| [05_reglas_de_negocio.md](05_reglas_de_negocio.md) | Reglas RN-XX por dominio |
| [06_funcionalidades.md](06_funcionalidades.md) | Épicas e historias de usuario |
| [07_flujos_principales.md](07_flujos_principales.md) | Flujos extremo a extremo |
| [08_arquitectura_propuesta.md](08_arquitectura_propuesta.md) | Capas, estructura de directorios, seguridad y variables de entorno |
| [09_decisiones_y_supuestos.md](09_decisiones_y_supuestos.md) | Decisiones DD y supuestos SU |
| [10_preguntas_abiertas.md](10_preguntas_abiertas.md) | Inconsistencias y preguntas priorizadas |
| [11_recordatorios_email.md](11_recordatorios_email.md) | Extra: emails de confirmación y recordatorio |

## Quick Start para Desarrolladores

1. Entender el dominio → [01](01_vision_y_objetivos.md), [03](03_actores_y_roles.md)
2. Entender los datos → [04](04_modelo_de_datos.md)
3. Entender las reglas → [05](05_reglas_de_negocio.md)
4. Entender la arquitectura → [02](02_descripcion_general.md), [08](08_arquitectura_propuesta.md)
5. Implementar → [07](07_flujos_principales.md), [06](06_funcionalidades.md), [11](11_recordatorios_email.md)
6. Antes de codificar → [10](10_preguntas_abiertas.md)

## Resumen Ejecutivo

Aplicación web para gestionar los turnos de un consultorio odontológico: agenda por profesional sin superposiciones (garantizada por la base de datos), ABM de pacientes, login con roles y emails de confirmación y recordatorio. Se construye con Next.js, Supabase y Resend en planes gratuitos, con datos ficticios y prioridad en la mantenibilidad. Antes de programar hay que resolver los puntos de alta prioridad de `10_preguntas_abiertas.md`, sobre todo los límites de Resend y del cron gratuito.
