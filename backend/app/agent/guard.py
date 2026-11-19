"""Post-response verification for prices and centimetre measurements."""

import json
import re

from sqlalchemy.orm import Session

from app.services.errors import log_error

_NUMBER = re.compile(r"(?:US\$|\$)\s*(\d+(?:[.,]\d+)?)|\b(\d+(?:[.,]\d+)?)\s*cm\b", re.I)


def _numbers(value) -> set[str]:
    text = json.dumps(value, ensure_ascii=False)
    return {m.group(0).replace(",", ".") for m in re.finditer(r"\d+(?:[.,]\d+)?", text)}


def _safe_text(results: list[dict]) -> str:
    products = []
    for result in results:
        products.extend(result.get("products", []))
        if result.get("product"):
            products.append(result["product"])
    if not products:
        return "No tengo datos verificados para responder esa cifra. Puedo consultar el catálogo por ti."
    return "\n".join(
        f"{p['name']}: US$ {p['price_usd']} · {p['dims_cm']} cm · stock {p['stock']}" for p in products
    )


def validate(text: str, tool_results: list[dict], db: Session | None = None,
             customer_id: int | None = None) -> tuple[bool, str]:
    stated = {next(x for x in m.groups() if x).replace(",", ".") for m in _NUMBER.finditer(text)}
    verified = set().union(*(_numbers(r) for r in tool_results)) if tool_results else set()
    invalid = sorted(stated - verified)
    if not invalid:
        return True, text
    if db is not None:
        log_error(db, "agent", "unverified_number", "Respuesta con cifra no verificada",
                  {"numbers": invalid}, customer_id=customer_id)
    return False, _safe_text(tool_results)
