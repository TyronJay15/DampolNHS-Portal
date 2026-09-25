# Dampol 1st National High School Grade Portal

Clean rebuild of the school portal. The previous project (`gradeportal2`) is reference only and is not part of this codebase.

## Stack

- Frontend: React (Vite) + JSX + CSS per page
- Backend: Django + Django REST Framework + JWT
- Database: SQLite for local development (MySQL-ready later)

## Roles

Accounts have exactly three types:

- `student`
- `teacher`
- `admin`

Adviser, subject teacher, and head teacher are **assignments** on a teacher account, not separate logins.

## Development

Local ports are fixed. Do not change them.

- Django API: http://localhost:8000 (`python manage.py runserver 8000`)
- Vite: http://localhost:5173
- Frontend API URL: `http://localhost:8000/api`

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py setup_school
python manage.py runserver 8000
```

API health: http://localhost:8000/api/health/

Default admin (change immediately): `admin@dampol1nhs.edu.ph` / `changeme123`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite default: http://localhost:5173
