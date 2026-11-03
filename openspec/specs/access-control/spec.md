# access-control Specification

## Purpose
Garantizar que toda ruta de la API, salvo el login y el chequeo de salud, exija una sesión válida y el rol adecuado según la matriz RBAC, con la base de datos como fuente de verdad del estado y el rol de cada cuenta, ya que no existe una segunda barrera como RLS (DD-02).

## Requirements

### Requirement: Toda ruta no pública exige sesión (RN-AU-01)

Toda ruta de la API SHALL exigir un token de acceso válido en el encabezado `Authorization: Bearer <token>`, salvo `POST /api/v1/auth/login` y `GET /api/v1/health`. Sin encabezado, con un esquema distinto de `Bearer` o con un token inválido o vencido, la respuesta MUST ser 401 con `error.code = "NOT_AUTHENTICATED"`, el encabezado `WWW-Authenticate: Bearer` y el cuerpo uniforme de errores. Un test automático MUST recorrer todas las rutas registradas en la app y fallar si alguna ruta fuera de la lista de públicas no exige sesión.

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
- **WHEN** se piden `POST /api/v1/auth/login` y `GET /api/v1/health` sin token
- **THEN** ninguna responde 401 por falta de sesión

#### Scenario: Ruta nueva sin protección (error)
- **WHEN** se registra en la app una ruta que no exige sesión y no figura en la lista de públicas
- **THEN** el test de inventario de rutas falla nombrando esa ruta

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

El sistema SHALL ofrecer una regla de alcance que decide si una cuenta puede leer los turnos u horarios de un profesional dado: el administrador y la recepción pueden con cualquier profesional; un odontólogo solo con el profesional asociado a su cuenta. Un odontólogo sin profesional asociado MUST NOT acceder a ningún profesional (P-12, CONFIRMADA (2026-11-03)). Cuando la regla niega el acceso, la ruta MUST responder 403 con `error.code = "FORBIDDEN"` (P-13, CONFIRMADA (2026-11-03)). Las rutas de turnos y horarios que aplican esta regla llegan en C-07 y C-08; este change entrega la regla y su forma de uso en rutas.

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
