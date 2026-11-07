# Spec Delta

## ADDED Requirements

### Requirement: Matriz única de permisos por ruta y rol (R-6)

El proyecto SHALL tener una única matriz de permisos que declara, para cada ruta de la API (método y ruta con prefijo), qué roles (`admin`, `receptionist`, `dentist`) la pueden usar, de acuerdo con `03_actores_y_roles.md`; las dos rutas públicas (`POST /api/v1/auth/login` y `GET /api/v1/health`) figuran como públicas. El conjunto de rutas de la matriz MUST ser exactamente el conjunto de rutas registradas en la app. Un test automático MUST recorrer cada ruta protegida de la matriz y comprobar que: sin token responde 401 con `error.code = "NOT_AUTHENTICATED"`; con el token de cada rol no permitido responde 403 con `error.code = "FORBIDDEN"`; con el token de cada rol permitido no responde 401 ni 403 por falta de rol. El alcance "propio" del odontólogo (RN-AU-04) sigue probado en sus tests por recurso y no cambia.

#### Scenario: Matriz igual al inventario (esperado)
- **WHEN** se comparan las rutas de la matriz con las rutas registradas en la app
- **THEN** son exactamente las mismas, con las dos públicas marcadas como públicas

#### Scenario: Ruta nueva sin fila en la matriz (error)
- **WHEN** se registra en la app una ruta protegida que no figura en la matriz
- **THEN** el test de la matriz falla nombrando esa ruta

#### Scenario: Fila de una ruta que ya no existe (error)
- **WHEN** la matriz declara una ruta que la app no registra
- **THEN** el test de la matriz falla nombrando esa fila

#### Scenario: Rol no permitido por la matriz (error de negocio)
- **WHEN** la recepcionista pide `POST /api/v1/users` con su token
- **THEN** la respuesta es 403 con `error.code = "FORBIDDEN"`

#### Scenario: Odontólogo en una ruta de escritura de turnos (error de negocio)
- **WHEN** un odontólogo pide `POST /api/v1/appointments` con su token
- **THEN** la respuesta es 403 con `error.code = "FORBIDDEN"`

#### Scenario: Roles permitidos pasan el chequeo de rol (esperado)
- **WHEN** el administrador y la recepcionista piden `GET /api/v1/patients?q=ruiz` con su token
- **THEN** ninguno recibe 401 ni 403

#### Scenario: Sin token en todas las rutas protegidas (borde)
- **WHEN** se pide cada ruta protegida de la matriz sin encabezado `Authorization`
- **THEN** todas responden 401 con `error.code = "NOT_AUTHENTICATED"`, antes de cualquier chequeo de rol

#### Scenario: Rutas públicas fuera del chequeo de rol (borde)
- **WHEN** se piden `POST /api/v1/auth/login` y `GET /api/v1/health` sin token
- **THEN** ninguna responde 401 ni 403 por falta de sesión o de rol
