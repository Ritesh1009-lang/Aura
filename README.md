# Aura

A small mental-wellbeing resource site with account registration, a supportive keyword-based chat widget, and self-reflection quizzes. Quiz results are informational only and are not medical diagnoses.

## Project structure

```
app.py                 Flask application and routes
templates/             Server-rendered HTML pages
static/css/            Site styles
static/images/         Site imagery
archive/               Superseded pages, databases, and the old standalone quiz app
```

## Run locally

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open 'aura-livid-tau.vercel.app' in a browser.

## Supabase setup

Aura uses Supabase Auth for credentials and Supabase Postgres for profile and quiz-result data. Copy `.env.example` to `.env`, fill in the Supabase values, then run the complete SQL in `supabase/schema.sql` in the Supabase SQL Editor. Never commit `.env` or expose `SUPABASE_SECRET_KEY`.

The detailed dashboard and security steps are in the project’s setup guide below.

1. In Supabase Dashboard, create a project. Open **Connect** to copy the Project URL and Publishable key; find the Secret key at **Settings → API Keys**.
2. Set **Authentication → URL Configuration**: Site URL `http://127.0.0.1:5000`; add redirect URLs `http://127.0.0.1:5000/login?confirmed=1` and `http://127.0.0.1:5000/reset-password`.
3. At **Authentication → Providers → Email**, enable Email and Confirm email. In production, configure Custom SMTP before launch.
4. Install requirements, restart the Flask server, and test sign-up, email confirmation, login, and password reset.

After registration, check both **Authentication → Users** (the secure Auth account) and **Table Editor → profiles** (username, phone, date of birth, and age). Passwords will never appear in either table because Supabase Auth stores them securely.
