# Arabic Learning & Exam Results System

Bilingual Arabic/Russian student registration and exam-results lookup platform.

## Local development

### Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
$env:DJANGO_DATABASE="sqlite"
.venv/Scripts/python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Django admin is available at `http://localhost:8000/admin/`.

## Tests and checks

```bash
cd backend
DJANGO_TESTING=1 .venv/Scripts/python manage.py test
python manage.py check --deploy

cd ../frontend
npm run build
npm run lint
```

## Docker development

```bash
docker compose up --build
```

## Production Docker

Copy the required values into a `.env` file, then run:

```bash
docker compose -f docker-compose.production.yml up --build -d
```

Set `DJANGO_SECURE_SSL_REDIRECT=1`, `DJANGO_SESSION_COOKIE_SECURE=1`, `DJANGO_CSRF_COOKIE_SECURE=1`, and HSTS only when TLS is terminated by the deployment environment.

## Public endpoints

- `POST /api/students/register/`
- `GET /api/results/<student_code>/`
- `GET /health/`
