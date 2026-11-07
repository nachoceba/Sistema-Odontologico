# Arquitectura Propuesta

Prioridad de calidad definida: **mantenibilidad**. La arquitectura busca reglas de negocio aisladas y testeables, con la infraestructura reemplazable.

## Patrones aplicados

| Patrón | Dónde se usa | Por qué |
|---|---|---|
| Capas (domain / application / infrastructure) | Todo el código de negocio del backend | Aísla las reglas de FastAPI, SQLAlchemy y Celery |
| Funciones puras de dominio | Cálculo de slots, validación de superposición y horarios | Testeables con pytest sin base ni red |
| Repository | Acceso a PostgreSQL mediante SQLAlchemy | Permite tests con repositorios en memoria |
| Casos de uso (application services) | `agendar_turno`, `cancelar_turno`, `reprogramar_turno`, `enviar_recordatorios` | Un lugar por operación de negocio |
| Constraint de exclusión en BD | Tabla `appointments` | Garantiza la no superposición aun con concurrencia |
| Idempotencia por unique key | `email_notifications (appointment_id, kind, appointment_starts_at)` | La tarea puede reintentarse sin duplicar emails |
| Puerto y adaptador | `EmailSender`, `NotificationPort` | Permite cambiar el proveedor de email y probar con un falso |

## Estructura de directorios

```
sistema-odontologico/
├── backend/
│   ├── app/
│   │   ├── api/                # routers FastAPI, dependencias (auth, roles), esquemas Pydantic
│   │   ├── domain/             # reglas puras, sin imports de framework
│   │   │   ├── appointments/   # slots, superposición, validaciones
│   │   │   ├── schedules/      # working_hours, time_off
│   │   │   └── patients/
│   │   ├── application/        # casos de uso
│   │   ├── infrastructure/
│   │   │   ├── db/             # modelos SQLAlchemy, sesión y repositorios
│   │   │   ├── email/          # cliente SMTP y plantillas
│   │   │   └── tasks/          # app Celery, tareas y programación (beat)
│   │   └── core/               # configuración, seguridad (JWT, hash), zona horaria, errores
│   ├── alembic/                # migraciones versionadas
│   ├── scripts/seed.py         # datos ficticios
│   ├── tests/                  # unit (domain) + integración + smoke (extremo a extremo)
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/                    # páginas, componentes, cliente de API, hooks
│   ├── scripts/check-bundle.mjs  # chequeo de secretos en dist/ (corre en el build de la demo)
│   ├── nginx.conf              # modo demo: archivos estáticos con vuelta a index.html
│   ├── vite.config.ts
│   └── Dockerfile              # etapas dev (Vite), build y demo (nginx)
├── docker-compose.yml          # migrate (una vez), db, redis, api, worker, beat, frontend, mailpit
├── docker-compose.demo.yml     # modo demo: se suma al anterior (frontend nginx en el 8080, API sin recarga)
├── .env.example
├── docs/adopcion-recepcion.md  # checklist de adopción para la recepción
└── knowledge-base/
```

## Seguridad

- **Autenticación**: JWT de acceso con expiración corta, emitido en `POST /api/v1/auth/login`. Las contraseñas se guardan con un hash seguro (argon2 o bcrypt), nunca en texto plano.
- **Autorización**: chequeo de rol en cada endpoint mediante una dependencia de FastAPI (`require_role`) y en los casos de uso. No existe una segunda barrera como RLS: por eso cada endpoint debe tener un test de permisos por rol (riesgo R-6 de `CHANGES.md`). Una matriz única ruta × rol (`tests/unit/api/test_permission_matrix.py`, DD-110) debe ser igual al conjunto de rutas registradas y comprueba 401 sin token, 403 por rol no permitido y paso con cada rol permitido; una ruta nueva sin fila hace fallar el test.
- **Validación de input**: esquemas Pydantic en cada endpoint; las reglas de negocio se validan además en `domain/`.
- **CORS**: solo se permiten los orígenes de `CORS_ORIGINS` (explícitos, con `http://` o `https://`; un `*` hace fallar el arranque), solo los métodos `GET`, `POST`, `PUT`, `PATCH`, `DELETE` y `OPTIONS`, solo los encabezados `Authorization` y `Content-Type` y sin credenciales de navegador (DD-116).
- **Registro de accesos**: el registro de la API escribe método, ruta y código, sin la parte de consulta (`?q=…` de la búsqueda de pacientes; DD-77, DD-107).
- **Bundle del frontend**: el código solo lee `VITE_API_URL` de `import.meta.env` y el build de la imagen de la demo falla si `dist/` contiene el nombre o el patrón de un secreto (DD-111).
- **Sesión y login**: token en `sessionStorage` y sin límite de intentos; decisiones abiertas antes de usar datos reales (DD-46, DD-47, DD-112).
- **Secrets management**: variables de entorno; `JWT_SECRET_KEY`, `SMTP_PASSWORD` y las credenciales de base de datos solo en el servidor y fuera del repositorio (`.env` ignorado por git; se versiona solo `.env.example`).
- **Datos de pacientes**: ficticios; aun así se aplica mínimo privilegio (RN-PR-02).

## Variables de entorno

| Variable | Descripción | Ejemplo | Sensible |
|---|---|---|---|
| `DATABASE_URL` | Cadena de conexión a PostgreSQL | `postgresql+psycopg://user:pass@db:5432/odonto` | Y |
| `REDIS_URL` | Conexión a Redis (broker de Celery) | `redis://redis:6379/0` | N |
| `JWT_SECRET_KEY` | Clave para firmar los JWT | cadena aleatoria larga | Y |
| `JWT_ALGORITHM` | Algoritmo de firma | `HS256` | N |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Vida del token de acceso | `30` | N |
| `SMTP_HOST` / `SMTP_PORT` | Servidor SMTP (en desarrollo, Mailpit) | `mailpit` / `1025` | N |
| `SMTP_USER` / `SMTP_PASSWORD` | Credenciales SMTP (vacías en desarrollo) | — | Y |
| `SMTP_USE_TLS` | Usar STARTTLS | `false` (Mailpit) / `true` (producción) | N |
| `EMAIL_FROM` | Remitente de los emails | `turnos@ejemplo.com` | N |
| `EMAIL_REDIRECT_TO` | Opcional: si tiene una dirección, todos los emails van a ella en lugar de al paciente, con una línea de demostración (DD-87) | vacía | N |
| `CLINIC_TIMEZONE` | Valor inicial de la zona horaria (el seed la escribe en `clinic_settings`) y zona de la app Celery | `America/Argentina/Buenos_Aires` | N |
| `CORS_ORIGINS` | Orígenes permitidos del frontend, separados por comas, con esquema y sin `*`: 5173 (desarrollo) y 8080 (modo demo) | `http://localhost:5173,http://localhost:8080` | N |
| `SEED_DEMO_PASSWORD` | Contraseña de las cuentas de demostración del seed; vacía en `.env.example`, cada persona completa una propia en su `.env` local (DD-40, DD-113) | — | Y |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Credenciales del contenedor de PostgreSQL | — | Y |
| `VITE_API_URL` | URL pública de la API para el frontend | `http://localhost:8000/api/v1` | N |
