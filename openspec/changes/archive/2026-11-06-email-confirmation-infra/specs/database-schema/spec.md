# Spec Delta

## ADDED Requirements

### Requirement: Antigüedad de cada notificación (P-3)

Una migración posterior a la inicial SHALL agregar a `email_notifications` la columna `created_at` (`timestamptz`, NOT NULL, con el instante de la inserción como valor por defecto) y un índice que permita buscar las `pending` por antigüedad. Al aplicarla sobre una base con filas, las filas existentes MUST quedar con el instante de la migración. Revertirla MUST quitar la columna y el índice sin tocar las demás columnas ni filas. Aplicar, revertir y volver a aplicar MUST funcionar sin errores, y el esquema MUST seguir coincidiendo con los modelos de la aplicación.

#### Scenario: Aplicar sobre una base con notificaciones (esperado)
- **DADO** una base con la migración inicial y dos notificaciones `pending` registradas en C-08
- **CUANDO** se aplica la migración hasta la última versión
- **ENTONCES** las dos filas conservan todos sus datos y tienen `created_at` con el instante de la migración

#### Scenario: Valor por defecto al insertar (esperado)
- **DADO** la migración aplicada
- **CUANDO** se inserta una notificación sin indicar `created_at`
- **ENTONCES** queda con el instante de la inserción

#### Scenario: Revertir y volver a aplicar (borde)
- **DADO** la base con la última migración aplicada
- **CUANDO** se revierte un paso y se vuelve a aplicar
- **ENTONCES** al revertir `email_notifications` no tiene `created_at` y conserva sus filas, y al volver a aplicar el esquema queda igual que antes

#### Scenario: Modelos y migración coinciden (esperado)
- **DADO** una base con todas las migraciones aplicadas
- **CUANDO** se comparan las tablas, columnas, tipos, índices y constraints de la base con los modelos de la aplicación
- **ENTONCES** no hay diferencias
