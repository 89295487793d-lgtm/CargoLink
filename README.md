# CargoLink — Telegram Mini App + Bot MVP

This package is a substantial **development MVP**, not a production-certified marketplace. It contains:
- Telegram bot entry point and notification helpers;
- Telegram Mini App frontend with CargoLink dark-navy / white / blue visual system;
- FastAPI backend;
- PostgreSQL persistence via SQLAlchemy async;
- loads, load offers, free vehicles, roadside help listings (АЗС/СТО/Шиномонтаж), partner reports/comments, profile, notifications, reports/moderation primitives, chat/contact-exchange data models;
- Docker Compose for local development.

## What is functional in this build
- Mini App navigation and forms;
- API endpoints for profile, create/list loads, load detail, offers, free vehicles, service listings, partner posts/comments, reports, and user notifications;
- Telegram bot `/start`, web-app launch button, and basic notifications;
- database tables are initialized on startup for development.

## Important gaps before public production launch
This is not a complete hardened marketplace. Contact exchange is represented in data models but mutual-consent workflow and internal chat UI/API are not fully completed. Moderation admin UI, real geocoding/autocomplete, market-rate data integration, phone verification, organization/INN verification, robust role-based authorization, migrations (Alembic), file uploads/storage, monitoring/backups, anti-abuse/rate limiting, legal/privacy review, and comprehensive automated tests must be completed before public launch. No real market-rate data is fabricated. All launch features are intended to be free.

## Setup (Docker)
1. Copy `.env.example` to `.env`.
2. Put the BotFather token into `BOT_TOKEN` in `.env`.
3. Set `WEBAPP_URL` to the HTTPS URL where the frontend will be hosted. For local development, a tunnel is required for Telegram Web Apps; localhost alone won't open on a phone.
4. Run `docker compose up --build`.
5. Open the frontend at `http://localhost:8000/` for local browser testing. API docs: `http://localhost:8000/docs`.
6. In BotFather, set the web app URL/menu button only after you have a public HTTPS deployment URL.

## Development environment
- Python 3.12+
- PostgreSQL 16+
- `pip install -r requirements.txt`
- Set `DATABASE_URL` to a reachable PostgreSQL URL and `BOT_TOKEN`, then `uvicorn app.api:app --host 0.0.0.0 --port 8000`.
- Start bot separately with `python -m app.bot`.

## Security
- Never commit `.env` or paste the Telegram token into chat.
- `X-Telegram-Init-Data` is verified when `BOT_TOKEN` is configured, but local browser testing can use `DEV_AUTH=true`. Set `DEV_AUTH=false` in deployment.
- The dev Compose password is for local use only.
- `create_all` is used for development bootstrap; use Alembic migrations before production.
