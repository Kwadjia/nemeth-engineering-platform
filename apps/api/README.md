# nemeth-api

FastAPI backend of the NEMETH Engineering Platform. See the repository
[README](../../README.md) and [`docs/`](../../docs/) for architecture and
setup; this file covers only what is specific to the Python package.

```
nemeth/
  core/        settings, db, logging, errors, auth boundary, identifiers,
               lifecycle, storage, pagination, lookup, audit
  modules/     products · components · bom · system   (models, schemas, service, router)
  seed/        N1 placeholder seed
  models.py    imports every model so Base.metadata is complete
  main.py      create_app()
  __main__.py  CLI: db upgrade | seed | openapi | serve
alembic/       migrations (0001_core_plm)
tests/         pytest against PostgreSQL (nemeth_test)
```

```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows; use bin/activate elsewhere
pip install -e ".[dev]"
python -m nemeth db upgrade
python -m nemeth seed
python -m nemeth serve
pytest
ruff check . && black --check . && mypy nemeth
```
