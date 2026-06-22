# Fit Zone Gym Management System — Setup Guide

## Prerequisites

| Requirement | Version | Download |
|---|---|---|
| Python | 3.9 or higher | https://www.python.org/downloads/ |
| Git | Any | https://git-scm.com/downloads |

> **Important:** During Python installation, check **"Add Python to PATH"** before clicking Install.

---

## Step 1 — Clone the Repository

Open **Command Prompt** or **PowerShell** and run:

```
git clone <your-repository-url>
cd demo
```

---

## Step 2 — Install Dependencies

```
pip install -r requirements.txt
```

This installs: FastAPI, Uvicorn, Jinja2, OpenPyXL, python-dateutil, and other required packages.

---

## Step 3 — Run the Application

**Option A — Double-click (easiest):**
- Double-click `start.bat`
- Browser will open automatically at `http://127.0.0.1:8000`

**Option B — Command line:**
```
python main.py
```

---

## Step 4 — First Login

On first startup the system automatically creates a default admin account.

| Field | Value |
|---|---|
| Username | `admin` |
| Password | `admin123` |

> Change the password after first login (via Settings or ask your admin).

---

## Folder Structure

```
demo/
├── main.py               ← Application entry point
├── database.py           ← Database logic (SQLite)
├── auth.py               ← Login / session management
├── config.py             ← Template engine config
├── requirements.txt      ← Python dependencies
├── start.bat             ← One-click launcher (Windows)
├── gym.db                ← SQLite database (auto-created on first run)
├── backup/               ← Auto-backups (created on each startup)
├── static/               ← CSS, JS, images
├── templates/            ← HTML pages
├── routers/              ← API route handlers
└── donotexecute/         ← Admin utility scripts (run manually only)
    ├── clear_data.py     ← Deletes all member/payment data
    └── clear_sessions.ps1← Clears all active login sessions
```

---

## Auto-Backup

Every time the application starts, it automatically:
- Creates `backup/DBBKPYYYYMMDD.db` (copy of gym.db)
- Keeps only the **2 most recent** backup files

---

## Troubleshooting

**"Python is not installed or not in PATH"**
- Reinstall Python and tick **"Add Python to PATH"** during setup.
- Verify with: `python --version`

**"Port 8000 already in use"**
- The app will automatically try ports 8001–8019.
- Or close the other application using port 8000.

**Browser does not open automatically**
- Manually open: `http://127.0.0.1:8000`

**Cannot log in after server restart**
- Sessions are stored in memory. A server restart logs everyone out — just sign in again.

**Lost admin password**
- Run this from the project folder to reset:
  ```
  python -c "import database as db, auth; db.create_user('admin2', auth.hash_password('newpassword'))"
  ```
