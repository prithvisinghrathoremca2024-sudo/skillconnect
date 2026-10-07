# SkillConnect

SkillConnect is a Flask web application that connects customers with local service workers. Customers can browse worker profiles and request bookings; workers can manage requests and earnings; administrators can review worker registrations.

The application renders HTML pages with Jinja templates and stores its data in SQLite. It is a browser-based web app, not a JSON/REST API.

## Features

- Browse services and search workers by skill, city, or search term.
- Register and sign in as a customer or worker.
- Create bookings and track their status.
- Let workers accept, reject, or complete bookings.
- Leave a rating and review after a booking is completed.
- View role-specific customer, worker, and administrator dashboards.
- Review and update worker verification status as an administrator.
- Send in-app notifications for booking and verification events.
- Calculate a 10% platform commission on bookings.

## Requirements

- Python 3.8 or later
- pip
- A modern web browser
- Internet access for the Bootstrap and Bootstrap Icons assets loaded from CDNs

SQLite is included with Python, so no separate database server is required.

## Run locally

Open a terminal in the project root (the directory containing `requirements.txt`).

### Windows PowerShell

Create and activate a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, allow it for the current terminal session and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Install the dependencies and start the app:

```powershell
python -m pip install -r requirements.txt
python backend/app.py
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python backend/app.py
```

When the server starts, open <http://127.0.0.1:5000/> in your browser. Stop it with **Ctrl+C** in the terminal.

## First login

On startup, the app creates the SQLite tables if they do not already exist. If there is no administrator account yet, it creates this demo account:

| Role | Email | Password |
|---|---|---|
| Administrator | `admin@skillconnect.com` | `admin123` |

Use these credentials only for local development or demonstration. Change the seeded credentials and secret key before using the application in any shared or production environment. If an administrator with that email already exists in the database, startup will not reset its password.

Customers can create an account from **Join as Customer**. Workers can register through **Become a Worker**; their account starts with a pending verification status, which an administrator can update from the admin console.

## Data and database

The SQLite database is `skillconnect.db` in the project root. The app creates it automatically when it initializes. It stores user accounts, worker profiles, service categories, bookings, reviews, and notifications. Moving the backend code does not move the database.

Keep a backup of `skillconnect.db` if you need to preserve local data. Avoid deleting or replacing it unless you intend to reset the application data. The application currently creates the categories table but does not automatically populate sample categories.

An optional sample-data script is available:

```powershell
python backend/seed.py
```

Run it from the project root after starting the app once. **This script deletes existing users, bookings, reviews, categories, and notifications before inserting demo data.** Do not run it if you need to preserve your current database contents.

## Project layout

```text
.
├── backend/
│   ├── app.py             # Flask app, routes, database setup, and application logic
│   └── seed.py            # Optional demo-data script
├── frontend/
│   ├── templates/         # Jinja HTML templates
│   └── static/
│       ├── css/style.css  # Application styles
│       └── js/main.js     # Browser-side JavaScript
├── requirements.txt       # Python dependencies
├── skillconnect.db        # SQLite database (created on startup)
└── README.md
```

## Main pages

| URL | Purpose |
|---|---|
| `/` | Home page |
| `/about` | About page |
| `/services` | Service categories |
| `/workers` | Browse and search workers |
| `/worker/<worker_id>` | Worker profile and reviews |
| `/register` | Customer registration |
| `/register-worker` | Worker registration |
| `/login` and `/logout` | Sign in and sign out |
| `/customer/dashboard` | Customer bookings |
| `/worker/dashboard` | Worker bookings and earnings |
| `/admin` | Administrator dashboard |

Some pages require a signed-in account with the appropriate role.

## Dependencies

Python packages are listed in `requirements.txt`:

- Flask
- Werkzeug

Install them with `python -m pip install -r requirements.txt` as shown above.

## Development and production notes

`python backend/app.py` starts Flask's built-in development server with debug mode enabled. Run this command from the project root. Use the built-in server only for local development. Before deploying:

- Turn off debug mode and use a production-ready WSGI server.
- Replace the hard-coded Flask secret key in `backend/app.py` with a securely managed environment-specific value.
- Change the demo administrator credentials.
- Review authentication, authorization, and form protections for your deployment requirements.
- Ensure the SQLite database is stored and backed up appropriately for the hosting environment.
