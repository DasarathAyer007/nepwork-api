# NepWork API

> A scalable, location-aware job & services marketplace backend — connecting employers, freelancers, and workers through map-based discovery, real-time chat, and integrated payments.

Built with **Django REST Framework**, **PostgreSQL**, and **PostGIS**.

---

## Features

### 👤 User System
- Multi-role accounts: Job Seeker, Employer, Freelancer, Worker
- Profile management with skills & resume upload
- Availability status: Online / Offline / Busy

### 💼 Job System
- Full-time, Part-time, Freelance, and One-time job types
- Remote, On-site, and Hybrid support
- Apply, save, and share jobs
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

| Layer | Technology |
|---|---|
| Backend | Django 6, Django REST Framework |
| Database | PostgreSQL, PostGIS |
| Geospatial | GeoDjango (GDAL, PROJ, GEOS) |
| Task Queue | Celery |
| Auth | JWT |

---

## Getting Started

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd nepwork-api
```

### 2. Create & Activate Virtual Environment

**Linux / macOS**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows**
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

## System Dependencies

> ⚠️ PostGIS and GeoDjango require GDAL, PROJ, and GEOS to be installed at the OS level.

**Ubuntu / Debian**
```bash
sudo apt update && sudo apt install -y gdal-bin libgdal-dev libproj-dev binutils
```

**Fedora**
```bash
sudo dnf install -y gdal gdal-devel proj proj-devel geos geos-devel
```

**macOS**
```bash
brew install gdal
```

**Windows**
Install [OSGeo4W](https://trac.osgeo.org/osgeo4w/) and include GDAL, PROJ, and GEOS during setup.

 Windows Guide : [Medium Artical](https://medium.com/@limeira.felipe94/gdal-configuration-and-installation-on-windows-for-django-projects-538171db5ccc/).
---

## Configuration

Create a `.env` file in the project root and set your environment variables:

```env
DATABASE_NAME=nepwork
DATABASE_USER=your_db_user
DATABASE_PASSWORD=your_db_password
DATABASE_HOST=localhost
DATABASE_PORT=5432
SECRET_KEY=your_django_secret_key
```

---

## Run the Project

### Apply Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### Create a Superuser

```bash
python manage.py createsuperuser
```

### Start the Development Server

```bash
python manage.py runserver
```

---

## Common Issues

### GDAL Not Found

Install the system-level GDAL package for your OS (see [System Dependencies](#system-dependencies)) and set the library path in your `.env` or `settings.py`:

```python
GDAL_LIBRARY_PATH = "/usr/lib/libgdal.so"  # adjust path as needed
```

### PostGIS Extension Missing

Connect to your PostgreSQL database and run:

```sql
CREATE EXTENSION postgis;
```

### Database Connection Fails

Double-check the values in your `.env` file match your local PostgreSQL setup.

---

