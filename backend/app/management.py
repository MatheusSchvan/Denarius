"""Saldos e operações de manutenção da segunda etapa."""
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, StrictInt

from .db import connection, database_path
from .domain import iso_date

router = APIRouter(prefix="/api/manage")


def backup_before_change(db):
    # A trava de escrita já deve estar adquirida. Outra conexão faz a leitura
    # consistente do estado anterior, antes do commit da operação destrutiva.
    folder = database_path().parent / "backups"
    folder.mkdir(exist_ok=True)
    filename = f"antes-limpeza-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}.sqlite3"
    with sqlite3.connect(database_path()) as reader, sqlite3.connect(folder / filename) as target:
        reader.backup(target)
    return filename


@router.get("/balances")
def balances():
    with connection() as db:
        result = []
        for account in db.execute("SELECT * FROM accounts ORDER BY bank,label"):
            item = dict(account)
            for kind in ("ledger", "available"):
                row = db.execute("SELECT * FROM balance_snapshots WHERE account_key=? AND balance_type=? ORDER BY as_of DESC,id DESC LIMIT 1", (account["account_key"], kind)).fetchone()
                item[kind] = dict(row) if row else None
            result.append(item)
        return {"accounts": result,
                "total_ledger_cents": sum(item["ledger"]["amount_cents"] for item in result if item["origin"] == "Conta" and item["ledger"]),
                "account_count_with_ledger": sum(item["origin"] == "Conta" and item["ledger"] is not None for item in result),
                "history": [dict(r) for r in db.execute("SELECT b.*,a.label FROM balance_snapshots b JOIN accounts a USING(account_key) ORDER BY as_of DESC,b.id DESC LIMIT 100")]}


class ManualBalance(BaseModel):
    account_key: str
    date: str
    amount_cents: StrictInt = Field(ge=-10_000_000_000, le=10_000_000_000)
    balance_type: Literal["ledger", "available"] = "ledger"


@router.post("/balances", status_code=201)
def manual_balance(body: ManualBalance):
    iso_date(body.date)
    with connection() as db:
        if not db.execute("SELECT 1 FROM accounts WHERE account_key=?", (body.account_key,)).fetchone():
            raise HTTPException(404, "Importe um OFX dessa conta antes de informar o saldo.")
        db.execute("INSERT INTO balance_snapshots(account_key,as_of,balance_type,amount_cents,source) VALUES(?,?,?,?,?)",
                   (body.account_key, body.date, body.balance_type, body.amount_cents, "Manual"))
    return {"ok": True}


@router.get("/trash")
def trash():
    with connection() as db:
        return [dict(r) for r in db.execute("SELECT id,date,description,bank,amount_cents FROM transactions WHERE active=0 ORDER BY id DESC")]


@router.post("/trash/{transaction_id}/restore")
def restore(transaction_id: int):
    with connection() as db:
        if not db.execute("SELECT id FROM transactions WHERE id=? AND active=0", (transaction_id,)).fetchone():
            raise HTTPException(404, "Lançamento não encontrado na lixeira.")
        db.execute("UPDATE transactions SET active=1 WHERE id=?", (transaction_id,))
    return {"ok": True}


class ClearBody(BaseModel):
    confirmation: str
    scope: Literal["transactions", "everything"]


@router.post("/clear")
def clear(body: ClearBody):
    if body.confirmation != "APAGAR":
        raise ValueError("Digite APAGAR para confirmar.")
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        try:
            backup = backup_before_change(db)
        except (OSError, sqlite3.Error) as error:
            raise HTTPException(503, "Não foi possível criar o backup. Nenhum dado foi apagado; confira o espaço em disco e as permissões da pasta de dados.") from error
        if body.scope == "transactions":
            # Apagar todos aqui é limpeza efetiva: permite reimportar o mesmo OFX.
            # As notas são preservadas, mas precisam ser vinculadas novamente.
            db.execute("UPDATE receipts SET transaction_id=NULL")
            db.execute("DELETE FROM transactions")
            db.execute("DELETE FROM imports")
        else:
            db.execute("DELETE FROM receipt_items")
            db.execute("DELETE FROM receipts")
            db.execute("DELETE FROM transactions")
            db.execute("DELETE FROM imports")
            db.execute("DELETE FROM balance_snapshots")
            db.execute("DELETE FROM accounts")
    return {"ok": True, "backup": backup}
