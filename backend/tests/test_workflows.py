import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import connection, database_path
from app.main import app
from app.ofx import parse_ofx
from app.receipts import parse_receipt

EXAMPLES = Path(__file__).resolve().parents[2] / "exemplos"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCEIRO_DATA_DIR", str(tmp_path))
    with TestClient(app, base_url="http://127.0.0.1:8765") as client:
        yield client


def ofx_upload(client, name="conta-exemplo.ofx", raw=None, path="/api/imports"):
    return client.post(path, files={"file": (name, raw if raw is not None else (EXAMPLES / name).read_bytes(), "application/octet-stream")})


def expense(client, value=-25291, day="2026-09-09"):
    response = client.post("/api/transactions", json={"date": day, "description": "Mercado de teste", "amount_cents": value, "kind": "expense", "category": "Mercado"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def receipt(client):
    response = client.post("/api/receipts", files={"file": ("nota.xml", (EXAMPLES / "nota-mercado.xml").read_bytes())})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def summary(client):
    return client.get("/api/summary?month=2026-09").json()


def test_preview_does_not_write_and_reimport_is_idempotent(client):
    preview = ofx_upload(client, path="/api/imports/preview")
    assert preview.status_code == 200
    assert client.get("/api/transactions").json() == []
    first = ofx_upload(client)
    assert first.status_code == 201, first.text
    assert first.json()["new"] == 19
    original = summary(client)
    second = ofx_upload(client, name="renomeado.ofx", raw=(EXAMPLES / "conta-exemplo.ofx").read_bytes())
    assert second.json()["new"] == 0
    assert second.json()["duplicates"] == 19
    assert summary(client) == original
    assert len(client.get("/api/transactions").json()) == 19


def test_overlapping_ofx_only_adds_new_transactions(client):
    raw = (EXAMPLES / "conta-exemplo.ofx").read_bytes()
    ofx_upload(client, raw=raw)
    new = b'<STMTTRN><TRNTYPE>DEBIT\n<DTPOSTED>20260916\n<TRNAMT>-10.00\n<FITID>novo\n<MEMO>NOVA COMPRA\n</STMTTRN>'
    response = ofx_upload(client, raw=raw.replace(b'</BANKTRANLIST>', new + b'</BANKTRANLIST>'))
    assert response.json()["new"] == 1
    assert response.json()["duplicates"] == 19


def test_identity_is_scoped_to_account(client):
    raw = (EXAMPLES / "conta-exemplo.ofx").read_bytes()
    ofx_upload(client, raw=raw)
    response = ofx_upload(client, raw=raw.replace(b"DEMO0001", b"DEMO0002"))
    assert response.json()["new"] == 19


def test_conflicting_fitid_rejects_entire_file(client):
    raw = (EXAMPLES / "conta-exemplo.ofx").read_bytes()
    ofx_upload(client, raw=raw)
    before = summary(client)
    changed = raw.replace(b"<TRNAMT>-252.91", b"<TRNAMT>-999.00")
    response = ofx_upload(client, raw=changed)
    assert response.status_code == 400
    assert summary(client) == before
    assert len(client.get("/api/imports").json()) == 1


def test_missing_fitid_requires_review_without_inflating_summary(client):
    raw = (EXAMPLES / "conta-exemplo.ofx").read_bytes()
    raw = re.sub(rb"<FITID>[^<\n]+", b"", raw)
    assert ofx_upload(client, raw=raw).json()["new"] == 19
    before = summary(client)
    response = ofx_upload(client, raw=raw + b'\n')
    assert response.json()["pending"] == 19
    assert summary(client)["expense_cents"] == before["expense_cents"]
    pending = [r for r in client.get("/api/transactions").json() if r["pending_duplicate"]]
    chosen = pending[0]
    result = client.patch(f'/api/transactions/{chosen["id"]}', json={"kind": chosen["kind"], "category": chosen["category"], "notes": "Compra legítima confirmada", "pending_duplicate": False})
    assert result.status_code == 200
    assert client.delete(f'/api/transactions/{pending[1]["id"]}').status_code == 200
    assert len(client.get("/api/transactions").json()) == 37


def test_xml_card_and_sgml_bank_are_supported(client):
    assert ofx_upload(client).status_code == 201
    assert ofx_upload(client, "cartao-exemplo.ofx").status_code == 201
    rows = client.get("/api/transactions").json()
    assert {r["origin"] for r in rows} == {"Conta", "Cartão"}
    assert len(rows) == 24


def test_identified_record_after_missing_id_still_requires_review(client):
    raw = (EXAMPLES / "conta-exemplo.ofx").read_bytes()
    unidentified = re.sub(rb"<FITID>[^<\n]+", b"", raw)
    ofx_upload(client, raw=unidentified)
    original = summary(client)
    response = ofx_upload(client, raw=raw)
    assert response.json()["pending"] == 19
    assert summary(client)["expense_cents"] == original["expense_cents"]


def test_receipt_link_and_unlink_do_not_change_financial_total(client):
    assert client.post("/api/demo", json={}).status_code == 201
    before = summary(client)
    detail = client.get("/api/receipts/1").json()
    assert len(detail["items"]) == 12
    assert sum(r["total_cents"] for r in detail["items"]) == 25291
    assert len(detail["candidates"]) == 1
    candidate = detail["candidates"][0]["id"]
    assert client.post("/api/receipts/1/link", json={"transaction_id": candidate}).status_code == 200
    assert summary(client)["expense_cents"] == before["expense_cents"]
    assert summary(client)["result_cents"] == before["result_cents"]
    assert client.get("/api/receipts/1").json()["transaction_id"] == candidate
    assert client.delete("/api/receipts/1/link").status_code == 200
    assert summary(client)["expense_cents"] == before["expense_cents"]


def test_receipt_cannot_link_different_value_or_far_date(client):
    receipt_id = receipt(client)
    wrong_value = expense(client, value=-25290)
    wrong_date = expense(client, day="2026-09-20")
    for transaction_id in (wrong_value, wrong_date):
        assert client.post(f'/api/receipts/{receipt_id}/link', json={"transaction_id": transaction_id}).status_code == 400


def test_receipt_duplicate_and_one_receipt_per_transaction(client):
    transaction_id = expense(client)
    receipt_id = receipt(client)
    assert client.post(f'/api/receipts/{receipt_id}/link', json={"transaction_id": transaction_id}).status_code == 200
    duplicate = client.post("/api/receipts", files={"file": ("copia.xml", (EXAMPLES / "nota-mercado.xml").read_bytes())})
    assert duplicate.status_code == 409
    raw = (EXAMPLES / "nota-mercado.xml").read_bytes().replace(b"9"*44, b"8"*44)
    second = client.post("/api/receipts", files={"file": ("outra.xml", raw)})
    assert second.status_code == 201
    assert client.post(f'/api/receipts/{second.json()["id"]}/link', json={"transaction_id": transaction_id}).status_code == 409


def test_receipt_with_unbalanced_items_cannot_link(client):
    raw = (EXAMPLES / "nota-mercado.xml").read_bytes().replace(b"<vNF>252.91", b"<vNF>253.91")
    response = client.post("/api/receipts", files={"file": ("nota.xml", raw)})
    transaction_id = expense(client, value=-25391)
    assert client.post(f'/api/receipts/{response.json()["id"]}/link', json={"transaction_id": transaction_id}).status_code == 400


def test_transfer_classification_excludes_invoice_payment(client):
    transaction_id = expense(client, value=-12000)
    assert summary(client)["expense_cents"] == 12000
    response = client.patch(f'/api/transactions/{transaction_id}', json={"category": "Transferências", "kind": "transfer", "notes": "Pagamento da fatura", "pending_duplicate": False})
    assert response.status_code == 200
    assert summary(client)["expense_cents"] == 0
    assert len(client.get("/api/transactions").json()) == 1


def test_money_sign_and_date_validation(client):
    base = {"date": "2026-09-09", "description": "Teste", "amount_cents": -10, "kind": "expense"}
    for delta in ({"amount_cents": 10}, {"amount_cents": -10.5}, {"amount_cents": 0}, {"date": "2026-02-30"}, {"category": "<script>"}, {"description": " "}):
        assert client.post("/api/transactions", json={**base, **delta}).status_code in (400, 422)
    expense(client, value=-10)
    expense(client, value=-20)
    assert summary(client)["expense_cents"] == 30


def test_unsafe_xml_and_non_brl_ofx_are_rejected(client):
    xml = b'<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><NFe>&xxe;</NFe>'
    assert client.post("/api/receipts", files={"file": ("nota.xml", xml)}).status_code == 400
    raw = (EXAMPLES / "conta-exemplo.ofx").read_bytes().replace(b"<CURDEF>BRL", b"<CURDEF>USD")
    assert ofx_upload(client, raw=raw).status_code == 400
    assert len(client.get("/api/transactions").json()) == 0


def test_foreign_origin_and_host_are_blocked(client):
    assert client.post("/api/demo", json={}, headers={"Origin": "https://malicious.example"}).status_code == 403
    assert client.get("/api/transactions", headers={"Host": "malicious.example"}).status_code == 400


def test_backup_is_valid_and_contains_original_files(client, tmp_path):
    client.post("/api/demo", json={})
    response = client.get("/api/backup")
    assert response.status_code == 200
    target = tmp_path / 'snapshot.sqlite3'
    target.write_bytes(response.content)
    with sqlite3.connect(target) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert db.execute('SELECT count(*) FROM transactions').fetchone()[0] == 24
        assert db.execute('SELECT original FROM receipts').fetchone()[0] == (EXAMPLES / "nota-mercado.xml").read_bytes()


def test_simultaneous_imports_do_not_duplicate(client):
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: ofx_upload(client), range(2)))
    assert all(r.status_code == 201 for r in responses)
    assert sum(r.json()["new"] for r in responses) == 19


def test_csv_guards_formula_cells_and_demo_requires_empty_database(client):
    client.post("/api/transactions", json={"date": "2026-09-09", "description": "=1+1", "amount_cents": -123, "kind": "expense"})
    text = client.get('/api/export.csv').content.decode('utf-8-sig')
    assert "'=1+1" in text
    assert "-1,23" in text
    assert client.post("/api/demo", json={}).status_code == 409


def test_data_persists_across_connections(client):
    expense(client)
    with connection() as db:
        assert db.execute('SELECT amount_cents FROM transactions').fetchone()[0] == -25291
    assert database_path().is_file()


def test_monthly_csv_matches_active_month_and_keeps_all_months_export(client):
    import csv
    import io
    from decimal import Decimal
    client.post('/api/demo', json={})
    deleted = expense(client, value=-1000)
    client.delete(f'/api/transactions/{deleted}')
    exported = client.get('/api/export.csv?month=2026-09')
    assert exported.status_code == 200
    assert 'lancamentos-2026-09.csv' in exported.headers['content-disposition']
    rows = list(csv.DictReader(io.StringIO(exported.content.decode('utf-8-sig')), delimiter=';'))
    assert rows and all(r['Data'].startswith('2026-09') for r in rows)
    assert all(r['Descrição'] != 'Mercado de teste' for r in rows)
    expense_cents = -sum(int(Decimal(r['Valor'].replace(',', '.')) * 100) for r in rows if r['Tipo']=='expense' and r['Revisar duplicidade']=='Não')
    assert expense_cents == summary(client)['expense_cents']
    all_rows = list(csv.DictReader(io.StringIO(client.get('/api/export.csv').content.decode('utf-8-sig')), delimiter=';'))
    assert len(all_rows) == 24 and len(all_rows) > len(rows)
    assert client.get('/api/export.csv?month=2026-13').status_code == 400
    empty = client.get('/api/export.csv?month=2025-01')
    assert len(list(csv.reader(io.StringIO(empty.content.decode('utf-8-sig')), delimiter=';'))) == 1
