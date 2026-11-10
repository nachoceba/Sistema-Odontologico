# access-control Specification

## Purpose
Garantizar que toda ruta de la API, salvo el login y el chequeo de salud, exija una sesión válida y el rol adecuado según la matriz RBAC, con la base de datos como fuente de verdad del estado y el rol de cada cuenta, ya que no existe una segunda barrera como RLS (DD-02).

## Requirements

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

### Requirement: La base es la fuente de verdad de la cuenta en cada request

En cada request protegido el sistema SHALL volver a leer la cuenta indicada en el token desde la base. Si la cuenta ya no existe, si tiene `active = false` o si su rol actual difiere del rol del token (P-8, CONFIRMADA (2026-11-03)), la respuesta MUST ser 401 con `error.code = "NOT_AUTHENTICATED"` aunque el token no haya vencido.

#### Scenario: Cuenta desactivada con token vigente (error de negocio, RN-AU-03)
- **WHEN** el administrador desactiva una cuenta y esa cuenta usa su token todavía vigente
- **THEN** la respuesta es 401 con `error.code = "NOT_AUTHENTICATED"`

#### Scenario: Rol cambiado con token vigente (borde)
- **WHEN** el rol de una cuenta cambia de `receptionist` a `dentist` y esa cuenta usa su token emitido antes del cambio
- **THEN** la respuesta es 401 con `error.code = "NOT_AUTHENTICATED"` y debe volver a iniciar sesión

#### Scenario: Cuenta borrada con token vigente (borde)
- **WHEN** el token es válido pero la cuenta que identifica ya no existe en la base
- **THEN** la respuesta es 401 con `error.code = "NOT_AUTHENTICATED"`

### Requirement: Chequeo de rol por ruta (RN-AU-02, matriz RBAC)

Cada ruta protegida SHALL declarar qué roles la pueden usar según la matriz de `03_actores_y_roles.md` (P-4, CONFIRMADA (2026-11-03)). Una cuenta autenticada cuyo rol no está entre los permitidos MUST recibir 403 con `error.code = "FORBIDDEN"` y un mensaje genérico que no revela datos del recurso. Toda ruta protegida MUST tener un test de permisos que pruebe cada uno de los tres roles y la falta de token.

#### Scenario: Rol permitido (esperado)
- **WHEN** el administrador pide una ruta restringida al rol `admin`
- **THEN** la ruta responde normalmente

#### Scenario: Rol no permitido (error de negocio)
- **WHEN** la recepcionista pide una ruta restringida al rol `admin`
- **THEN** la respuesta es 403 con `error.code = "FORBIDDEN"`

#### Scenario: Varios roles permitidos (borde)
- **WHEN** una ruta permite `admin` y `receptionist` y la piden el administrador, la recepcionista y un odontólogo
- **THEN** los dos primeros reciben respuesta normal y el odontólogo recibe 403

#### Scenario: Sin token en ruta con rol (borde)
- **WHEN** se pide sin token una ruta restringida al rol `admin`
- **THEN** la respuesta es 401 (no 403): primero se exige sesión y después rol

### Requirement: Un odontólogo solo accede a lo propio (RN-AU-04)

El sistema SHALL ofrecer una regla de alcance que decide si una cuenta puede leer los turnos u horarios de un profesional dado: el administrador y la recepción pueden con cualquier profesional; un odontólogo solo con el profesional asociado a su cuenta. Un odontólogo sin profesional asociado MUST NOT acceder a ningún profesional (P-12, CONFIRMADA (2026-11-03)). Cuando la regla niega el acceso, la ruta MUST responder 403 con `error.code = "FORBIDDEN"` (P-13, CONFIRMADA (2026-11-03)). Desde C-08, la regla MUST aplicarse en los endpoints reales de turnos y franjas (`appointment-api`), tanto cuando el profesional llega en la ruta o en la consulta como cuando sale del turno pedido, y MUST probarse de punta a punta contra esos endpoints con los usuarios del seed (DD-53). Las rutas de horarios que aplican esta regla llegan en C-07.

#### Scenario: Odontólogo con su propio profesional (esperado)
- **WHEN** un odontólogo pide los turnos de su propio profesional
- **THEN** la regla permite el acceso

#### Scenario: Odontólogo con otro profesional (error de negocio)
- **WHEN** un odontólogo pide los turnos del otro profesional del seed
- **THEN** la regla niega el acceso y la ruta responde 403 con `error.code = "FORBIDDEN"`

#### Scenario: Recepción y administración con cualquier profesional (esperado)
- **WHEN** la recepcionista y el administrador piden los turnos de cualquiera de los dos profesionales
- **THEN** la regla permite el acceso a ambos

#### Scenario: Odontólogo sin ficha de profesional (borde)
- **WHEN** una cuenta con rol `dentist` que no tiene fila en `professionals` pide los turnos de cualquier profesional
- **THEN** la regla niega el acceso

#### Scenario: Identificador de profesional mal formado (borde)
- **WHEN** un odontólogo pide los turnos de un profesional con un identificador que no es un UUID válido
- **THEN** la regla niega el acceso sin error interno

#### Scenario: De punta a punta contra el endpoint real (esperado)
- **WHEN** la Dra. A del seed, con su token, pide `GET /api/v1/appointments/{id}` de un turno del Dr. B y `GET /api/v1/appointments?professional_id=<Dr. B>`
- **THEN** ambos pedidos responden 403 con `error.code = "FORBIDDEN"` y no devuelven ningún dato del turno

#### Scenario: El profesional sale del turno, no del pedido (borde)
- **WHEN** la Dra. A pide marcar atención de un turno del Dr. B usando el identificador del turno, sin mandar ningún profesional
- **THEN** la regla se aplica sobre el profesional del turno y la respuesta es 403

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
