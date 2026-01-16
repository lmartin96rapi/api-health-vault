# Health Insurance API

Aplicación FastAPI para la gestión de formularios de reembolso de seguros de salud con autenticación Google SSO, API keys, sistema ACL (Access Control List), integraciones con APIs externas, carga de archivos y registro de auditoría completo.

## Características

### Framework y Base de Datos
- **FastAPI** con soporte asíncrono para endpoints de API de alto rendimiento
- **SQLAlchemy** ORM con soporte asíncrono para operaciones eficientes de base de datos
- **Alembic** para migraciones de base de datos y control de versiones
- Soporte para SQLite (desarrollo) y PostgreSQL (producción)

### Autenticación y Autorización
- **Google SSO** autenticación mediante OAuth2 para acceso de operadores
- **API Keys** para autenticación service-to-service
- **ACL (Access Control List)** con permisos a nivel de endpoint y recurso
- Control de acceso basado en roles con permisos configurables
- Modo superadmin con bypass de permisos

### Seguridad
- **Rate limiting** con límites configurables por endpoint
- Middleware de **protección CSRF**
- Validación de carga de archivos (tipos MIME, límites de tamaño)
- Enmascaramiento de datos sensibles en logs
- Middleware de headers de seguridad
- Límites de tamaño de solicitud

### Integraciones y Resiliencia
- **Integraciones con APIs externas** (Backend API, WspApi)
- Patrón **circuit breaker** para tolerancia a fallos de APIs externas
- Lógica de reintentos con backoff exponencial
- Manejo de timeouts de solicitudes

### Almacenamiento y Logging
- **Almacenamiento de archivos** (sistema de archivos local, preparado para migración a bucket)
- **Registro de auditoría completo** con seguimiento de acciones
- Logging estructurado con trazabilidad mediante request IDs
- Políticas de rotación y retención de logs

### Despliegue y Rendimiento
- Soporte **Docker** con múltiples entornos (desarrollo, staging, producción)
- **Multi-threaded** y optimizado para alto tráfico
- Configuración Gunicorn para producción
- Endpoints de health check

## Funcionalidades Principales

### Gestión de Formularios
- **Creación de formularios**: Generación de formularios con tokens únicos y seguros para identificación
- **Soporte de idempotencia**: Prevención de duplicados mediante header Idempotency-Key
- **Expiración configurable**: Los formularios tienen un tiempo de expiración configurable (por defecto 24 horas)
- **Envío de formularios**: Proceso de envío con documentos adjuntos (factura, receta médica, diagnósticos)
- **Consulta de estado**: Endpoints públicos para verificar el estado y detalles del formulario

### Gestión de Documentos
- **Subida de archivos**: 
  - Factura (requerida)
  - Receta médica (requerida)
  - Diagnósticos e indicaciones terapéuticas (opcionales, hasta 3 archivos)
- **Almacenamiento**: Sistema de archivos local organizado por estructura de directorios, preparado para migración futura a bucket de almacenamiento en la nube
- **Visualización y descarga**: Control de acceso mediante ACL, solo facturas son descargables, otros documentos son de solo visualización
- **Enlaces de acceso**: Tokens temporales con expiración configurable para acceso a envíos de formularios

### Autenticación y Autorización
- **Google SSO**: Autenticación mediante OAuth2 para operadores del sistema
- **API Keys**: Autenticación service-to-service para creación de formularios desde sistemas externos
- **ACL (Access Control List)**: 
  - Permisos a nivel de endpoint (acceso general a funcionalidades)
  - Permisos a nivel de recurso (acceso específico a recursos individuales)
- **Roles y permisos**: Sistema configurable de roles con permisos asociados
- **Modo superadmin**: Usuarios superadmin con bypass completo de verificaciones de permisos

### Integraciones Externas
- **Backend API**: Integración para creación de órdenes y envío de facturas al sistema backend
- **WspApi**: Integración con servicios externos adicionales
- **Circuit breaker**: Patrón de protección contra fallos en cascada en APIs externas
- **Lógica de reintentos**: Reintentos automáticos con backoff exponencial para mejorar la resiliencia

### Auditoría y Logging
- **Registro de acciones**: Todas las acciones del sistema son registradas (creación de formularios, envíos, accesos, descargas)
- **Logging estructurado**: Logs con formato estructurado y sanitización automática de datos sensibles
- **Rotación de logs**: Rotación automática de archivos de log con políticas de retención configurables
- **Trazabilidad**: Request IDs únicos para seguimiento completo de solicitudes a través del sistema

### Seguridad
- **Rate limiting**: Límites de velocidad configurables por endpoint para prevenir abuso
- **Protección CSRF**: Middleware de protección contra ataques Cross-Site Request Forgery
- **Validación de archivos**: Validación de tipos MIME permitidos y tamaño máximo de archivos
- **Sanitización de logs**: Enmascaramiento automático de datos sensibles en los logs del sistema

## Estructura del Proyecto

```
api-health-vault/
├── app/
│   ├── api/v1/endpoints/    # Endpoints REST de la API
│   │   ├── forms.py         # Gestión de formularios (crear, consultar, enviar)
│   │   ├── documents.py     # Gestión de documentos (visualizar, descargar)
│   │   ├── auth.py          # Autenticación (Google SSO, usuario actual)
│   │   └── audit.py         # Consulta de logs de auditoría
│   ├── core/                # Lógica central del sistema
│   │   ├── acl.py           # Sistema de permisos ACL
│   │   ├── api_key.py       # Validación de API keys
│   │   ├── security.py      # JWT, Google OAuth2
│   │   ├── circuit_breaker.py # Circuit breaker para APIs externas
│   │   ├── exceptions.py    # Excepciones personalizadas
│   │   └── logging_config.py # Configuración de logging
│   ├── models/              # Modelos SQLAlchemy (entidades de base de datos)
│   │   ├── form.py          # Form, FormSubmission
│   │   ├── document.py      # Document
│   │   ├── operator.py      # Operator (usuarios/operadores)
│   │   ├── api_key.py       # ApiKey
│   │   ├── acl.py           # Role, Permission, UserRole, ResourcePermission
│   │   └── audit_log.py     # AuditLog
│   ├── schemas/             # Schemas Pydantic para validación de datos
│   ├── services/            # Lógica de negocio y acceso a datos
│   │   ├── form_service.py  # Servicio de formularios
│   │   ├── document_service.py # Servicio de documentos
│   │   ├── operator_service.py # Servicio de operadores
│   │   ├── acl_service.py   # Servicio de ACL
│   │   └── audit_service.py # Servicio de auditoría
│   ├── external/            # Clientes de APIs externas
│   │   ├── backend_client.py # Cliente Backend API
│   │   └── wsp_api_client.py # Cliente WspApi
│   ├── middleware/          # Middlewares de FastAPI
│   │   ├── rate_limit.py    # Rate limiting
│   │   ├── csrf.py          # Protección CSRF
│   │   ├── security.py      # Headers de seguridad
│   │   └── logging_middleware.py # Logging de requests
│   ├── database.py          # Configuración y setup de base de datos
│   ├── config.py            # Configuración de la aplicación (Settings)
│   └── main.py              # Aplicación FastAPI principal
├── alembic/                 # Migraciones de base de datos
│   ├── versions/            # Archivos de migración
│   └── env.py               # Configuración de Alembic
├── tests/                   # Suite de tests
│   ├── conftest.py          # Fixtures de pytest
│   ├── test_forms.py        # Tests de formularios
│   ├── test_documents.py    # Tests de documentos
│   ├── test_api_key.py      # Tests de API keys
│   ├── test_security.py     # Tests de seguridad
│   └── test_endpoints.py    # Tests de integración de endpoints
├── docker/                  # Dockerfiles
│   ├── Dockerfile           # Dockerfile de producción
│   └── Dockerfile.dev       # Dockerfile de desarrollo
├── uploads/                 # Archivos subidos por usuarios
├── logs/                    # Logs de la aplicación
├── data/                    # Base de datos SQLite (desarrollo)
└── requirements.txt         # Dependencias del proyecto
```

## Configuración

### 1. Variables de Entorno

Copia el archivo `.env.example` a `.env` y configura las variables necesarias:

```bash
cp .env.example .env
```

**Variables críticas a configurar:**
- `SECRET_KEY`: Clave secreta para generación de tokens JWT (requerida)
- `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET`: Credenciales de Google OAuth2 (requeridas)
- `BACKEND_API_URL` y `BACKEND_API_KEY`: URL y clave de la API backend (requeridas)
- `WSP_API_URL`: URL de la API WspApi (requerida)
- `DATABASE_URL`: URL de conexión a la base de datos (SQLite para desarrollo, PostgreSQL para producción)
- `ENVIRONMENT`: Entorno de ejecución (development, staging, production)

### 2. Instalación de Dependencias

Instala las dependencias del proyecto:

```bash
pip install -r requirements.txt
```

Para desarrollo, también instala las dependencias de desarrollo:

```bash
pip install -r requirements-dev.txt
```

### 3. Migraciones de Base de Datos

Ejecuta las migraciones de Alembic para crear las tablas en la base de datos:

```bash
alembic upgrade head
```

Esto aplicará todas las migraciones pendientes y creará la estructura de base de datos necesaria.

**Nota**: Para testing, el proyecto utiliza una base de datos SQLite separada (`test_health_insurance.db`) que se crea y elimina automáticamente durante la ejecución de tests.

### 4. Ejecutar la Aplicación

**Desarrollo:**
```bash
uvicorn app.main:app --reload
```

El flag `--reload` permite recarga automática cuando se detectan cambios en el código.

**Producción (con Gunicorn):**
```bash
gunicorn app.main:app -c gunicorn_conf.py
```

Gunicorn proporciona múltiples workers para mejor rendimiento en producción. La configuración se encuentra en `gunicorn_conf.py`.

## Docker

El proyecto incluye configuración Docker para facilitar el despliegue en diferentes entornos. Se utilizan archivos docker-compose separados para desarrollo y producción.

### Desarrollo

Para ejecutar la aplicación en modo desarrollo con Docker:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

Este comando combina la configuración base (`docker-compose.yml`) con la configuración de desarrollo (`docker-compose.dev.yml`), que incluye:
- Recarga automática de código
- Volúmenes montados para desarrollo
- Configuraciones de logging más verbosas

### Producción

Para ejecutar la aplicación en modo producción:

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

El flag `-d` ejecuta los contenedores en modo detached (en segundo plano). La configuración de producción incluye:
- Optimizaciones de rendimiento
- Configuración de Gunicorn con múltiples workers
- Health checks configurados
- Políticas de reinicio automático

**Volúmenes montados:**
- `./logs:/app/logs` - Logs de la aplicación
- `./uploads:/app/uploads` - Archivos subidos por usuarios
- `./data:/app/data` - Base de datos SQLite (desarrollo)

**Health checks:**
El contenedor incluye un health check que verifica el endpoint `/health` cada 30 segundos.

## Endpoints de la API

### Formularios

- **POST /api/v1/forms** - Crear formulario
  - Requiere autenticación mediante API key
  - Soporta idempotencia mediante header `Idempotency-Key`
  - Retorna el token del formulario y URL de acceso
  - Establece fecha de expiración configurable

- **GET /api/v1/forms/{form_token}** - Obtener detalles del formulario
  - Endpoint público (no requiere autenticación)
  - Rate limited para prevenir enumeración de tokens
  - Retorna información del formulario (nombre, DNI, email, estado, fecha de expiración)

- **POST /api/v1/forms/{form_token}/submit** - Enviar formulario con documentos
  - Endpoint público (no requiere autenticación)
  - Requiere factura y receta médica (obligatorias)
  - Permite hasta 3 archivos de diagnóstico (opcionales)
  - Valida que el formulario no esté expirado o ya enviado
  - Retorna token de acceso para visualización posterior

- **GET /api/v1/forms/{form_token}/status** - Obtener estado del formulario
  - Endpoint público (no requiere autenticación)
  - Rate limited para prevenir enumeración de tokens
  - Retorna el estado actual del formulario (pending, submitted, expired)

### Documentos

- **GET /api/v1/document-access/{access_token}** - Ver envío completo
  - Requiere autenticación Google SSO
  - Requiere validación del access token
  - Requiere permisos ACL para visualizar documentos
  - Retorna información del envío y lista de documentos asociados

- **GET /api/v1/document-access/{access_token}/documents/{document_id}/invoice/download** - Descargar factura
  - Requiere autenticación Google SSO
  - Requiere validación del access token
  - Requiere permisos ACL para descargar documentos
  - Solo disponible para documentos de tipo factura
  - Retorna el archivo PDF de la factura

- **GET /api/v1/document-access/{access_token}/documents/{document_id}/view** - Ver documento
  - Requiere autenticación Google SSO
  - Requiere validación del access token
  - Requiere permisos ACL para visualizar documentos
  - Disponible para recetas y diagnósticos (no facturas)
  - Retorna el archivo en modo de solo lectura

### Autenticación

- **POST /api/v1/auth/google** - Autenticación Google SSO
  - Recibe token de Google OAuth2
  - Valida el token con Google
  - Crea o valida operador en el sistema
  - Retorna token JWT para autenticación posterior

- **GET /api/v1/auth/me** - Obtener usuario actual
  - Requiere autenticación JWT
  - Retorna información del operador autenticado (ID, email, nombre, estado)

- **POST /api/v1/auth/test-superadmin** - Login de prueba superadmin
  - Solo disponible en entornos development y test
  - Crea o autentica un usuario superadmin de prueba
  - Bypassa autenticación Google SSO para testing
  - Retorna token JWT con permisos de superadmin

### Auditoría

- **GET /api/v1/audit-logs** - Consultar logs de auditoría
  - Requiere autenticación Google SSO
  - Requiere permisos ACL para visualizar logs de auditoría
  - Soporta filtros por tipo de acción, usuario, recurso, fechas
  - Retorna lista paginada de logs de auditoría

## Testing

### Configuración

Para ejecutar los tests, es necesario configurar las variables de entorno apropiadas. El proyecto utiliza una base de datos SQLite separada para testing (`test_health_insurance.db`) que se crea y elimina automáticamente durante la ejecución de tests.

**Variables de entorno importantes para testing:**
- `ENVIRONMENT=test` o `ENVIRONMENT=development` - Entorno de ejecución
- `SECRET_KEY` - Clave secreta para JWT (puede ser un valor de prueba)
- `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET` - Pueden ser valores de prueba para testing
- `BACKEND_API_URL` y `BACKEND_API_KEY` - Pueden ser mocks o valores de prueba
- `WSP_API_URL` - Puede ser un mock para testing

### Ejecución

Los tests se ejecutan utilizando pytest. El proyecto incluye pytest-asyncio para soporte de tests asíncronos.

**Comandos principales:**
- Ejecutar todos los tests: `pytest`
- Ejecutar con salida verbose: `pytest -v`
- Ejecutar tests específicos: `pytest tests/test_forms.py`
- Ejecutar con coverage: `pytest --cov=app --cov-report=html`
- Ejecutar tests asíncronos: `pytest -v --asyncio-mode=auto`

### Estructura de Tests

Los tests están organizados por funcionalidad en el directorio `tests/`:
- `test_forms.py` - Tests de creación, validación y envío de formularios
- `test_documents.py` - Tests de subida, descarga y visualización de documentos
- `test_api_key.py` - Tests de validación de API keys
- `test_security.py` - Tests de autenticación y autorización
- `test_endpoints.py` - Tests de integración de endpoints

### Fixtures Disponibles

El archivo `conftest.py` proporciona fixtures reutilizables para los tests:
- `db_session` - Sesión de base de datos de prueba que se crea y limpia automáticamente
- `client` - Cliente HTTP de FastAPI para realizar requests de prueba
- `event_loop` - Loop de asyncio para ejecutar tests asíncronos

### Tipos de Tests

El proyecto incluye diferentes tipos de tests:
- **Tests unitarios**: Prueban servicios y modelos de forma aislada
- **Tests de integración**: Prueban endpoints completos con todas sus dependencias
- **Tests asíncronos**: Utilizan pytest-asyncio para probar operaciones asíncronas

### Testing con Docker

Para ejecutar tests dentro de un contenedor Docker, se puede usar el comando:

```bash
docker-compose exec api pytest
```

Esto ejecuta los tests en el contenedor de la aplicación con todas las dependencias ya instaladas.

### Coverage

Para generar reportes de cobertura de código, se utiliza el comando:

```bash
pytest --cov=app --cov-report=html
```

Esto genera un reporte HTML en el directorio `htmlcov/` que muestra qué líneas de código están cubiertas por los tests.

## Tecnologías Utilizadas

- **FastAPI**: Framework web asíncrono moderno y de alto rendimiento para construcción de APIs REST
- **SQLAlchemy**: ORM (Object-Relational Mapping) con soporte asíncrono para operaciones eficientes de base de datos
- **Alembic**: Herramienta de migraciones de base de datos para gestionar cambios en el esquema
- **Pydantic**: Biblioteca para validación de datos y definición de schemas usando anotaciones de tipo Python
- **pytest**: Framework de testing robusto y extensible para Python
- **httpx**: Cliente HTTP asíncrono moderno para realizar requests a APIs externas
- **JWT (JSON Web Tokens)**: Estándar para tokens de autenticación seguro y escalable
- **Google OAuth2**: Protocolo de autenticación SSO (Single Sign-On) mediante Google

## Características Destacadas

### Arquitectura en Capas

El proyecto sigue una arquitectura en capas que separa claramente las responsabilidades:
- **Capa de Endpoints**: Maneja las solicitudes HTTP y respuestas
- **Capa de Servicios**: Contiene la lógica de negocio y orquestación
- **Capa de Modelos**: Define las entidades de base de datos y relaciones
- Esta separación facilita el mantenimiento, testing y escalabilidad del código

### Async/Await

Toda la aplicación utiliza operaciones asíncronas mediante `async/await` de Python, lo que permite:
- Alto rendimiento con manejo eficiente de I/O
- Capacidad de manejar múltiples solicitudes concurrentes
- Mejor utilización de recursos del servidor

### Manejo de Errores Robusto

El sistema incluye un manejo de errores centralizado con:
- Excepciones personalizadas para diferentes tipos de errores
- Handlers globales que capturan y formatean respuestas de error
- Logging detallado de errores con información de contexto
- Mensajes de error apropiados según el entorno (desarrollo vs producción)

### Seguridad Multicapa

La aplicación implementa múltiples capas de seguridad:
- **API Keys**: Para autenticación service-to-service
- **JWT**: Para autenticación de operadores
- **ACL**: Sistema de permisos granular
- **CSRF Protection**: Protección contra ataques Cross-Site Request Forgery
- **Rate Limiting**: Prevención de abuso y ataques de fuerza bruta

### Observabilidad

Sistema completo de observabilidad que incluye:
- **Logging estructurado**: Logs con formato consistente y fácil de parsear
- **Audit logs**: Registro completo de todas las acciones del sistema
- **Request IDs**: Trazabilidad de solicitudes a través de todo el sistema
- **Sanitización automática**: Enmascaramiento de datos sensibles en logs

### Resiliencia

Mecanismos de resiliencia para garantizar disponibilidad:
- **Circuit breaker**: Protección contra fallos en cascada de APIs externas
- **Reintentos automáticos**: Lógica de reintentos con backoff exponencial
- **Timeouts configurables**: Prevención de esperas indefinidas
- **Manejo de errores de red**: Recuperación graceful de errores de conectividad

### Escalabilidad

Diseñado para escalar horizontalmente:
- Arquitectura stateless que permite múltiples instancias
- Base de datos con soporte para conexiones concurrentes
- Configuración de Gunicorn con múltiples workers
- Preparado para despliegue en contenedores y orquestación

## Documentación

La documentación interactiva de la API está disponible en los siguientes endpoints cuando la aplicación está en ejecución:

- **Swagger UI**: `http://localhost:8000/api/v1/docs` - Interfaz interactiva para explorar y probar los endpoints
- **ReDoc**: `http://localhost:8000/api/v1/redoc` - Documentación alternativa con formato más legible

Ambas interfaces se generan automáticamente a partir de los schemas Pydantic y las anotaciones de los endpoints FastAPI.

