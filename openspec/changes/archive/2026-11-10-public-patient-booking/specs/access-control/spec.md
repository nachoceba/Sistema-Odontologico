# Spec Delta: access-control

## MODIFIED Requirements

### Requirement: Toda ruta no pública exige sesión (RN-AU-01)

Toda ruta de la API SHALL exigir un token de acceso válido en el encabezado `Authorization: Bearer <token>`, salvo `POST /api/v1/auth/login`, `GET /api/v1/health` y las cuatro rutas de turnos online bajo `/api/v1/public/` (`GET /api/v1/public/professionals`, `GET /api/v1/public/professionals/{professional_id}/slots`, `POST /api/v1/public/appointment-confirmations` y `POST /api/v1/public/appointments`, C-15), que se protegen con límite de pedidos y validación estricta según la spec `public-booking-api`. Sin encabezado, con un esquema distinto de `Bearer` o con un token inválido o vencido, la respuesta de una ruta protegida MUST ser 401 con `error.code = "NOT_AUTHENTICATED"`, el encabezado `WWW-Authenticate: Bearer` y el cuerpo uniforme de errores. Un test automático MUST recorrer todas las rutas registradas en la app y fallar si alguna ruta fuera de la lista de públicas no exige sesión. Ninguna ruta nueva bajo `/api/v1/public/` MUST quedar pública sin figurar en esa lista.

#### Scenario: Ruta protegida con token válido (esperado)
- **WHEN** una cuenta activa pide una ruta protegida con su token vigente
- **THEN** la ruta responde normalmente

#### Scenario: Sin encabezado de autorización (error)
- **WHEN** se pide una ruta protegida sin encabezado `Authorization`
- **THEN** la respuesta es 401 con `error.code = "NOT_AUTHENTICATED"` y `WWW-Authenticate: Bearer`

#### Scenario: Esquema distinto de Bearer (borde)
- **WHEN** se pide una ruta protegida con `Authorization: Basic ...`
- **THEN** la respuesta es 401 con `error.code = "NOT_AUTHENTICATED"`

#### Scenario: Token vencido (error de negocio)
- **WHEN** se pide una ruta protegida con un token vencido
- **THEN** la respuesta es 401 con `error.code = "NOT_AUTHENTICATED"`

#### Scenario: Rutas públicas siguen abiertas (borde)
- **WHEN** se piden `POST /api/v1/auth/login`, `GET /api/v1/health` y las cuatro rutas de `/api/v1/public/` sin token
- **THEN** ninguna responde 401 por falta de sesión

#### Scenario: Ruta nueva sin protección (error)
- **WHEN** se registra en la app una ruta que no exige sesión y no figura en la lista de públicas
- **THEN** el test de inventario de rutas falla nombrando esa ruta

#### Scenario: Las rutas internas de turnos siguen protegidas (borde)
- **WHEN** se pide `POST /api/v1/appointments` o `GET /api/v1/professionals/{professional_id}/slots` sin token
- **THEN** la respuesta es 401 con `error.code = "NOT_AUTHENTICATED"`

### Requirement: Matriz única de permisos por ruta y rol (R-6)

El proyecto SHALL tener una única matriz de permisos que declara, para cada ruta de la API (método y ruta con prefijo), qué roles (`admin`, `receptionist`, `dentist`) la pueden usar, de acuerdo con `03_actores_y_roles.md`; las seis rutas públicas (`POST /api/v1/auth/login`, `GET /api/v1/health` y las cuatro de `/api/v1/public/`) figuran como públicas. El conjunto de rutas de la matriz MUST ser exactamente el conjunto de rutas registradas en la app. Un test automático MUST recorrer cada ruta protegida de la matriz y comprobar que: sin token responde 401 con `error.code = "NOT_AUTHENTICATED"`; con el token de cada rol no permitido responde 403 con `error.code = "FORBIDDEN"`; con el token de cada rol permitido no responde 401 ni 403 por falta de rol. Para cada ruta pública el test MUST comprobar que sin token no responde 401 ni 403. El alcance "propio" del odontólogo (RN-AU-04) sigue probado en sus tests por recurso y no cambia.

#### Scenario: Matriz igual al inventario (esperado)
- **WHEN** se comparan las rutas de la matriz con las rutas registradas en la app
- **THEN** son exactamente las mismas, con las seis públicas marcadas como públicas

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
- **WHEN** se piden las seis rutas públicas sin token
- **THEN** ninguna responde 401 ni 403 por falta de sesión o de rol
