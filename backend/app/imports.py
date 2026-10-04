from collections import Counter
from pathlib import PurePath

from .domain import digest
from .ofx import parse_ofx


def plan_import(db, raw: bytes) -> dict:
    parsed = parse_ofx(raw)
    file_hash = digest(raw)
    repeated = db.execute("SELECT id FROM imports WHERE file_hash=? AND status='importado'", (file_hash,)).fetchone()
    seen_ids = {}
    fingerprints = Counter()
    missing_id_fingerprints = set()
    rows = []
    for row in parsed["rows"]:
        row = row.copy()
        key = (row["account_key"], row["fitid"])
        existing = None
        if row["fitid"]:
            existing = seen_ids.get(key)
            if existing is None:
                existing = db.execute("SELECT fingerprint FROM transactions WHERE account_key=? AND fitid=?", key).fetchone()
        if existing and existing["fingerprint"] != row["fingerprint"]:
            raise ValueError("Um identificador bancário aparece com data, valor ou descrição diferente. Confira o extrato; nada foi importado.")
        if repeated or existing:
            row["action"] = "duplicate"
        elif not row["fitid"] and (fingerprints[row["fingerprint"]] or db.execute("SELECT 1 FROM transactions WHERE fingerprint=?", (row["fingerprint"],)).fetchone()):
            row["action"] = "review"
        elif row["fitid"] and (row["fingerprint"] in missing_id_fingerprints or db.execute("SELECT 1 FROM transactions WHERE fingerprint=? AND fitid IS NULL", (row["fingerprint"],)).fetchone()):
            row["action"] = "review"
        else:
            row["action"] = "new"
        fingerprints[row["fingerprint"]] += 1
        if row["fitid"]:
            seen_ids[key] = row
        else:
            missing_id_fingerprints.add(row["fingerprint"])
        rows.append(row)
    counts = Counter(row["action"] for row in rows)
    return {"bank": parsed["bank"], "rows": rows, "total": len(rows), "new": counts["new"],
            "duplicates": counts["duplicate"], "pending": counts["review"], "file_hash": file_hash}


def import_ofx(db, raw: bytes, filename: str) -> dict:
    plan = plan_import(db, raw)
    parsed = parse_ofx(raw)
    keep_original = bool(plan["new"] or plan["pending"] or (
        parsed["balances"] and not db.execute(
            "SELECT 1 FROM imports WHERE file_hash=? AND original IS NOT NULL", (plan["file_hash"],)
        ).fetchone()
    ))
    for account in parsed["accounts"]:
        db.execute("INSERT OR IGNORE INTO accounts VALUES(?,?,?,?)", tuple(account[k] for k in ("account_key", "bank", "origin", "label")))
    for balance in parsed["balances"]:
        db.execute("INSERT OR IGNORE INTO balance_snapshots(account_key,as_of,balance_type,amount_cents,source) VALUES(?,?,?,?,?)",
                   (*[balance[k] for k in ("account_key", "as_of", "balance_type", "amount_cents")], "OFX"))
    cursor = db.execute(
        "INSERT INTO imports(filename,file_hash,bank,row_count,added,duplicates,pending,status,original) VALUES(?,?,?,?,?,?,?,?,?)",
        (PurePath(filename.replace('\\', '/')).name[:200], plan["file_hash"], plan["bank"], plan["total"],
         plan["new"], plan["duplicates"], plan["pending"], "importado", raw if keep_original else None),
    )
    for row in plan["rows"]:
        if row["action"] == "duplicate":
            continue
        db.execute(
            """INSERT INTO transactions(account_key,bank,origin,fitid,fingerprint,date,description,
               original_description,amount_cents,kind,category,pending_duplicate,import_id)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (row["account_key"], row["bank"], row["origin"], row["fitid"], row["fingerprint"], row["date"],
             row["description"], row["description"], row["amount_cents"], row["kind"], row["category"],
             int(row["action"] == "review"), cursor.lastrowid),
        )
    return {key: value for key, value in plan.items() if key not in ("rows", "file_hash")}
