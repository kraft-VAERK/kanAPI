# Production Checklist

Everything that needs to change before kanAPI goes live.

---

## 1. Secrets & Credentials

All values below are development defaults. Every one must be regenerated for production.

| Variable | Current (dev) | Production action |
|----------|---------------|-------------------|
| `JWT_SECRET_KEY` | 64-char hex | Regenerate: `openssl rand -hex 32` |
| `DB_USER` / `DB_PASSWORD` | `admin` / `admin` | Strong unique password, 20+ chars |
| `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | `minioadmin` / `minioadmin` | Strong unique credentials |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | Falls back to root creds | Create a dedicated service account in MinIO |
| `FGA_PRESHARED_KEY` | `kanapi-fga-secret-change-me` | Regenerate: `openssl rand -hex 24` |
| OpenFGA DB password | `password` (in docker-compose) | Strong unique password |
| `COOKIE_SECURE` | `false` | **Must be `true`** (requires HTTPS) |

Never commit `.env` to version control. Use a secrets manager (Vault, AWS Secrets Manager, Doppler) or encrypted environment injection in your deployment pipeline.

---

## 2. Environment Variables

```env
# Required for production
COOKIE_SECURE=true
AUTH_RATE_LIMIT=10/minute
CORS_ORIGINS=https://your-domain.com
MINIO_SECURE=true

# Already set but verify
JWT_ALGORITHM=HS256
FGA_API_URL=http://openfga:8080      # internal Docker address, not localhost
```

---

## 3. HTTPS / TLS

kanAPI currently has no TLS termination. In production:

- Put a reverse proxy (Nginx, Caddy, Traefik) in front of the FastAPI app
- Terminate TLS at the proxy
- Redirect all HTTP to HTTPS
- Set `COOKIE_SECURE=true` so session cookies are only sent over HTTPS
- Add HSTS header in the proxy config (or in `SecurityHeadersMiddleware` once TLS is confirmed):
  ```
  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
  ```

---

## 4. Network Isolation

### Current state (after pentest fixes)
- All Docker ports bound to `127.0.0.1` (not externally reachable)
- OpenFGA playground (port 3000) removed from host
- OpenFGA DB (port 5433) removed from host
- OpenFGA requires preshared key auth

### Production changes needed

**Remove all host port bindings.** The FastAPI app should run inside Docker on the same network, not on the host connecting via localhost.

```yaml
# Production docker-compose override:
services:
  postgres:
    ports: []                    # No host exposure
    # App connects via postgres:5432 on project_network

  minio:
    ports: []                    # No host exposure
    # App connects via minio:9000 on project_network

  openfga:
    ports: []                    # No host exposure
    # App connects via openfga:8080 on project_network
```

The only port exposed to the internet should be the reverse proxy (443).

---

## 5. Database

- [ ] Change `DB_USER` and `DB_PASSWORD` from `admin/admin`
- [ ] Change OpenFGA DB password from `password`
- [ ] Enable SSL on the PostgreSQL connection (`sslmode=require` in connection string)
- [ ] Enable SSL on the OpenFGA-to-DB connection (change `sslmode=disable` in docker-compose)
- [ ] Set up automated backups (pg_dump cron or managed DB snapshots)
- [ ] Configure connection pooling (PgBouncer or SQLAlchemy pool settings for multiple workers)

---

## 6. MinIO / Object Storage

- [ ] Change root credentials from `minioadmin/minioadmin`
- [ ] Create a dedicated service account with limited permissions (read/write to `kanapi` bucket only)
- [ ] Set `MINIO_SECURE=true` or use AWS S3 with IAM roles in production
- [ ] Enable server-side encryption for stored documents
- [ ] Configure bucket lifecycle policies if documents should expire
- [ ] Restrict MinIO console (port 9001) to admin VPN only, or disable it entirely

---

## 7. OpenFGA

- [ ] Change `FGA_PRESHARED_KEY` from the default
- [ ] Remove port 8080 from host entirely (app connects via Docker network)
- [ ] Enable SSL on the OpenFGA DB connection string
- [ ] Run `make fga-prod` on first deploy (creates store + model idempotently)
- [ ] After model changes: run `make fga-prod`, restart app, verify with a test login

---

## 8. Rate Limiting

Current: `AUTH_RATE_LIMIT=6000/minute` (effectively disabled for dev).

Production recommendation:
```env
AUTH_RATE_LIMIT=10/minute
```

This applies to `/auth/login` and `/auth/token` only. Consider adding rate limiting to other write endpoints if exposed publicly.

---

## 9. CORS

Current: `CORS_ORIGINS=http://localhost:5173`

Production:
```env
CORS_ORIGINS=https://your-domain.com
```

Never use `*` with `allow_credentials=True`. List only the exact origin(s) that need access.

---

## 10. Application Server

Current: single Uvicorn worker (`make run` / `uvicorn src.api.main:app`).

Production:
```bash
# Gunicorn with Uvicorn workers (use 2*CPU+1 workers)
gunicorn src.api.main:app -k uvicorn.workers.UvicornWorker -w 4 --bind 0.0.0.0:8000
```

Or use `make run-prod` which starts 4 workers.

---

## 11. Logging & Monitoring

- [ ] Audit logs (`logs/audit.log`) — ship to a centralized log system (ELK, Datadog, CloudWatch)
- [ ] Set up alerting on:
  - HTTP 5xx spike
  - Rate limit (429) spike (brute force attempts)
  - OpenFGA connection failures
  - Database connection pool exhaustion
- [ ] Rotate log files or use a log driver (Docker `json-file` with `max-size`)
- [ ] Never log sensitive data (passwords, tokens, PII) — audit middleware currently logs emails on login attempts, which is acceptable for audit trails but review for GDPR compliance

---

## 12. Things That Still Need Building

These are gaps identified during the pentest that aren't configuration changes:

| Gap | Risk | Effort |
|-----|------|--------|
| No file upload endpoint (documents only via seed) | Low | Medium — needs virus scanning, file type validation, size limits |
| No CSRF tokens (relies on SameSite cookies) | Medium | Low — add if any GET endpoints mutate state (legacy `GET /user/delete` exists) |
| `GET /user/delete` uses GET for mutation | Low | Low — deprecate, use `DELETE /user/{id}` instead |
| No account lockout after failed logins | Medium | Medium — track failed attempts per email, lock after N failures |
| No password complexity requirements | Low | Low — add validator in `UserCreate` (already has min_length=6) |
| No session invalidation on password change | Medium | Medium — track a `password_changed_at` timestamp, reject JWTs issued before it |

---

## Quick Start

Minimum changes for a production deploy:

```bash
# 1. Generate secrets
export JWT_SECRET_KEY=$(openssl rand -hex 32)
export DB_PASSWORD=$(openssl rand -hex 16)
export FGA_PRESHARED_KEY=$(openssl rand -hex 24)
export MINIO_ROOT_PASSWORD=$(openssl rand -hex 16)

# 2. Set production flags
export COOKIE_SECURE=true
export AUTH_RATE_LIMIT=10/minute
export CORS_ORIGINS=https://your-domain.com
export MINIO_SECURE=true

# 3. Bootstrap FGA
make fga-prod

# 4. Run with multiple workers behind a reverse proxy
make run-prod
```
