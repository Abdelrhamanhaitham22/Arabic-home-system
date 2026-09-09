# Arabic Language Learning & Exam Results System

Bilingual (Arabic/Russian) web platform for student registration and exam result lookup.

## Overview

- **Students** register for free and receive a permanent unique code (e.g., `ST202600001`).
- **Students** use their code on the Results page to look up exam scores.
- **Administrators** manage students, exams, and results via Django's built-in admin dashboard (`/admin/`).

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Django 5.x + Django REST Framework |
| Database | PostgreSQL 16 |
| Frontend | React 18 + Vite + TypeScript |
| Styling | Tailwind CSS 3 |
| Admin Theme | django-jazzmin |
| Containerization | Docker + Docker Compose |

## Project Structure

```
.
├── backend/          # Django project
├── frontend/         # React app (3 public pages)
├── docker-compose.yml
├── docker-compose.production.yml
├── Dockerfile.backend
├── Dockerfile.frontend
└── implementation_plan.md
```

## Public Pages

- `/` — Home
- `/register` — Student registration
- `/results` — Exam result lookup

## Public API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/students/register/` | Register a new student |
| `GET` | `/api/results/{student_code}/` | Look up results by student code |

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/Abdelrhamanhaitham22/Arabic-home-system.git
cd Arabic-home-system
```

### 2. Run locally with Docker Compose

```bash
docker compose up --build
```

This starts:
- Django backend at `http://localhost:8000`
- PostgreSQL at `localhost:5432`
- React frontend at `http://localhost:5173`

### 3. Run in production with Docker Compose

```bash
docker compose -f docker-compose.production.yml up --build
```

This starts:
- Frontend + Nginx reverse proxy on `http://localhost`
- Backend API served at `/api/` and `/admin/` via Nginx
- PostgreSQL database

### 4. Create an admin user

```bash
docker compose exec backend python manage.py createsuperuser
```

Then access the admin panel at `http://localhost/admin/`.

### 4. Run backend tests

```bash
docker compose exec backend python manage.py test
```

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DJANGO_SECRET_KEY` | `dev-only-secret-key` | Django secret key (required in production) |
| `DJANGO_DEBUG` | `1` | Set to `0` in production |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated list of allowed hostnames; use `*` to allow any Railway domain |
| `POSTGRES_HOST` | `localhost` | PostgreSQL host |
| `POSTGRES_DB` | `arabic_learning` | PostgreSQL database name |
| `POSTGRES_USER` | `postgres` | PostgreSQL user |
| `POSTGRES_PASSWORD` | `postgres` | PostgreSQL password |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | Comma-separated allowed frontend origins; use `*` to allow all |
| `CORS_ALLOW_ALL_ORIGINS` | `0` | Set to `1` to allow CORS from any origin |
| `DJANGO_SECURE_SSL_REDIRECT` | `0` | Set to `1` to redirect HTTP to HTTPS |

## Railway Deployment

### Single origin (recommended)

Deploy the whole stack from `docker-compose.production.yml`. Nginx will proxy `/api/` and `/admin/` to the backend service automatically.

### Separate frontend and backend services

1. In the frontend Railway service, set the build variable:

```env
VITE_API_BASE_URL=https://your-backend-service.up.railway.app/api
```

2. In the backend Railway service, set the allowed frontend origin and allow any Railway hostname:

```env
DJANGO_ALLOWED_HOSTS=*
CORS_ALLOWED_ORIGINS=https://your-frontend-service.up.railway.app
```

Or allow all origins for testing (not recommended for production):

```env
CORS_ALLOW_ALL_ORIGINS=1
```

The backend root path (`/`) and `/health/` both return `{"status":"ok"}` for Railway's healthcheck.

## License

[MIT](LICENSE)
