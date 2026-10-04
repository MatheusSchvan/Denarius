BEGIN;
CREATE TABLE imports (
    id INTEGER PRIMARY KEY,
    filename TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    bank TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    added INTEGER NOT NULL DEFAULT 0,
    duplicates INTEGER NOT NULL DEFAULT 0,
    pending INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    original BLOB,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX imports_hash ON imports(file_hash);

CREATE TABLE transactions (
    id INTEGER PRIMARY KEY,
    account_key TEXT NOT NULL,
    bank TEXT NOT NULL,
    origin TEXT NOT NULL CHECK(origin IN ('Conta','Cartão','Manual')),
    fitid TEXT,
    fingerprint TEXT NOT NULL,
    date TEXT NOT NULL,
    description TEXT NOT NULL,
    original_description TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('income','expense','transfer','investment','adjustment')),
    category TEXT NOT NULL DEFAULT 'Não classificado',
    notes TEXT NOT NULL DEFAULT '',
    pending_duplicate INTEGER NOT NULL DEFAULT 0 CHECK(pending_duplicate IN (0,1)),
    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
    import_id INTEGER REFERENCES imports(id),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE UNIQUE INDEX transactions_identity ON transactions(account_key, fitid) WHERE fitid IS NOT NULL;
CREATE INDEX transactions_fingerprint ON transactions(fingerprint);
CREATE INDEX transactions_date ON transactions(date);

CREATE TABLE receipts (
    id INTEGER PRIMARY KEY,
    access_key TEXT UNIQUE,
    file_hash TEXT UNIQUE,
    filename TEXT,
    original BLOB,
    merchant TEXT NOT NULL,
    date TEXT NOT NULL,
    total_cents INTEGER NOT NULL CHECK(total_cents > 0),
    transaction_id INTEGER UNIQUE REFERENCES transactions(id),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE TABLE receipt_items (
    id INTEGER PRIMARY KEY,
    receipt_id INTEGER NOT NULL REFERENCES receipts(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    quantity TEXT NOT NULL,
    unit TEXT NOT NULL,
    unit_price_cents INTEGER NOT NULL,
    total_cents INTEGER NOT NULL,
    category TEXT NOT NULL DEFAULT 'Não classificado'
);
PRAGMA user_version = 1;
COMMIT;

