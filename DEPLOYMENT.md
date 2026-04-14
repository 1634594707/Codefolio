# Deployment Guide

This document focuses on production deployment for Codefolio.

## 1. Files You Need

- `backend/.env`
- `.env.production`
- `docker-compose.prod.yml`
- `docker-compose.postgres.yml` for PostgreSQL deployments

Templates:

- [backend/.env.example](/D:/Administrator/Desktop/Project/Codefolio/backend/.env.example)
- [.env.production.example](/D:/Administrator/Desktop/Project/Codefolio/.env.production.example)

## 2. Backend Secrets

Create `backend/.env` from the template and fill in at least:

```env
GITHUB_TOKEN=your_github_token
AI_API_KEY=your_ai_api_key
AI_API_BASE_URL=https://api.deepseek.com/v1
AI_MODEL=deepseek-chat
REDIS_URL=redis://redis:6379
DATABASE_PATH=/app/data/codefolio.db
```

Recommended:

- Use a dedicated GitHub token with the minimum scopes you need
- Use a production-grade AI key, not a development key
- Keep this file out of Git

PostgreSQL example:

```env
DATABASE_URL=postgresql://codefolio:change-me@postgres:5432/codefolio
DATABASE_PATH=
POSTGRES_POOL_MIN_SIZE=1
POSTGRES_POOL_MAX_SIZE=10
```

## 3. Public Runtime Variables

Create `.env.production` from the template:

```env
PUBLIC_HTTP_PORT=80
CORS_ORIGINS=https://your-domain.com
```

If you have multiple domains, separate them with commas.

## 4. Start Production

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

To run with PostgreSQL instead of SQLite:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml -f docker-compose.postgres.yml up -d --build
```

## 4.1 Migrate Existing SQLite Data to PostgreSQL

1. Keep the existing SQLite file available.
2. Bring up PostgreSQL once so the target database exists.
3. Run the migration script:

```bash
python backend/scripts/migrate_sqlite_to_postgres.py \
  --sqlite-path backend/data/codefolio.db \
  --postgres-url postgresql://codefolio:change-me@127.0.0.1:5432/codefolio
```

If you want to replace existing PostgreSQL data during migration:

```bash
python backend/scripts/migrate_sqlite_to_postgres.py \
  --sqlite-path backend/data/codefolio.db \
  --postgres-url postgresql://codefolio:change-me@127.0.0.1:5432/codefolio \
  --drop-existing
```

After the migration succeeds, switch production to the PostgreSQL compose override.

## 5. Health Checks

The production compose file includes health checks for:

- `redis`
- `backend` via `/api/health`
- `frontend` via `/healthz`

Useful commands:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml ps
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f
```

## 5.1 Backup and Restore

Create a PostgreSQL backup:

```bash
python backend/scripts/backup_postgres.py \
  --postgres-url postgresql://codefolio:change-me@127.0.0.1:5432/codefolio \
  --output backups/codefolio.dump
```

Restore a PostgreSQL backup:

```bash
python backend/scripts/restore_postgres.py \
  --postgres-url postgresql://codefolio:change-me@127.0.0.1:5432/codefolio \
  --input backups/codefolio.dump \
  --clean
```

These scripts depend on local PostgreSQL client tools:

- `pg_dump`
- `pg_restore`

## 6. Data Persistence

Docker volumes:

- `backend-data`: SQLite database and snapshot state
- `redis-data`: Redis persisted data
- `postgres-data`: PostgreSQL data when you enable the PostgreSQL override

Back up `backend-data` or `postgres-data` regularly depending on the backend you choose.

## 7. Reverse Proxy and HTTPS

The included frontend container serves HTTP only.

For internet-facing deployment, place one of these in front:

- Nginx
- Caddy
- Traefik
- Cloudflare Tunnel plus origin proxy

Minimum requirements:

- Enable HTTPS
- Forward traffic to the frontend container
- Preserve standard forwarded headers

Ready-to-adapt samples:

- [deploy/Caddyfile.example](/D:/Administrator/Desktop/Project/Codefolio/deploy/Caddyfile.example)
- [deploy/nginx.codefolio.conf](/D:/Administrator/Desktop/Project/Codefolio/deploy/nginx.codefolio.conf)

### Caddy rollout steps

1. Point your domain DNS record to the server IP.
2. Start Codefolio on `127.0.0.1:8080` or keep Docker publishing only locally.
3. Copy `deploy/Caddyfile.example` into your real Caddy config.
4. Replace `your-domain.com` with the real domain.
5. Reload Caddy and let it provision HTTPS automatically.

### Nginx rollout steps

1. Point your domain DNS record to the server IP.
2. Obtain certificates with Let's Encrypt or your existing PKI.
3. Copy `deploy/nginx.codefolio.conf` into `/etc/nginx/sites-available/`.
4. Replace `your-domain.com` and certificate paths.
5. Enable the site and reload Nginx.
6. Confirm HTTPS traffic reaches the frontend on `127.0.0.1:8080`.

## 8. Recommended Next Step

If you expect multiple users or long-term growth, the next production upgrade should be:

1. Move durable storage from SQLite to PostgreSQL
2. Add user accounts or tenant identities on top of the current workspace isolation model
3. Add centralized logs and metrics
