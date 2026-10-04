import sqlite3
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import database_path

EXAMPLES = Path(__file__).resolve().parents[2] / 'exemplos'

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('FINANCEIRO_DATA_DIR', str(tmp_path))
    with TestClient(app, base_url='http://127.0.0.1:8765') as c:
        yield c

def load(client, raw=None):
    return client.post('/api/imports', files={'file': ('exemplo.ofx', raw or (EXAMPLES/'conta-exemplo.ofx').read_bytes())})

def test_balances_are_dated_and_reimport_is_idempotent(client):
    assert load(client).status_code == 201
    data = client.get('/api/manage/balances').json()
    assert data['total_ledger_cents'] == 429598
    assert data['accounts'][0]['ledger']['as_of'] == '2026-09-15'
    assert data['accounts'][0]['available'] is None
    load(client)
    assert len(client.get('/api/manage/balances').json()['history']) == 1

def test_older_balance_does_not_replace_latest_and_zero_is_valid(client):
    load(client)
    data = client.get('/api/manage/balances').json()
    key = data['accounts'][0]['account_key']
    for date,value in [('2026-08-01',99),('2026-09-17',0)]:
        assert client.post('/api/manage/balances', json={'account_key': key,'date':date,'amount_cents':value}).status_code == 201
    result = client.get('/api/manage/balances').json()
    assert result['total_ledger_cents'] == 0
    assert len(result['history']) == 3

def test_trash_and_restore_do_not_silently_reimport(client):
    load(client)
    row = client.get('/api/transactions').json()[0]
    assert client.delete(f'/api/transactions/{row["id"]}').status_code == 200
    assert len(client.get('/api/manage/trash').json()) == 1
    load(client)
    assert len(client.get('/api/transactions').json()) == 18
    assert client.post(f'/api/manage/trash/{row["id"]}/restore', json={}).status_code == 200
    assert len(client.get('/api/transactions').json()) == 19

def test_clear_requires_confirmation_and_makes_recoverable_backup(client):
    load(client)
    assert client.post('/api/manage/clear',json={'scope':'transactions','confirmation':'wrong'}).status_code == 400
    result = client.post('/api/manage/clear',json={'scope':'transactions','confirmation':'APAGAR'})
    assert result.status_code == 200
    with sqlite3.connect(database_path().parent/'backups'/result.json()['backup']) as backup:
        assert backup.execute('SELECT count(*) FROM transactions').fetchone()[0] == 19
    assert client.get('/api/transactions').json() == []
    assert client.get('/api/imports').json() == []
    assert load(client).json()['new'] == 19

def test_backup_failure_aborts_clear(client, monkeypatch):
    load(client)
    def fail(db): raise OSError('Falha simulada de backup')
    monkeypatch.setattr('app.management.backup_before_change',fail)
    assert client.post('/api/manage/clear',json={'scope':'everything','confirmation':'APAGAR'}).status_code == 503
    assert len(client.get('/api/transactions').json()) == 19

def test_clear_all_empties_notes_and_accounts(client):
    client.post('/api/demo',json={})
    assert client.post('/api/manage/clear',json={'scope':'everything','confirmation':'APAGAR'}).status_code == 200
    assert client.get('/api/receipts').json() == []
    assert client.get('/api/manage/balances').json()['accounts'] == []
    assert client.post('/api/demo',json={}).status_code == 201

def test_balance_only_ofx_is_supported(client):
    import re
    raw = re.sub(rb'<STMTTRN>.*?</STMTTRN>',b'',(EXAMPLES/'conta-exemplo.ofx').read_bytes(),flags=re.S)
    assert load(client,raw).status_code == 201
    assert client.get('/api/manage/balances').json()['total_ledger_cents'] == 429598
    with sqlite3.connect(database_path()) as db:
        assert db.execute('SELECT original FROM imports').fetchone()[0] == raw

def test_manual_balance_can_correct_back_to_an_earlier_value(client):
    load(client)
    key = client.get('/api/manage/balances').json()['accounts'][0]['account_key']
    for value in (100, 200, 100):
        assert client.post('/api/manage/balances',json={'account_key':key,'date':'2026-09-17','amount_cents':value}).status_code == 201
    assert client.get('/api/manage/balances').json()['total_ledger_cents'] == 100

def test_available_and_card_balances_are_not_added_to_account_total(client):
    load(client)
    key = client.get('/api/manage/balances').json()['accounts'][0]['account_key']
    client.post('/api/manage/balances',json={'account_key':key,'date':'2026-09-17','amount_cents':500000,'balance_type':'available'})
    raw = (EXAMPLES/'cartao-exemplo.ofx').read_bytes().replace(b'</CCSTMTRS>', b'<LEDGERBAL><BALAMT>-200.00</BALAMT><DTASOF>20260917</DTASOF></LEDGERBAL></CCSTMTRS>')
    assert load(client,raw).status_code == 201
    result = client.get('/api/manage/balances').json()
    assert result['total_ledger_cents'] == 429598
    assert next(a for a in result['accounts'] if a['origin']=='Cartão')['ledger']['amount_cents'] == -20000
    assert next(a for a in result['accounts'] if a['origin']=='Conta')['available']['amount_cents'] == 500000

def test_migration_from_stage_one_preserves_transactions(tmp_path, monkeypatch):
    monkeypatch.setenv('FINANCEIRO_DATA_DIR',str(tmp_path))
    schema = Path(__file__).resolve().parents[1]/'app'/'schema.sql'
    with sqlite3.connect(database_path()) as db:
        db.executescript(schema.read_text())
        db.execute("INSERT INTO transactions(account_key,bank,origin,fingerprint,date,description,original_description,amount_cents,kind) VALUES('a','Demo','Manual','f','2026-09-01','Existente','Existente',-100,'expense')")
    with TestClient(app,base_url='http://127.0.0.1:8765') as client:
        assert client.get('/api/transactions').json()[0]['description']=='Existente'
        assert client.get('/api/manage/balances').status_code==200
