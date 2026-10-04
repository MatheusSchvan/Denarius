"""Leitura do subconjunto OFX de conta/cartão usado no MVP (SGML 1.x e XML 2.x)."""
import re
from datetime import datetime
from html import unescape

from .domain import cents, classify, digest, normalize


def field(text: str, name: str, default: str = "") -> str:
    match = re.search(rf"<{name}(?:\s[^>]*)?>\s*([^<]*)", text, re.I)
    return unescape(match.group(1).strip()) if match else default


def decode(raw: bytes) -> str:
    if b"\x00" in raw:
        raise ValueError("OFX UTF-16 ou arquivo binário não é suportado neste MVP.")
    header = raw[:1024].decode("ascii", "ignore")
    declared = re.search(r'(?:encoding=["\']|CHARSET:\s*)([\w-]+)', header, re.I)
    encoding = declared.group(1).lower() if declared else ""
    mapping = {"1252": "cp1252", "windows-1252": "cp1252", "8859-1": "iso-8859-1", "iso-8859-1": "iso-8859-1"}
    if encoding in mapping:
        return raw.decode(mapping[encoding])
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252")


def parse_ofx(raw: bytes) -> dict:
    try:
        text = decode(raw)
    except UnicodeError:
        raise ValueError("Não foi possível ler a codificação do OFX.") from None
    if not re.search(r"<OFX\s*>", text, re.I) or not re.search(r"</OFX\s*>", text, re.I):
        raise ValueError("Arquivo OFX inválido ou incompleto.")
    if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
        raise ValueError("Declarações externas não são permitidas.")
    if re.search(r"<(CORRECTFITID|CORRECTACTION|INVSTMTRS)>", text, re.I):
        raise ValueError("OFX com correções bancárias ou investimentos requer um adaptador próprio; nada foi importado.")
    statements = re.findall(r"<(STMTRS|CCSTMTRS)>(.*?)</\1>", text, re.I | re.S)
    if not statements:
        raise ValueError("Não encontrei extrato de conta ou cartão neste OFX.")
    org = field(text, "ORG")
    fid = field(text, "FID")
    rows, banks, accounts, balances = [], set(), [], []
    for tag, statement in statements:
        if field(statement, "CURDEF").upper() != "BRL":
            raise ValueError("Esta versão aceita apenas extratos em reais (BRL).")
        origin = "Cartão" if tag.upper() == "CCSTMTRS" else "Conta"
        bank_id = field(statement, "BANKID") or fid or org
        account_id = field(statement, "ACCTID")
        branch_id = field(statement, "BRANCHID")
        if not bank_id or not account_id:
            raise ValueError("O OFX precisa identificar banco e conta/cartão para evitar duplicatas.")
        known = {"756": "Sicoob", "001": "Banco do Brasil", "341": "Itaú", "237": "Bradesco", "104": "Caixa", "260": "Nubank", "748": "Sicredi"}
        bank = org or known.get(bank_id.zfill(3), f"Banco {bank_id}")
        banks.add(bank)
        account_key = digest(f"{normalize(bank_id)}|{origin}|{branch_id}|{account_id}")
        accounts.append({"account_key": account_key, "bank": bank, "origin": origin,
                         "label": f"{bank} · {origin} · final {account_id[-4:]}"})
        for balance_tag, balance_type in (("LEDGERBAL", "ledger"), ("AVAILBAL", "available")):
            section = re.search(rf"<{balance_tag}>(.*?)</{balance_tag}>", statement, re.I | re.S)
            if section:
                try:
                    as_of = datetime.strptime(field(section.group(1), "DTASOF")[:8], "%Y%m%d").date().isoformat()
                    value = cents(field(section.group(1), "BALAMT"))
                except ValueError:
                    raise ValueError("Saldo com valor ou data inválida; nada foi importado.") from None
                balances.append({"account_key": account_key, "as_of": as_of,
                                 "balance_type": balance_type, "amount_cents": value})
        transactions = re.findall(r"<STMTTRN>(.*?)</STMTTRN>", statement, re.I | re.S)
        if len(transactions) != len(re.findall(r"<STMTTRN>", statement, re.I)):
            raise ValueError("Há um lançamento incompleto no OFX; nada foi importado.")
        for index, transaction in enumerate(transactions, 1):
            try:
                raw_date = field(transaction, "DTPOSTED")
                day = datetime.strptime(raw_date[:8], "%Y%m%d").date().isoformat()
                amount = cents(field(transaction, "TRNAMT"))
                name, memo = field(transaction, "NAME"), field(transaction, "MEMO")
                description = " — ".join(dict.fromkeys(v for v in (name, memo) if v)) or "Sem descrição"
                if len(description) > 500:
                    raise ValueError("Descrição excede 500 caracteres.")
                fitid = field(transaction, "FITID") or None
                if fitid and len(fitid) > 250:
                    raise ValueError("Identificador bancário muito longo.")
                kind, category = classify(description, amount)
                rows.append({
                    "account_key": account_key, "bank": bank, "origin": origin,
                    "fitid": fitid, "date": day, "description": description,
                    "amount_cents": amount, "kind": kind, "category": category,
                    "fingerprint": digest(f"{account_key}|{day}|{amount}|{normalize(description)}"),
                })
            except ValueError as error:
                raise ValueError(f"Lançamento {index}: {error}") from None
    if not rows and not balances:
        raise ValueError("Este OFX não contém lançamentos.")
    if len(rows) > 20_000:
        raise ValueError("O limite é de 20 mil lançamentos por arquivo.")
    return {"rows": rows, "bank": ", ".join(sorted(banks)), "accounts": accounts, "balances": balances}
