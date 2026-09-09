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

### 2. Run with Docker Compose

```bash
docker compose up --build
```

This starts:
- Django backend at `http://localhost:8000`
- PostgreSQL at `localhost:5432`
- React frontend at `http://localhost:5173`

### 3. Create an admin user

```bash
docker compose exec backend python manage.py createsuperuser
```

Then access the admin panel at `http://localhost:8000/admin/`.

### 4. Run backend tests

```bash
docker compose exec backend python manage.py test
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

```env
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=postgres://user:password@db:5432/dbname
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

## License

[MIT](LICENSE)
