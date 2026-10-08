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

Local development only: `setup_school` creates `admin@dampol1nhs.edu.ph` with the password `changeme123`. With `DEBUG=false` that default is refused; run `python manage.py setup_school --password '<a strong password>'`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite default: http://localhost:5173

## Production (Railway)

Three services in one Railway project, all over HTTPS:

```
Browser -> Frontend (static site) -> Django API -> MySQL (Railway private network only)
```

MySQL is reached through Railway's private network variables. It never needs a public address. Every secret
is a Railway variable; nothing secret goes into the repository or into `VITE_*` variables, which are public.

### API service (root directory `backend`)

`backend/railway.json` runs migrations before each deploy, collects static files and starts gunicorn, and
uses `/api/health/` as the health check. First deploy on an empty database only:

```bash
python manage.py setup_school --password '<a strong password>'
```

Variables (names only; values live in Railway):

```
DEBUG=false
SECRET_KEY                 at least 50 random characters
ALLOWED_HOSTS              the API's own hostname
FRONTEND_URL               https:// address of the frontend service
CORS_ALLOWED_ORIGINS       the same frontend address
CSRF_TRUSTED_ORIGINS       the same frontend address
NUM_PROXIES=1              Railway's proxy, so request limits apply per visitor (required)
AUTH_COOKIE_SAMESITE       Lax (same site, recommended) or None (cross-site); see "Sign-in cookies and domains"
DB_NAME DB_USER DB_PASSWORD DB_HOST DB_PORT   from the MySQL service's private variables
MAIL_TRANSPORT=brevo_api   Railway Hobby blocks SMTP
BREVO_API_KEY
DEFAULT_FROM_EMAIL         a sender verified in Brevo
EMAIL_FROM_NAME
MAIL_DELIVERY=background
RECAPTCHA_SECRET_KEY       required when DEBUG is false
GEMINI_API_KEY             optional; the chatbot works without it
MEDIA_ROOT                 the mount path of the volume that keeps uploaded photos
DJANGO_ADMIN_PATH          a hard-to-guess path for the Django admin, or "off"
SECURE_HSTS_SECONDS        starts at 3600; raise to 31536000 once HTTPS on the final domain is confirmed
```

With `DEBUG=false` the API refuses to start if the secret key, hosts, frontend address, reCAPTCHA secret, mail
settings, or `NUM_PROXIES` are missing, if a CORS origin is not `https://`, or if `MAIL_PRINT_CODES` is on.
Railway's health-check host is allowed automatically.

The app's database user should not be `root`. Create one with rights on the portal database only, and put it in
`DB_USER` / `DB_PASSWORD`:

```sql
CREATE USER 'portal_app'@'%' IDENTIFIED BY '<long random password>';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, DROP, REFERENCES ON dampol_portal.* TO 'portal_app'@'%';
```

(No `FILE`, `GRANT OPTION` or rights on other databases. The schema rights are for migrations.)

### Sign-in cookies and domains

The browser keeps only a short-lived access token in memory. The refresh token is an HttpOnly cookie that scripts
cannot read, sent only to `/api/auth/`. Login, refresh and logout also need a CSRF token. Sessions end after 30
minutes without activity and after 12 hours in any case; a password change, reset, archive or "Sign out
everywhere" ends them at once.

Give the frontend and the API addresses on the **same site**, for example `portal.<school domain>` and
`api.portal.<school domain>`, and keep `AUTH_COOKIE_SAMESITE=Lax`. Two Railway default addresses
(`*.up.railway.app`) are different sites to a browser: the cookie would need `AUTH_COOKIE_SAMESITE=None`, and
browsers that block third-party cookies (Safari, private windows) would sign people out on every page reload.

### Maintenance console

Grant console access only with `python manage.py console_access --maintenance <email>` (full, for maintainers)
or `--content-editor <email>` (chatbot FAQs only, for the portal Admin); `--revoke <email>` removes it. Sign-in
is email and password. The console path is `DJANGO_ADMIN_PATH`.

### Email sender (cron service, same repository, root `backend`)

Start command `python manage.py send_outbox`, cron schedule `*/5 * * * *`, with the API's variables. Approving or
rejecting a student queues the email in the same transaction, so it is never lost. The sender keeps
`MAIL_CODE_RESERVE` of the `MAIL_DAILY_LIMIT` free for activation and password codes, retries failures, and removes
finished rows after `MAIL_KEEP_DAYS`. With `MAIL_DELIVERY=inline` (the default, for local use) emails are sent right
after saving and no sender is needed.

### Daily maintenance (cron service, same repository, root `backend`)

Start command `python manage.py daily_maintenance`, cron schedule `0 3 * * *`, with the API's variables. It deletes
sign-in records that ended over `SESSION_KEEP_DAYS` (30) ago and blanks chatbot question text older than
`CHAT_QUESTION_KEEP_DAYS` (90), keeping only the date, topic and source.

### Frontend service (root directory `frontend`)

Set the service variable `RAILPACK_SPA_OUTPUT_DIR=dist`; Railway then builds with `npm run build` and serves the
`dist` folder as a single-page app. `frontend/Caddyfile` adds the browser security headers (Content-Security-Policy,
HSTS, no framing); confirm them on staging with `curl -I`. Variables:

```
VITE_API_BASE_URL          https://<API hostname>/api   (build, public)
VITE_RECAPTCHA_SITE_KEY    the public site key          (build, public)
API_ORIGIN                 https://<API hostname>       (runtime, for the Content-Security-Policy)
```

### Demo environment (defence only)

A separate Railway environment with its own MySQL, `DEMO_MODE=true` and its own `SECRET_KEY`. Only there may
`seed_demo_forecast` add synthetic history. Never set `DEMO_MODE` on the real school's server.

### Grade 11 forecast (Admin › Planning)

The page shows live counts, a Grade 12 estimate from the retention rate the Admin sets, and the Grade 11
trend. The trend uses scikit-learn `LinearRegression` and stays locked until three school years under the
current Grade 11 curriculum are archived. Training never runs on a page request, only here:

```bash
python manage.py train_forecast        # same as the Retrain button
```

Archiving a school year saves its final counts and retrains automatically. For the defence only, a demo
database may add invented history (refused unless `DEMO_MODE=true`):

```bash
python manage.py seed_demo_forecast           # synthetic years, marked as such on the page
python manage.py seed_demo_forecast --remove  # take them out again
```

Local development is unchanged: Django `8000`, Vite `5173`.
