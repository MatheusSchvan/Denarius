import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]


def database_path() -> Path:
    folder = Path(os.environ.get("FINANCEIRO_DATA_DIR", PROJECT_DIR / "data"))
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "financeiro.sqlite3"


@contextmanager
def connection():
    db = sqlite3.connect(database_path(), timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def initialize():
    with connection() as db:
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version > 2:
            raise RuntimeError("Este banco pertence a uma versão mais nova do aplicativo.")
        if version == 0:
            schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
            db.executescript(schema)
        if version < 2:
            db.executescript(Path(__file__).with_name("migration_002.sql").read_text(encoding="utf-8"))
