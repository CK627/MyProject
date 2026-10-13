# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Portfolio monorepo containing 13 independent projects. The `main` branch holds all project directories and serves as the index; most projects also have their own dedicated git branch (e.g., `git checkout ChatRoom`). Documentation is primarily in Chinese.

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

### CtfSweep (Python, 零依赖 CLI)
CTF / 应急响应取证扫描器：把 pcap/pcapng、evtx、.reg、内存镜像、浏览器数据库、邮件、
日志、数据库导出里的可疑线索一次翻出，按置信度分级输出。

```bash
sudo bash installer/install.sh       # 落地（形态对齐 jtool/ptool；用户级去掉 sudo）
ctfsweep 抓包.pcap                    # 安装后 PATH 上唯一的无后缀软链（ctf 是 shell-setup 写的 alias）
python3 -m ctfsweep <文件或目录>      # 不安装也能跑；仓库启动器是 ./bin/ctfsweep.sh（.bat 为 Windows 版）
ctfsweep update [--check]            # 真更新：镜像优先 + GitHub 回退
bash tests/smoke.sh                  # 完整冒烟（CI 用 3.8 / 3.11 / 3.13 跑同一套）
python3 tests/test_smoke.py          # 只跑 Python 冒烟
python3 lab/train.py                 # 离线训练判断核模型（运行时不提供训练入口）
```

- **纯标准库、Python 3.8+、零第三方依赖**。
- **安装形态与 jtool/ptool 同规**：装成 devtools 副本（`~/.devtools/ctfsweep`，
  sudo 则 `/Library/devtools/ctfsweep`），PATH 上只有无后缀软链 `<根>/bin/ctfsweep`。
  ⚠️ 仓库 `bin/` 是**素材目录**（`ctfsweep.sh` + `ctfsweep.bat` 靠扩展名区分系统），
  **绝不能整体进 PATH**——zsh 命令名补全走 `$commands` 哈希、不检查可执行位，`.bat` 会跟着进候选。
- **运行时只做扫描与打分**：模型随版本发布（`models/model.ctfj` + `train_config.json`）；
  自学习闭环（留存 → 标注 → 训练 → 回写）已整体移除，训练只走仓库里的 `lab/train.py`。
- 数据目录只有一个语义——**扫描缓存**（`~/.devtools/ctfsweep/cache/`，每次扫描都写），
  **永不自动删除**；`update` / `uninstall` 都只碰功能文件。
- 改版本号要同步 `VERSION` 与 `ctfsweep/__init__.py`
  （与 jtool/ptool 的 `VERSION` 规矩同理，此处由冒烟测试断言）。
- 输出/注释/提交信息均为中文，报告文案被测试逐字断言。
- **动手前先读 `CtfSweep/CLAUDE.md`**（有路由静默失败、findings 数据契约、
  噪音闸门、负样本必须同题等关键约定）。

### Static Frontend Projects (ResponsiveQujiangTravelInformationPlatform, BitTally)
No build step. Open `index.html` directly in a browser or serve with `python -m http.server 8000`.

### Shell Tools (jtool, ptool)
Cross-platform version managers installed via `./install.sh` (macOS/Linux) or `install.bat` (Windows).

```bash
jtool use 21          # switch Java version
ptool use 3.11        # switch Python version
```

**VERSION 管理**: jtool 和 ptool 各自根目录有 `VERSION` 文件，`update` 命令通过比对远程 VERSION 决定是否更新。每次修改这两个项目时，必须同步递增 `VERSION` 文件中的版本号（语义化版本），否则用户的 `update` 不会检测到变化。

## Architecture Notes

- **SmartCampusServicePlatform**: Next.js 14 (App Router, TypeScript, Tailwind CSS) frontend → FastAPI REST backend → MySQL via SQLAlchemy. JWT stored client-side. WebSocket for real-time notifications.
- **PHP projects**: Traditional B/S with one-file-per-route PHP API pattern. SchoolConferenceSystem has three separate API directories for PC, mobile, and admin contexts.
- **ChatRoom**: Flask-SocketIO for WebSocket, UDP broadcast for LAN peer discovery, P2P messaging (no central relay).
- **FileUpload**: Role-based access (student/teacher/admin), chunked file upload, two MySQL databases (`FileUpload` for app data, `FileUploadS` for file storage).
- **CtfSweep**: Zero-dependency Python CLI (pure stdlib pcap/pcapng parser, no scapy/Wireshark). Each input runs through two parallel paths — a Router that dispatches to per-format forensic modules (their `Finding`s weighted by `MetaJudge`) and the legacy 5-tuple scanner rendered by `report.py` — converging in one confidence-graded report. Router dispatch failures are swallowed silently.

## Multi-Branch Workflow

Each project has its own branch. When working on a specific project, check it out to its branch for the clean, standalone view:
```bash
git checkout <ProjectDirectoryName>
```
The `main` branch contains all directories together for the portfolio overview.
