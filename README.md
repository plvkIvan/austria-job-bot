# Austria Job Bot — Python MVP foundation

Three languages: Ukrainian, German, English. FastAPI, SQLAlchemy, WhatsApp webhook scaffold, matching, five source adapters.

**IMPORTANT:** The five Austrian source adapters are intentionally DISABLED until authorized APIs or written permissions are obtained. The demo adapter returns synthetic data only. This is **not** a functioning live job aggregator yet.

## Quick start (Python 3.11+)

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Windows: copy .env.example .env
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs and try POST `/demo/message` with `{"phone":"test1","text":"hi"}`, then `uk`, city, occupation, German level, employment, consent. `GET /health` returns `ok`.

```bash
pytest -q
```

## What is ready
- Local conversation state machine and 3-language prompts
- Consent, STOP/START, profile and delete commands
- SQLite for local development; PostgreSQL via DATABASE_URL for production
- Job normalization, uniqueness per source/external_id, basic matcher, collector
- WhatsApp verification endpoint, HMAC-validated inbound webhook, basic outbound replies
- Dockerfile, tests, configuration template

## Not production-ready / still needed
- Authorized live feeds for karriere.at, AMS, StepStone, hokify, willhaben
- Approved WhatsApp message templates for proactive job alerts; no automated alerts yet
- Webhook event idempotency, background queue/retries, provider rate limits, structured logs
- Migrations (Alembic), encryption/privacy review, retention and access controls
- Geographic distance, job synonym dictionary, robust matching and duplicate detection across sources
- GDPR-compliant privacy notice and opt-in language, Meta Business setup
- Production scheduler, monitoring, full integration tests

**Security:** Never commit `.env`. The webhook refuses incoming POST requests until app secret is set. The `/demo/message` route is a local development tool and MUST be disabled or authenticated before deployment to the internet.
