# Local Setup

Two supported ways to run the platform: natively with the database in
Docker (fastest feedback loop), or everything in Docker Compose.

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Docker Desktop | 24+ | PostgreSQL runs here in both modes |
| Python | 3.11+ | `python --version` |
| Node.js | 20+ | ships with npm; no other package manager needed |
| Git | any | |

## 1. Environment file

```bash
cp .env.example .env
```

Every setting has a working default for local development. The API reads
`NEMETH_*` variables (see `apps/api/nemeth/core/config.py`); Compose reads
the `POSTGRES_*` ones.

## 2. Database

```bash
docker compose up -d db
```

Creates `nemeth` and `nemeth_test` databases on `localhost:5432`
(user/password `nemeth`/`nemeth`). Data persists in the `pgdata` volume.
`docker compose down -v` wipes it.

## 3. API (native)

```bash
cd apps/api
python -m venv .venv
. .venv/Scripts/activate            # Windows (Git Bash / PowerShell: .venv\Scripts\Activate.ps1)
# source .venv/bin/activate         # macOS / Linux
pip install -e ".[dev]"

python -m nemeth db upgrade         # alembic upgrade head
python -m nemeth seed               # N1 placeholder data; safe to re-run
python -m nemeth serve              # uvicorn with reload on :8000
```

* Interactive docs: <http://localhost:8000/api/v1/docs>
* Health: <http://localhost:8000/api/v1/health>

Other CLI commands: `python -m nemeth db revision -m "message"`
(autogenerate a migration — review it), `python -m nemeth db current`,
`python -m nemeth db check` (fails when models and the migrated schema
differ), `python -m nemeth openapi --out file.json`.

## 4. Web (native)

From the repository root:

```bash
npm install
npm run dev                          # Vite on :5173, proxies /api → :8000
```

`VITE_API_PROXY_TARGET` in `.env` changes the proxy target.

## 5. Everything in Docker Compose

```bash
docker compose up
```

* `db` — PostgreSQL 16
* `api` — builds `apps/api/Dockerfile`, runs `python -m nemeth db upgrade`
  then uvicorn with reload; `apps/api` and `storage/` are bind-mounted
* `web` — `node:22-alpine`, installs workspace dependencies into named
  volumes, runs the Vite dev server

Seed inside the container: `docker compose exec api python -m nemeth seed`.

The first `web` start takes a minute while npm installs into the volume.
On Windows the bind mount is slower than native; native mode is
recommended for day-to-day work.

## Tests and quality gates

```bash
# API (database container must be running)
cd apps/api
pytest                               # drops + migrates nemeth_test, then runs the suite
ruff check . && black --check . && mypy nemeth

# Web (repository root)
npm run typecheck
npm run lint
npm run test
npm run build
npm run format:check
```

The API test session rebuilds `nemeth_test` from the Alembic migrations,
so a migration that no longer matches the models fails the suite.

## Regenerating API types for the frontend

After any change to a Pydantic schema or router:

```bash
npm run api:types
```

This exports `packages/domain-types/openapi.json` from the API and
compiles it to `packages/domain-types/src/api.d.ts`. Commit both.

## Troubleshooting

* **`connection refused` on 5432** — the `db` container is not up or is
  still starting; `docker compose ps` and `docker compose logs db`.
* **`database "nemeth_test" does not exist`** — the volume was created by
  an older Compose file. Either `docker compose down -v && docker compose up -d db`
  or create it manually: `docker compose exec db psql -U nemeth -c 'CREATE DATABASE nemeth_test'`.
  The test fixture also creates it when it can.
* **Port 5173 in use** — Vite is configured with `strictPort`; stop the other process.
* **Types out of date** — `npm run api:types`.
