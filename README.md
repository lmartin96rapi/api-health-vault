# Health Insurance API

FastAPI application for health insurance reimbursement form management with Google SSO, API keys, ACL, external API integrations, file uploads, and comprehensive audit logging.

## Features

- **FastAPI** with async support
- **SQLAlchemy** ORM with async support
- **Alembic** for database migrations
- **Google SSO** + **API Keys** authentication
- **ACL** (Access Control List) with endpoint and resource-level permissions
- **External API integrations** (Backend API, WspApi)
- **File storage** (local filesystem, prepared for bucket migration)
- **Comprehensive audit logging**
- **Docker** support with multiple environments
- **Multi-threaded** and optimized for high traffic

## Project Structure

```
api_health_insurance/
├── app/
│   ├── api/v1/endpoints/    # API endpoints
│   ├── core/                # Security, config, exceptions, ACL
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic + data access
│   ├── external/            # External API clients
│   ├── database.py          # Database setup
│   ├── config.py            # Configuration
│   └── main.py              # FastAPI app
├── alembic/                 # Database migrations
├── tests/                   # Test suite
├── docker/                  # Dockerfiles
└── requirements.txt         # Dependencies
```

## Setup

### 1. Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Database Migrations

```bash
alembic upgrade head
```

### 4. Run Application

**Development:**
```bash
uvicorn app.main:app --reload
```

**Production (with Gunicorn):**
```bash
gunicorn app.main:app -c gunicorn_conf.py
```

## Docker

### Development
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Production
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## API Endpoints

### Forms
- `POST /api/v1/forms` - Create form
- `GET /api/v1/forms/{form_token}` - Get form details
- `POST /api/v1/forms/{form_token}/submit` - Submit form with documents
- `GET /api/v1/forms/{form_token}/status` - Get form status

### Documents
- `GET /api/v1/document-access/{access_token}` - View submission
- `GET /api/v1/document-access/{access_token}/documents/{document_id}/invoice/download` - Download invoice
- `GET /api/v1/document-access/{access_token}/documents/{document_id}/view` - View document

### Authentication
- `POST /api/v1/auth/google` - Google SSO authentication
- `GET /api/v1/auth/me` - Get current user

### Audit
- `GET /api/v1/audit-logs` - Query audit logs

## Documentation

API documentation available at:
- Swagger UI: `http://localhost:8000/api/v1/docs`
- ReDoc: `http://localhost:8000/api/v1/redoc`

## License

MIT

