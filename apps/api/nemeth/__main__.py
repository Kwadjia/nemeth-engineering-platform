"""Command line entry point: ``python -m nemeth <command>``.

Commands
--------
db upgrade          Apply Alembic migrations to head.
db revision -m MSG  Autogenerate a migration (review it before committing).
db check            Fail if the models and the migrated schema differ.
seed                Load the NEMETH N1 placeholder data (idempotent).
openapi [--out]     Write the OpenAPI document (used to generate TypeScript types).
serve               Run the development server.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from alembic.config import Config as AlembicConfig

API_ROOT = Path(__file__).resolve().parent.parent


def _alembic_config() -> AlembicConfig:
    from alembic.config import Config as AlembicConfig

    config = AlembicConfig(str(API_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(API_ROOT / "alembic"))
    return config


def cmd_db(args: argparse.Namespace) -> int:
    from alembic import command

    config = _alembic_config()
    if args.db_command == "upgrade":
        command.upgrade(config, args.revision)
    elif args.db_command == "downgrade":
        command.downgrade(config, args.revision)
    elif args.db_command == "revision":
        command.revision(config, message=args.message, autogenerate=True)
    elif args.db_command == "current":
        command.current(config, verbose=True)
    elif args.db_command == "check":
        command.check(config)
    return 0


def cmd_seed(_: argparse.Namespace) -> int:
    from nemeth.core.db import get_sessionmaker
    from nemeth.seed.n1 import seed_n1

    with get_sessionmaker()() as session:
        result = seed_n1(session)
        session.commit()
    print(result.summary())
    return 0


def cmd_openapi(args: argparse.Namespace) -> int:
    from nemeth.main import create_app

    document = create_app().openapi()
    text = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(text)
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    uvicorn.run("nemeth.main:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nemeth", description="NEMETH Engineering Platform CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    db = sub.add_parser("db", help="database migrations")
    db_sub = db.add_subparsers(dest="db_command", required=True)
    up = db_sub.add_parser("upgrade")
    up.add_argument("revision", nargs="?", default="head")
    down = db_sub.add_parser("downgrade")
    down.add_argument("revision", nargs="?", default="-1")
    rev = db_sub.add_parser("revision")
    rev.add_argument("-m", "--message", required=True)
    db_sub.add_parser("current")
    db_sub.add_parser("check", help="fail if models and the migrated schema differ")
    db.set_defaults(func=cmd_db)

    seed = sub.add_parser("seed", help="load NEMETH N1 placeholder data")
    seed.set_defaults(func=cmd_seed)

    openapi = sub.add_parser("openapi", help="export the OpenAPI document")
    openapi.add_argument("--out", help="write to this path instead of stdout")
    openapi.set_defaults(func=cmd_openapi)

    serve = sub.add_parser("serve", help="run the development server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--no-reload", dest="reload", action="store_false")
    serve.set_defaults(func=cmd_serve)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
