# Expense Tracker — Multi-user Streamlit App

A Streamlit expense tracker with registration/login, bcrypt password hashing, PostgreSQL persistence, and per-user expense isolation.

## Features

- Register with username, email, and password
- Login with username or email
- Passwords are stored as bcrypt hashes, never plaintext
- Expenses stored in PostgreSQL and persist across app restarts
- Each query is scoped to the logged-in user's ID
- Add expenses by date/category/amount/note
- Dashboard with category totals and monthly spending
- Filter and delete your own expenses
- BDT currency display

## 1. Create a PostgreSQL database

Create a database with a hosted PostgreSQL provider such as Supabase or Neon. Copy its connection string. Do not share or commit this secret.

The app expects a SQLAlchemy URL similar to:

```text
postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require
```

If your provider gives a URL beginning with `postgres://` or `postgresql://`, convert the prefix to `postgresql+psycopg://` and retain the remaining connection details. URL-encode special characters in the username/password if necessary.

## 2. Run locally

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Set the environment variable before starting Streamlit.

PowerShell:

```powershell
$env:DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require"
streamlit run app.py
```

macOS/Linux:

```bash
export DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require"
streamlit run app.py
```

The app creates the `users` and `expenses` tables on startup.

## 3. Deploy to Streamlit Community Cloud

1. Upload `app.py`, `requirements.txt`, `README.md`, and `.gitignore` to your GitHub repository.
2. Deploy/redeploy the app from Streamlit Community Cloud, with `app.py` as the main file.
3. Open the deployed app's **Settings → Secrets**.
4. Add your actual database URL:

```toml
DATABASE_URL = "postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require"
```

5. Save the secret and restart/reboot the app.
6. Test by creating a new account and saving an expense.

Never commit the real database URL to GitHub. Use a separate database credential for production and rotate it if exposed.

## Security notes

- Passwords are hashed with bcrypt.
- Database statements use SQL parameters.
- Expense reads/deletes are scoped to the authenticated user's `user_id`.
- This is a useful starter application, not a full enterprise identity system. For a public production service, add email verification, password reset, rate limiting/login throttling, CSRF/session hardening as appropriate, monitoring, backups, and database access policies.
- Anyone who registers can use the app; no admin approval is required.
- Existing data in any old local CSV/SQLite file is not automatically imported. Back up and migrate it separately if needed.
