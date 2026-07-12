# NepWork API

> A scalable, location-aware job & services marketplace backend — connecting employers, freelancers, and workers through map-based discovery, real-time chat, and integrated payments.

Built with **Django REST Framework**, **PostgreSQL**, and **PostGIS**.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the Project](#running-the-project)
- [Database Migrations](#database-migrations)
- [Dev Tools](#dev-tools)
- [Troubleshooting](#troubleshooting)

---

## Overview

NepWork API is a location-aware job marketplace backend designed for the Nepali market. It supports multiple user roles, geospatial job discovery powered by PostGIS, escrow-based payments via eSewa and Khalti, real-time chat, and an intelligent recommendation engine — all exposed through a clean REST API.

---

## Features

### 👤 User System

- Multi-role accounts: Job Seeker, Employer, Freelancer, Worker
- Profile management with skills & resume upload
- Availability status: Online / Offline / Busy

### 💼 Job System

- Job types: Full-time, Part-time, Freelance, One-time
- Work modes: Remote, On-site, Hybrid
- Apply, save, share jobs
- Job status tracking

### 🗺️ Map System (PostGIS)

- Nearby job search via radius queries
- Worker location tracking
- Map-based discovery
- Geo filtering by city, country, or distance

### 💳 Payments (Escrow)

- Stripe, eSewa, and Khalti integration
- Milestone-based payments
- Refund system

### 💬 Chat System

- Real-time messaging
- Job-based chat rooms
- File sharing

### ⭐ Rating System

- Employer & worker reviews
- Trust score system

### 🤖 Recommendation System

- Skill-based matching
- Location-based ranking
- Behavioral recommendations

### 🛡️ Admin Panel

- Permission-based admin system
- User & job moderation
- Analytics dashboard with heatmaps

---

## Architecture

```
React / Next.js (Frontend)
        │
        ▼
Django REST Framework (API Layer)
        │
        ├── PostgreSQL + PostGIS (Geospatial Database)
        ├── Celery (Background Tasks)
        └── eSewa / Khalti (Payment Gateways)
```

---

## Tech Stack

| Layer      | Technology                      |
| ---------- | ------------------------------- |
| Backend    | Django 6, Django REST Framework |
| Database   | PostgreSQL, PostGIS             |
| Geospatial | GeoDjango (GDAL, PROJ, GEOS)    |
| Task Queue | Celery                          |
| Auth       | JWT                             |

---

## Prerequisites

This project uses [`uv`](https://docs.astral.sh/uv/) for fast, reliable Python package management. Install it before getting started.

**Linux / macOS**

```bash
curl -Ls https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell)**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify installation:

```bash
uv --version
```

> 📖 Official docs: https://docs.astral.sh/uv/

---

## Installation

### 1. Clone the Repository

```bash
git clone <repo-url>
cd nepwork-api
```

### 2. Create Virtual Environment

```bash
uv venv
```

> Creates a `.venv/` directory. No manual activation required — `uv run` handles it automatically.

### 3. Install Dependencies

**Development (recommended for local work):**

```bash
uv sync
```

**Production dependencies only:**

```bash
uv sync --no-dev
```

### 4. Install Pre-commit Hooks

```bash
uv run pre-commit install
```

### 5. Configure Environment Variables

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Make sure your `.env` matches your local PostgreSQL credentials and any required API keys.

### 6. Set Up the Database

Connect to PostgreSQL and enable the PostGIS extension:

```sql
CREATE EXTENSION postgis;
```

Then apply migrations:

```bash
uv run python manage.py migrate
```

---

## Running the Project

**Start the development server:**

```bash
uv run python manage.py runserver
```

**Create a superuser:**

```bash
uv run python manage.py createsuperuser
```

---

## Database Migrations

**Generate migration files after model changes:**

```bash
uv run python manage.py makemigrations
```

**Apply pending migrations:**

```bash
uv run python manage.py migrate
```

---

## Managing Dependencies

**Add a production dependency:**

```bash
uv add <package-name>
```

**Add a dev dependency** (linting, testing, etc.):

```bash
uv add --dev <package-name>
```

**Remove a dependency:**

```bash
uv remove <package-name>
```

---

## Dev Tools

### Linting & Formatting

This project uses [Ruff](https://docs.astral.sh/ruff/) for fast linting and formatting.

```bash
# Check for issues
uv run ruff check .

# Auto-fix issues
uv run ruff check . --fix

# Watch mode (re-lint on file change)
ruff check --watch

# Format code
uv run ruff format .
```

### Type Checking

```bash
mypy .
```

### Pre-commit

Run all hooks against every file:

```bash
uv run pre-commit run --all-files
```

Clean the pre-commit cache if needed:

```bash
uv run pre-commit clean
```

Pre-commit runs the following checks automatically on each commit:

- `ruff` — lint and fix
- `mypy` — type checking
- Standard file checks (trailing whitespace, end-of-file, etc.)

---

## Troubleshooting

### GDAL Not Found

Install the system-level GDAL package for your OS, then set the library path in your `.env` or `settings.py`:

```python
GDAL_LIBRARY_PATH = "/usr/lib/libgdal.so"  # adjust path as needed
```

### PostGIS Extension Missing

Connect to your PostgreSQL database and run:

```sql
CREATE EXTENSION postgis;
```

### Database Connection Fails

Double-check that the values in your `.env` file match your local PostgreSQL setup (host, port, name, user, password).


python manage.py startapp user_activity apps/user_activity
