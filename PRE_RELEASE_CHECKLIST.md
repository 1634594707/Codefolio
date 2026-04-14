# Pre-Release Checklist

## Configuration

- `backend/.env` exists and is not committed
- `.env.production` exists and is not committed
- `GITHUB_TOKEN` is valid
- `AI_API_KEY` is valid
- `CORS_ORIGINS` only includes real production domains
- `DATABASE_URL` and pool settings match the intended production backend

## Database

- SQLite source file has been backed up before migration
- PostgreSQL target database is reachable
- SQLite to PostgreSQL migration has been executed
- PostgreSQL row counts are checked after migration
- A fresh PostgreSQL backup dump has been created
- A restore test has been executed against a separate verification database
- Rollback path to SQLite has been tested or documented for this release

## Docker

- `docker compose --env-file .env.production -f docker-compose.prod.yml config` passes
- `docker compose --env-file .env.production -f docker-compose.prod.yml -f docker-compose.postgres.yml config` passes when using PostgreSQL
- Image build succeeds in the real deployment environment
- Backend health endpoint returns healthy
- Frontend `/healthz` returns `ok`
- Redis health check passes

## Reverse Proxy and HTTPS

- Domain DNS points to the correct server
- HTTPS certificates are valid
- Reverse proxy forwards `Host` and `X-Forwarded-*` headers
- HTTP traffic is redirected to HTTPS
- Browser opens the production domain without certificate warnings

## Product Checks

- `/api/health` responds successfully
- Developer profile generation works
- Repository benchmark works
- Export page still works
- Workspace isolation still works across separate browsers or sessions
- Cache invalidation endpoints still behave as expected

## Operations

- Backup retention path is defined
- Monitoring/log access is available
- Disk space is sufficient for PostgreSQL, Redis, and Docker images
- Rollback owner and rollback window are agreed before release
