import csv
import base64
import binascii
import io
import logging
import os
import re
import secrets
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import date
from pathlib import PurePath
from typing import Literal

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, field_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .db import PROJECT_DIR, connection, initialize
from .domain import CATEGORIES, digest, iso_date
from .imports import import_ofx, plan_import
from .receipts import parse_receipt

MAX_FILE = 5 * 1024 * 1024
Kind = Literal['income', 'expense', 'transfer', 'investment', 'adjustment']


@asynccontextmanager
async def lifespan(app):
    initialize()
    if os.getenv("FINANCEIRO_DEMO_MODE") == "1":
        password = os.getenv("FINANCEIRO_DEMO_PASSWORD", "")
        host = os.getenv("RENDER_EXTERNAL_HOSTNAME", "")
        if len(password) < 14 or not host or not re.fullmatch(r"[A-Za-z0-9.-]+", host):
            raise RuntimeError("O modo de demonstração precisa de FINANCEIRO_DEMO_PASSWORD (14+ caracteres) e RENDER_EXTERNAL_HOSTNAME.")
        with connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if not db.execute("SELECT 1 FROM transactions LIMIT 1").fetchone() and not db.execute("SELECT 1 FROM receipts LIMIT 1").fetchone():
                seed_demo(db)
    yield


app = FastAPI(title="Financeiro pessoal", version="0.3.0", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url="/api/openapi.json")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", os.getenv("RENDER_EXTERNAL_HOSTNAME", "localhost")])


def demo_authenticated(header: str | None) -> bool:
    if not header or len(header) > 2048 or not header.startswith("Basic "):
        return False
    try:
        raw = base64.b64decode(header[6:], validate=True).decode("utf-8")
    except (UnicodeError, ValueError, binascii.Error):
        return False
    user, separator, password = raw.partition(":")
    return bool(separator) and secrets.compare_digest(user, os.getenv("FINANCEIRO_DEMO_USER", "demo")) and secrets.compare_digest(password, os.environ["FINANCEIRO_DEMO_PASSWORD"])


@app.middleware("http")
async def local_request(request: Request, call_next):
    public_demo = os.getenv("FINANCEIRO_DEMO_MODE") == "1"
    if public_demo and request.url.path != "/api/health" and not demo_authenticated(request.headers.get("authorization")):
        return JSONResponse({"detail": "Acesso à demonstração restrito."}, status_code=401,
                            headers={"WWW-Authenticate": 'Basic realm="Financeiro Demo", charset="UTF-8"', "Cache-Control": "no-store"})
    origin = request.headers.get("origin")
    allowed = {"http://127.0.0.1:8765", "http://localhost:8765", "http://127.0.0.1:5173", "http://localhost:5173"}
    if public_demo:
        host = os.environ["RENDER_EXTERNAL_HOSTNAME"]
        allowed = {"https://" + host}
        if host == "localhost":
            allowed.add("http://localhost:10000")
        if request.method not in {"GET", "HEAD", "OPTIONS"} and origin not in allowed:
            return JSONResponse({"detail": "Origem da requisição não permitida."}, status_code=403)
    if origin and origin not in allowed:
        return JSONResponse({"detail": "Origem da requisição não permitida."}, status_code=403)
    length = request.headers.get("content-length", "0")
    if not length.isdigit() or int(length) > MAX_FILE + 64 * 1024:
        return JSONResponse({"detail": "O limite é de 5 MB por arquivo."}, status_code=413)
    if request.method in {"POST", "PATCH", "PUT"} and request.url.path.startswith("/api/") and "content-length" not in request.headers:
        return JSONResponse({"detail": "Informe o tamanho da requisição."}, status_code=411)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    return response


@app.exception_handler(ValueError)
async def bad_value(request, error):
    return JSONResponse({"detail": str(error)}, status_code=400)


@app.exception_handler(sqlite3.OperationalError)
async def database_error(request, error):
    logging.exception("Erro no banco local", exc_info=error)
    return JSONResponse({"detail": "Não foi possível acessar o banco local. Tente novamente e confira o espaço em disco."}, status_code=503)


def month_value(month: str | None):
    if month and (not re.fullmatch(r"\d{4}-\d{2}", month) or not 1 <= int(month[5:]) <= 12 or int(month[:4]) < 1):
        raise ValueError("Mês inválido.")
    return month


def get_transaction(db, transaction_id):
    row = db.execute("SELECT * FROM transactions WHERE id=? AND active=1", (transaction_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Lançamento não encontrado.")
    return row


def get_receipt(db, receipt_id):
    row = db.execute("SELECT id,merchant,date,total_cents,transaction_id,filename,access_key FROM receipts WHERE id=?", (receipt_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Nota não encontrada.")
    result = dict(row)
    result["items"] = [dict(r) for r in db.execute("SELECT * FROM receipt_items WHERE receipt_id=? ORDER BY id", (receipt_id,))]
    result["difference_cents"] = result["total_cents"] - sum(item["total_cents"] for item in result["items"])
    return result


async def uploaded(file: UploadFile, extension: str) -> bytes:
    try:
        if not (file.filename or "").lower().endswith(extension):
            raise ValueError(f"Selecione um arquivo {extension}.")
        raw = await file.read(MAX_FILE + 1)
        if len(raw) > MAX_FILE:
            raise HTTPException(413, "O limite é de 5 MB por arquivo.")
        if not raw:
            raise ValueError("O arquivo está vazio.")
        return raw
    finally:
        await file.close()


class ManualTransaction(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    date: str
    description: str = Field(min_length=1, max_length=500)
    bank: str = Field(default="Carteira", min_length=1, max_length=100)
    amount_cents: StrictInt = Field(gt=-10_000_000_000, lt=10_000_000_000)
    kind: Kind
    category: str = "Não classificado"
    notes: str = Field(default="", max_length=2000)

    @field_validator("date")
    @classmethod
    def valid_date(cls, value):
        return iso_date(value)

    @field_validator("category")
    @classmethod
    def valid_category(cls, value):
        if value not in CATEGORIES:
            raise ValueError("Categoria inválida.")
        return value


class TransactionEdit(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    category: str
    kind: Kind
    notes: str = Field(max_length=2000)
    pending_duplicate: StrictBool = False


class LinkReceipt(BaseModel):
    transaction_id: StrictInt = Field(gt=0)


class ItemEdit(BaseModel):
    category: str


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.3.0"}


@app.get("/api/bootstrap")
def bootstrap():
    with connection() as db:
        months = [r[0] for r in db.execute("SELECT DISTINCT substr(date,1,7) FROM transactions WHERE active=1 ORDER BY 1 DESC")]
        total = db.execute("SELECT count(*) FROM transactions WHERE active=1").fetchone()[0]
        return {"categories": CATEGORIES, "months": months, "transaction_count": total,
                "demo_mode": os.getenv("FINANCEIRO_DEMO_MODE") == "1",
                "banks": [r[0] for r in db.execute("SELECT DISTINCT bank FROM transactions WHERE active=1 ORDER BY bank")]}


@app.get("/api/transactions")
def transactions(month: str | None = None, search: str = Query("", max_length=200), category: str = "", bank: str = "", pending: bool = False):
    month_value(month)
    where, params = ["t.active=1"], []
    if month:
        where.append("substr(t.date,1,7)=?")
        params.append(month)
    if search:
        where.append("(t.description LIKE ? OR t.notes LIKE ?)")
        params.extend([f"%{search}%"] * 2)
    for column, value in (("category", category), ("bank", bank)):
        if value:
            where.append(f"t.{column}=?")
            params.append(value)
    if pending:
        where.append("(t.pending_duplicate=1 OR t.category='Não classificado')")
    with connection() as db:
        rows = db.execute(f"""SELECT t.*,r.id AS receipt_id FROM transactions t LEFT JOIN receipts r ON r.transaction_id=t.id
            WHERE {' AND '.join(where)} ORDER BY t.date DESC,t.id DESC""", params)
        return [dict(r) for r in rows]


@app.post("/api/transactions", status_code=201)
def create_transaction(body: ManualTransaction):
    if body.amount_cents == 0:
        raise ValueError("O valor deve ser diferente de zero.")
    if (body.kind == "expense" and body.amount_cents > 0) or (body.kind == "income" and body.amount_cents < 0):
        raise ValueError("O sinal do valor não corresponde ao tipo do lançamento.")
    with connection() as db:
        key = str(uuid.uuid4())
        cursor = db.execute("""INSERT INTO transactions(account_key,bank,origin,fingerprint,date,description,original_description,amount_cents,kind,category,notes)
            VALUES(?,?,'Manual',?,?,?,?,?,?,?,?)""", (key, body.bank, key, body.date, body.description, body.description, body.amount_cents, body.kind, body.category, body.notes))
        return {"id": cursor.lastrowid}


@app.patch("/api/transactions/{transaction_id}")
def edit_transaction(transaction_id: int, body: TransactionEdit):
    if body.category not in CATEGORIES:
        raise ValueError("Categoria inválida.")
    with connection() as db:
        row = get_transaction(db, transaction_id)
        if (body.kind == "expense" and row["amount_cents"] > 0) or (body.kind == "income" and row["amount_cents"] < 0):
            raise ValueError("Entrada exige valor positivo; despesa exige valor negativo.")
        linked = db.execute("SELECT id FROM receipts WHERE transaction_id=?", (transaction_id,)).fetchone()
        if linked and (body.kind != "expense" or body.pending_duplicate):
            raise ValueError("Desvincule a nota antes de alterar esse tipo de movimento.")
        db.execute("UPDATE transactions SET category=?,kind=?,notes=?,pending_duplicate=? WHERE id=?", (body.category, body.kind, body.notes, int(body.pending_duplicate), transaction_id))
    return {"ok": True}


@app.delete("/api/transactions/{transaction_id}")
def delete_transaction(transaction_id: int):
    with connection() as db:
        get_transaction(db, transaction_id)
        if db.execute("SELECT 1 FROM receipts WHERE transaction_id=?", (transaction_id,)).fetchone():
            raise ValueError("Desvincule a nota em Notas de compra antes de excluir esse lançamento.")
        db.execute("UPDATE transactions SET active=0 WHERE id=?", (transaction_id,))
    return {"ok": True}


@app.get("/api/summary")
def summary(month: str = Query(...)):
    month_value(month)
    with connection() as db:
        records = [dict(r) for r in db.execute("SELECT * FROM transactions WHERE active=1 AND substr(date,1,7)=?", (month,))]
        counted = [r for r in records if not r["pending_duplicate"]]
        income = sum(r["amount_cents"] for r in counted if r["kind"] == "income")
        expense = -sum(r["amount_cents"] for r in counted if r["kind"] == "expense")
        grouped = {}
        for row in counted:
            if row["kind"] == "expense":
                grouped[row["category"]] = grouped.get(row["category"], 0) - row["amount_cents"]
        categories = [{"category": k, "amount_cents": v} for k, v in sorted(grouped.items(), key=lambda x: -x[1])]
        unlinked = db.execute("SELECT count(*) FROM receipts WHERE transaction_id IS NULL").fetchone()[0]
        trend = [dict(r) for r in db.execute("""SELECT substr(date,1,7) AS month,
            sum(CASE WHEN kind='income' THEN amount_cents ELSE 0 END) AS income,
            -sum(CASE WHEN kind='expense' THEN amount_cents ELSE 0 END) AS expense
            FROM transactions WHERE active=1 AND pending_duplicate=0 AND substr(date,1,7)<=?
            GROUP BY substr(date,1,7) ORDER BY month DESC LIMIT 6""", (month,))][::-1]
        return {"income_cents": income, "expense_cents": expense, "result_cents": income - expense,
                "count": len(records), "unclassified": sum(r["category"] == "Não classificado" for r in counted),
                "pending_duplicates": sum(r["pending_duplicate"] for r in records), "unlinked_receipts": unlinked,
                "excluded_count": sum(r["kind"] not in ("income", "expense") for r in counted),
                "categories": categories, "trend": trend}


@app.post("/api/imports/preview")
async def preview_ofx(file: UploadFile = File(...)):
    raw = await uploaded(file, ".ofx")
    with connection() as db:
        plan = plan_import(db, raw)
        return {**{k: v for k, v in plan.items() if k not in ("rows", "file_hash")}, "rows": plan["rows"][:100]}


@app.post("/api/imports", status_code=201)
async def create_import(file: UploadFile = File(...)):
    raw = await uploaded(file, ".ofx")
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        return import_ofx(db, raw, file.filename or "extrato.ofx")


@app.get("/api/imports")
def list_imports():
    with connection() as db:
        return [dict(r) for r in db.execute("SELECT id,filename,bank,row_count,added,duplicates,pending,status,created_at FROM imports ORDER BY id DESC LIMIT 100")]


def save_receipt(db, raw, filename):
    parsed = parse_receipt(raw)
    if db.execute("SELECT id FROM receipts WHERE file_hash=? OR (access_key IS NOT NULL AND access_key=?)", (digest(raw), parsed["access_key"])).fetchone():
        raise HTTPException(409, "Esta nota já está cadastrada.")
    cursor = db.execute("INSERT INTO receipts(access_key,file_hash,filename,original,merchant,date,total_cents) VALUES(?,?,?,?,?,?,?)",
                        (parsed["access_key"], digest(raw), PurePath(filename.replace('\\', '/')).name[:200], raw, parsed["merchant"], parsed["date"], parsed["total_cents"]))
    receipt_id = cursor.lastrowid
    for item in parsed["items"]:
        db.execute("INSERT INTO receipt_items(receipt_id,description,quantity,unit,unit_price_cents,total_cents,category) VALUES(?,?,?,?,?,?,?)",
                   (receipt_id, item["description"], item["quantity"], item["unit"], item["unit_price_cents"], item["total_cents"], item["category"]))
    return {"id": receipt_id}


@app.post("/api/receipts/preview")
async def preview_receipt(file: UploadFile = File(...)):
    return parse_receipt(await uploaded(file, ".xml"))


@app.post("/api/receipts", status_code=201)
async def create_receipt(file: UploadFile = File(...)):
    raw = await uploaded(file, ".xml")
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        return save_receipt(db, raw, file.filename or "nota.xml")


@app.get("/api/receipts")
def list_receipts():
    with connection() as db:
        return [dict(r) for r in db.execute("""SELECT r.id,r.merchant,r.date,r.total_cents,r.transaction_id,
            (SELECT count(*) FROM receipt_items i WHERE i.receipt_id=r.id) AS item_count,
            t.description AS transaction_description FROM receipts r LEFT JOIN transactions t ON t.id=r.transaction_id ORDER BY r.date DESC,r.id DESC""")]


@app.get("/api/receipts/{receipt_id}")
def receipt_detail(receipt_id: int):
    with connection() as db:
        receipt = get_receipt(db, receipt_id)
        receipt["candidates"] = [dict(r) for r in db.execute("""SELECT t.id,t.date,t.description,t.bank,t.amount_cents,
            abs(julianday(t.date)-julianday(?)) AS days_apart FROM transactions t
            LEFT JOIN receipts r ON r.transaction_id=t.id WHERE t.active=1 AND t.pending_duplicate=0
            AND t.kind='expense' AND t.amount_cents=? AND r.id IS NULL
            AND abs(julianday(t.date)-julianday(?))<=3 ORDER BY days_apart,t.id""", (receipt["date"], -receipt["total_cents"], receipt["date"]))]
        return receipt


@app.post("/api/receipts/{receipt_id}/link")
def link_receipt(receipt_id: int, body: LinkReceipt):
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        receipt = get_receipt(db, receipt_id)
        if receipt["transaction_id"]:
            raise HTTPException(409, "Esta nota já tem um vínculo. Desvincule antes de trocar.")
        if receipt["difference_cents"]:
            raise ValueError("A soma dos itens difere do total; este MVP só concilia notas com os totais fechados.")
        transaction = get_transaction(db, body.transaction_id)
        if transaction["kind"] != "expense" or transaction["pending_duplicate"]:
            raise ValueError("Selecione uma despesa confirmada.")
        if transaction["amount_cents"] != -receipt["total_cents"]:
            raise ValueError("O valor da compra deve ser igual ao total da nota.")
        if abs((date.fromisoformat(transaction["date"]) - date.fromisoformat(receipt["date"])).days) > 3:
            raise ValueError("Neste MVP, a compra deve estar a até três dias da nota.")
        if db.execute("SELECT id FROM receipts WHERE transaction_id=?", (body.transaction_id,)).fetchone():
            raise HTTPException(409, "Este lançamento já possui uma nota.")
        db.execute("UPDATE receipts SET transaction_id=? WHERE id=?", (body.transaction_id, receipt_id))
    return {"ok": True}


@app.delete("/api/receipts/{receipt_id}/link")
def unlink_receipt(receipt_id: int):
    with connection() as db:
        get_receipt(db, receipt_id)
        db.execute("UPDATE receipts SET transaction_id=NULL WHERE id=?", (receipt_id,))
    return {"ok": True}


@app.patch("/api/receipt-items/{item_id}")
def edit_item(item_id: int, body: ItemEdit):
    if body.category not in CATEGORIES:
        raise ValueError("Categoria inválida.")
    with connection() as db:
        if not db.execute("SELECT id FROM receipt_items WHERE id=?", (item_id,)).fetchone():
            raise HTTPException(404, "Item não encontrado.")
        db.execute("UPDATE receipt_items SET category=? WHERE id=?", (body.category, item_id))
    return {"ok": True}


@app.post("/api/demo", status_code=201)
def demo():
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT count(*) FROM transactions").fetchone()[0] or db.execute("SELECT count(*) FROM receipts").fetchone()[0]:
            raise HTTPException(409, "Use os exemplos apenas em uma base vazia, para não misturar dados fictícios com seus dados.")
        seed_demo(db)
    return {"ok": True, "month": "2026-09"}


def seed_demo(db):
    for filename in ("conta-exemplo.ofx", "cartao-exemplo.ofx"):
        import_ofx(db, (PROJECT_DIR / "exemplos" / filename).read_bytes(), filename)
    save_receipt(db, (PROJECT_DIR / "exemplos" / "nota-mercado.xml").read_bytes(), "nota-mercado.xml")


@app.get("/api/export.csv")
def export_csv(month: str | None = None):
    month_value(month)
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Data", "Descrição", "Banco", "Origem", "Valor", "Categoria", "Tipo", "Revisar duplicidade", "Observação"])
    with connection() as db:
        for row in db.execute("SELECT * FROM transactions WHERE active=1 AND (? IS NULL OR substr(date,1,7)=?) ORDER BY date,id", (month, month)):
            safe = lambda value: "'" + value if value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else value
            amount = row["amount_cents"]
            formatted = f"{'-' if amount < 0 else ''}{abs(amount)//100},{abs(amount)%100:02}"
            writer.writerow([row["date"], safe(row["description"]), safe(row["bank"]), row["origin"], formatted, row["category"], row["kind"], "Sim" if row["pending_duplicate"] else "Não", safe(row["notes"])])
    filename = f"lancamentos-{month}.csv" if month else "lancamentos.csv"
    return Response(output.getvalue().encode("utf-8-sig"), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.get("/api/backup")
def backup():
    with connection() as db:
        snapshot = sqlite3.connect(":memory:")
        try:
            db.backup(snapshot)
            raw = snapshot.serialize()
        finally:
            snapshot.close()
    return Response(raw, media_type="application/vnd.sqlite3", headers={"Content-Disposition": f'attachment; filename="financeiro-{date.today().isoformat()}.sqlite3"'})


from .management import router as management_router
app.include_router(management_router)

assets = PROJECT_DIR / "frontend" / "dist"
if assets.is_dir():
    app.mount("/", StaticFiles(directory=assets, html=True), name="frontend")
