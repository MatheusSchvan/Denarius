BEGIN;
CREATE TABLE accounts (
    account_key TEXT PRIMARY KEY,
    bank TEXT NOT NULL,
    origin TEXT NOT NULL,
    label TEXT NOT NULL
);
CREATE TABLE balance_snapshots (
    id INTEGER PRIMARY KEY,
    account_key TEXT NOT NULL REFERENCES accounts(account_key),
    as_of TEXT NOT NULL,
    balance_type TEXT NOT NULL CHECK(balance_type IN ('ledger','available')),
    amount_cents INTEGER NOT NULL,
    source TEXT NOT NULL
);
CREATE UNIQUE INDEX unique_ofx_balance
ON balance_snapshots(account_key,as_of,balance_type,amount_cents)
WHERE source='OFX';
PRAGMA user_version=2;
COMMIT;
