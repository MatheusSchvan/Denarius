import hashlib
import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation

CATEGORIES = [
    "Não classificado", "Salário", "Outras entradas", "Mercado", "Restaurantes",
    "Moradia", "Transporte", "Saúde", "Educação", "Lazer", "Compras",
    "Higiene", "Limpeza", "Tarifas", "Transferências", "Investimentos",
]
KINDS = {"income", "expense", "transfer", "investment", "adjustment"}


def normalize(value: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", ascii_text.upper()).strip()


def digest(value: str | bytes) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def cents(value: str) -> int:
    try:
        amount = Decimal(value.strip().replace(",", "."))
        if not amount.is_finite() or abs(amount) > 100_000_000:
            raise ValueError("Valor monetário fora do limite suportado.")
        scaled = amount * 100
        if scaled != scaled.to_integral_value():
            raise ValueError("Valor monetário deve ter no máximo duas casas decimais.")
        return int(scaled)
    except (InvalidOperation, AttributeError):
        raise ValueError("Valor monetário inválido.") from None


def iso_date(value: str) -> str:
    try:
        if len(value) != 10:
            raise ValueError()
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise ValueError("Data inválida; use AAAA-MM-DD.") from None


def classify(description: str, amount: int) -> tuple[str, str]:
    text = normalize(description)
    # São sugestões simples. PIX e pagamentos de fatura exigem decisão do usuário.
    kind = "income" if amount > 0 else "expense"
    if amount > 0:
        return kind, "Salário" if "SALARIO" in text else "Outras entradas"
    rules = [
        (("MERCADO", "SUPERMERC", "ATACADO"), "Mercado"),
        (("RESTAUR", "LANCH", "PADARIA", "IFOOD"), "Restaurantes"),
        (("POSTO", "COMBUST", "UBER", "OFICINA"), "Transporte"),
        (("FARMAC", "DROGARIA", "CONSULTA"), "Saúde"),
        (("ALUGUEL", "ENERGIA", "INTERNET", "AGUA"), "Moradia"),
        (("FACULDADE", "UNOESC", "CURSO", "LIVRO"), "Educação"),
        (("STEAM", "CINEMA", "SPOTIFY", "NETFLIX"), "Lazer"),
        (("TARIFA", "ANUIDADE"), "Tarifas"),
    ]
    for words, category in rules:
        if any(word in text for word in words):
            return kind, category
    return kind, "Não classificado"

