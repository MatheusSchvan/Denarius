from decimal import Decimal, InvalidOperation

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

from .domain import cents, classify, iso_date


def parse_receipt(raw: bytes) -> dict:
    try:
        root = ElementTree.fromstring(raw, forbid_dtd=True, forbid_entities=True, forbid_external=True)
    except (ElementTree.ParseError, DefusedXmlException):
        raise ValueError("XML inválido ou com declarações externas não permitidas.") from None
    # A mesma leitura atende NF-e e NFC-e com ou sem namespace.
    for element in root.iter():
        element.tag = element.tag.rsplit("}", 1)[-1]
    info = root if root.tag == "infNFe" else root.find(".//infNFe")
    if info is None:
        raise ValueError("O arquivo não contém uma NF-e/NFC-e com itens.")
    if len(root.findall(".//infNFe")) > 1:
        raise ValueError("Importe uma nota por arquivo XML.")

    def read(path: str, fallback: str = "") -> str:
        return (info.findtext(path) or fallback).strip()

    merchant = read("emit/xFant") or read("emit/xNome")
    if not merchant:
        raise ValueError("A nota não informa o estabelecimento.")
    day = iso_date((read("ide/dhEmi") or read("ide/dEmi"))[:10])
    total = cents(read("total/ICMSTot/vNF"))
    if total <= 0:
        raise ValueError("A nota precisa ter total positivo.")
    items = []
    for detail in info.findall("det"):
        product = detail.find("prod")
        if product is None:
            raise ValueError("Item sem dados do produto.")
        if product.findtext("indTot", "1") != "1":
            continue
        description = product.findtext("xProd", "").strip()
        if not description or len(description) > 500:
            raise ValueError("Descrição de produto ausente ou longa demais.")
        try:
            quantity = Decimal(product.findtext("qCom", ""))
            unit_price = Decimal(product.findtext("vUnCom", ""))
            if not quantity.is_finite() or not unit_price.is_finite() or quantity <= 0 or unit_price < 0 or quantity > 1_000_000 or unit_price > 100_000_000:
                raise ValueError("Quantidade ou preço unitário inválido.")
        except InvalidOperation:
            raise ValueError("Quantidade ou preço unitário inválido.") from None
        gross = cents(product.findtext("vProd", ""))
        discount = cents(product.findtext("vDesc", "0"))
        extras = sum(cents(product.findtext(tag, "0")) for tag in ("vFrete", "vSeg", "vOutro"))
        net = gross - discount + extras
        if net < 0:
            raise ValueError("Total negativo em um item da nota.")
        _, category = classify(description, -net)
        items.append({"description": description, "quantity": str(quantity.normalize()), "unit": product.findtext("uCom", "UN"), "unit_price_cents": int((unit_price * 100).quantize(Decimal("1"))), "total_cents": net, "category": category})
    if not items or len(items) > 500:
        raise ValueError("A nota deve ter entre 1 e 500 itens.")
    key = info.attrib.get("Id", "").removeprefix("NFe") or None
    difference = total - sum(item["total_cents"] for item in items)
    return {"merchant": merchant[:250], "date": day, "total_cents": total, "access_key": key,
            "items": items, "difference_cents": difference,
            "warnings": ["A soma dos itens difere do total da nota. Confira descontos, frete e impostos antes de vincular."] if difference else []}
