# Dampol 1st National High School Grade Portal

Clean rebuild of the school portal. The previous project (`gradeportal2`) is reference only and is not part of this codebase.

## Stack

- Frontend: React (Vite) + JSX + CSS per page
- Backend: Django + Django REST Framework + JWT
- Database: MySQL (`dampol_portal` by default)

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
```

Set `DB_PASSWORD` in `backend/.env` to the password for the configured MySQL user. Django connects to the MySQL database in `DB_NAME` (`dampol_portal` by default); the MySQL server and database must be available before starting Django.

The existing SQLite records have been exported to `%TEMP%\dampol_portal.json`. After setting MySQL credentials in `.env`, run these commands from `backend` to create the schema and import the fixture:

```powershell
$env:PYTHONUTF8='1'
python manage.py migrate
python manage.py loaddata "$env:TEMP\dampol_portal.json"
Remove-Item Env:PYTHONUTF8
```

Keep `backend/db.sqlite3` and the fixture until the imported records have been verified in MySQL. Remove those backup files only after confirming the import.

```powershell
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

## Production

Live frontend: https://dampol1nhsportal.web.app (Firebase project `dampol1nhsportal`). Django cannot run on Firebase Hosting. Deploy the API to a public HTTPS host that allows outbound SMTP on port 587, then point the frontend at that API.

Recommended host: **Render Web Service, paid Starter** (or any VPS). Render **free** blocks SMTP ports 25/465/587, so Brevo mail will not send there. Set the Render **root directory** to `backend`.

Do not put Django secrets in `frontend/.env.production`. Do not set `VITE_API_BASE_URL` to the Firebase URL.

### Django environment (set on the API host)

```
DEBUG=false
SECRET_KEY=
ALLOWED_HOSTS=
FRONTEND_URL=https://dampol1nhsportal.web.app
CORS_ALLOWED_ORIGINS=https://dampol1nhsportal.web.app
CSRF_TRUSTED_ORIGINS=https://dampol1nhsportal.web.app
DB_NAME=dampol_portal
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=3306
EMAIL_HOST=smtp-relay.brevo.com
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=
EMAIL_FROM_NAME=Dampol 1st NHS
MAIL_PRINT_CODES=false
MAIL_DELIVERY=background
MAIL_DAILY_LIMIT=300
MAIL_CODE_RESERVE=50
RECAPTCHA_SECRET_KEY=
GEMINI_API_KEY=
```

`ALLOWED_HOSTS` is the Django hostname only (for example `something.onrender.com`). `FRONTEND_URL` is the Firebase site. `DEFAULT_FROM_EMAIL` must already be a verified sender in Brevo.

### Django deploy (Render, root directory `backend`)

Build:

```bash
pip install -r requirements.txt
python manage.py collectstatic --noinput
```

Start (also in `backend/Procfile`):

```bash
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --timeout 60
```

Release / first boot:

```bash
python manage.py migrate --noinput
python manage.py setup_school
```

`setup_school` is only for an empty database.

Registration emails sender (needed when `MAIL_DELIVERY=background`):

```bash
python manage.py send_outbox --loop   # always-on task (PythonAnywhere)
python manage.py send_outbox          # one round, for a cron job every 5 minutes (Railway)
```

Approving or rejecting a student queues the email in the same transaction, so it is never lost. The sender keeps `MAIL_CODE_RESERVE` of the `MAIL_DAILY_LIMIT` free for activation and password codes, retries failures, and removes finished rows after `MAIL_KEEP_DAYS`. With `MAIL_DELIVERY=inline` (the default, for local use) emails are sent right after saving and no sender is needed.

### Firebase rebuild (after the API URL exists)

```powershell
cd frontend
copy .env.production.example .env.production
```

Set `VITE_API_BASE_URL=https://YOUR-DJANGO-HOST/api` and copy the public reCAPTCHA site key into `VITE_RECAPTCHA_SITE_KEY`. Then:

```powershell
npm install
npm run build
cd ..
firebase.cmd deploy --only hosting
```

Local development is unchanged: Django `8000`, Vite `5173`.
