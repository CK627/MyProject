# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Portfolio monorepo containing 12 independent projects. The `main` branch holds all project directories and serves as the index; most projects also have their own dedicated git branch (e.g., `git checkout ChatRoom`). Documentation is primarily in Chinese.

## Project Quick Reference

### SmartCampusServicePlatform (Next.js + FastAPI)
The most complex project — full-stack SPA with JWT auth.

```bash
# Frontend
cd SmartCampusServicePlatform && npm install && npm run dev   # port 3000
npm run build                                                  # production build
npm run lint

# Backend
cd SmartCampusServicePlatform/backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Database: MySQL 8.0+, configure `backend/.env` from `.env.example`
- Auth: JWT via python-jose + optional GitHub OAuth (`GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`)
- ORM: SQLAlchemy 2.0 with PyMySQL
- Frontend talks to backend via REST (Fetch API) and WebSocket

### PHP Projects (SchoolConferenceSystem, FlightControlBoardMaintenanceWorkOrderSystem, NingboTravelGuideWebsite, FileUpload)
All require a PHP web server + MySQL. Common pattern:
1. Import the SQL file into MySQL
2. Copy example config files and fill in DB credentials
3. Run with `php -S localhost:8000` or use XAMPP/Nginx

| Project | SQL File | Config Location | Default Port |
|---------|----------|-----------------|-------------|
| SchoolConferenceSystem | `docs/school_conference.sql` | `frontend/api/database.php`, `backend/api/database.php` | XAMPP default |
| FlightControlBoardMaintenanceWorkOrderSystem | `fcbmwos_mysql8_updated.sql` | `config/mysql.ini` (copy from `.example`) | 8000 |
| NingboTravelGuideWebsite | `api/config/init.sql` | `api/config/db.php` (copy from `.example`) | XAMPP default |
| FileUpload | Auto-creates tables | `config/mysql.ini`, `config/mysql_files.ini` | 8000 |

**FileUpload** is the largest PHP project (~60 API files). Has a documented MVC refactoring plan in `REFACTOR_PLAN.md`. Supports Vercel deployment via `vercel.json`.

### Python Projects (ChatRoom, WebMailMonitor, BlockchainRandomNumberGenerator)

```bash
# ChatRoom — LAN P2P chat
cd ChatRoom && pip install -r requirements.txt && python app.py

# WebMailMonitor — uptime monitor with email alerts
cd WebMailMonitor && pip install requests schedule pystray pillow
python web_monitor_server.py    # web panel (port 2442)
python web_monitor_console.py   # console mode

# BlockchainRandomNumberGenerator
cd BlockchainRandomNumberGenerator && pip install flask
python BlockchainRandomNumberGenerator.py   # port 5000
```

### Static Frontend Projects (ResponsiveQujiangTravelInformationPlatform, BitTally)
No build step. Open `index.html` directly in a browser or serve with `python -m http.server 8000`.

### Shell Tools (jtool, ptool)
Cross-platform version managers installed via `./install.sh` (macOS/Linux) or `install.bat` (Windows).

```bash
jtool use 21          # switch Java version
ptool use 3.11        # switch Python version
```

## Architecture Notes

- **SmartCampusServicePlatform**: Next.js 14 (App Router, TypeScript, Tailwind CSS) frontend → FastAPI REST backend → MySQL via SQLAlchemy. JWT stored client-side. WebSocket for real-time notifications.
- **PHP projects**: Traditional B/S with one-file-per-route PHP API pattern. SchoolConferenceSystem has three separate API directories for PC, mobile, and admin contexts.
- **ChatRoom**: Flask-SocketIO for WebSocket, UDP broadcast for LAN peer discovery, P2P messaging (no central relay).
- **FileUpload**: Role-based access (student/teacher/admin), chunked file upload, two MySQL databases (`FileUpload` for app data, `FileUploadS` for file storage).

## Multi-Branch Workflow

Each project has its own branch. When working on a specific project, check it out to its branch for the clean, standalone view:
```bash
git checkout <ProjectDirectoryName>
```
The `main` branch contains all directories together for the portfolio overview.
