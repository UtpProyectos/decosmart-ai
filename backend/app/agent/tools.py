"""Strict function schemas and server-side tool dispatch."""
# ruff: noqa: E501

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models import Conversation, Customer
from app.services import catalog, inquiries, orders, quotes


def _tool(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {"type": "function", "name": name, "description": description, "strict": True,
            "parameters": {"type": "object", "additionalProperties": False,
                           "properties": properties, "required": required}}


TOOLS = [
    _tool("search_products", "Busca productos activos del catálogo por texto, categoría, rango de precio o tipo de ambiente.",
          {"query": {"type": ["string", "null"], "description": "Texto libre, p. ej. 'sofá gris'"},
           "category": {"type": ["string", "null"],
                        "enum": ["sofas", "mesas", "sillas", "camas", "almacenamiento", "escritorios", None]},
           "max_price": {"type": ["number", "null"]},
           "room": {"type": ["string", "null"],
                    "enum": ["sala", "dormitorio", "comedor", "oficina", None]}},
          ["query", "category", "max_price", "room"]),
    _tool("get_product", "Obtiene detalle completo (precio, medidas en cm, colores, material, stock) de un producto por id o SKU.",
          {"product_ref": {"type": "string", "description": "id numérico o SKU, p. ej. 'DS-SOF-001'"}},
          ["product_ref"]),
    _tool("check_stock", "Verifica disponibilidad de una cantidad de un producto.",
          {"product_ref": {"type": "string"}, "quantity": {"type": "integer", "minimum": 1}},
          ["product_ref", "quantity"]),
    _tool("recommend_products", "Recomienda hasta 3 productos en stock según presupuesto, ambiente y medidas disponibles. El backend filtra; el modelo solo explica.",
          {"budget": {"type": ["number", "null"], "description": "Presupuesto máximo en USD"},
           "room": {"type": ["string", "null"],
                    "enum": ["sala", "dormitorio", "comedor", "oficina", None]},
           "category": {"type": ["string", "null"]},
           "max_width_cm": {"type": ["integer", "null"],
                            "description": "Ancho máximo disponible para el mueble"},
           "style": {"type": ["string", "null"]}}, ["budget", "room", "category", "max_width_cm", "style"]),
    _tool("select_product", "Marca un producto como seleccionado por el cliente en la conversación (para simular o cotizar).",
          {"product_ref": {"type": "string"}}, ["product_ref"]),
    _tool("start_simulation", "Inicia el flujo de simulación visual del producto seleccionado. NO genera la imagen: el bot pedirá foto, medidas y confirmación.",
          {"product_ref": {"type": ["string", "null"],
                           "description": "Si es null usa el producto seleccionado"}}, ["product_ref"]),
    _tool("create_quote", "Crea una cotización formal con precios del catálogo y la envía al cliente por Telegram.",
          {"items": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                     "properties": {"product_ref": {"type": "string"},
                                    "quantity": {"type": "integer", "minimum": 1}},
                     "required": ["product_ref", "quantity"]}}, "notes": {"type": ["string", "null"]}},
          ["items", "notes"]),
    _tool("create_order_request", "Registra un pedido de demostración (sin pago) a partir de una cotización del cliente.",
          {"quote_code": {"type": "string"}, "contact_phone": {"type": ["string", "null"]},
           "delivery_address": {"type": ["string", "null"]}},
          ["quote_code", "contact_phone", "delivery_address"]),
    _tool("get_request_status", "Consulta el estado de una cotización (COT-...) o pedido (PED-...) del cliente actual.",
          {"code": {"type": "string"}}, ["code"]),
]


@dataclass
class ToolContext:
    customer: Customer
    conversation: Conversation
    actions: list[dict[str, Any]] = field(default_factory=list)


def _products(items) -> dict:
    return {"ok": True, "products": [catalog.product_to_tool(p) for p in items]}


def _record(db: Session, ctx: ToolContext, kind: str, product=None, payload=None) -> None:
    inquiries.record_inquiry(db, kind, customer_id=ctx.customer.id,
                             product_id=product.id if product else None,
                             category_id=product.category_id if product else None,
                             channel="telegram", payload=payload or {})


def _show(ctx: ToolContext, products) -> None:
    """Pide al bot enviar las tarjetas con foto de estos productos tras la respuesta de texto."""
    ids = [p.id for p in products]
    if not ids:
        return
    existing = next((a for a in ctx.actions if a["type"] == "show_products"), None)
    if existing is None:
        ctx.actions.append({"type": "show_products", "product_ids": ids})
    else:
        existing["product_ids"] += [i for i in ids if i not in existing["product_ids"]]


def dispatch(db: Session, name: str, args: dict, ctx: ToolContext) -> dict:
    if name == "search_products":
        products = catalog.search_products(db, **args, limit=10)
        for p in products:
            _record(db, ctx, "catalog", p, args)
        _show(ctx, products)
        return _products(products)
    if name == "get_product":
        p = catalog.get_product(db, args["product_ref"])
        if not p:
            return {"ok": False, "error": "PRODUCT_NOT_FOUND"}
        _record(db, ctx, "product_info", p, args)
        return {"ok": True, "product": catalog.product_to_tool(p)}
    if name == "check_stock":
        result = catalog.check_stock(db, args["product_ref"], args["quantity"])
        p = catalog.get_product(db, args["product_ref"])
        if p:
            _record(db, ctx, "stock", p, args)
        return result
    if name == "recommend_products":
        products = catalog.recommend(db, **args)
        for p in products:
            _record(db, ctx, "recommendation", p, args)
        _show(ctx, products)
        return _products(products)
    if name in {"select_product", "start_simulation"}:
        ref = args.get("product_ref") or (ctx.conversation.context or {}).get("selected_product")
        p = catalog.get_product(db, ref)
        if not p:
            return {"ok": False, "error": "PRODUCT_NOT_FOUND"}
        context = dict(ctx.conversation.context or {})
        context["selected_product"] = p.sku
        ctx.conversation.context = context
        if name == "start_simulation":
            ctx.actions.append({"type": "start_simulation", "product_id": p.id})
        db.commit()
        return {"ok": True, "product": catalog.product_to_tool(p)}
    if name == "create_quote":
        quote = quotes.create_quote(db, ctx.customer, args["items"], channel="telegram", notes=args.get("notes"))
        ctx.actions.append({"type": "quote_created", "quote_code": quote.code})
        return {"ok": True, "quote_code": quote.code, "total_usd": f"{quote.total:.2f}"}
    if name == "create_order_request":
        order = orders.create_order(db, ctx.customer, quote_code=args["quote_code"], channel="telegram",
                                    contact_phone=args.get("contact_phone"),
                                    delivery_address=args.get("delivery_address"), require_same_customer=True)
        ctx.actions.append({"type": "order_created", "order_code": order.code})
        return {"ok": True, "order_code": order.code, "status": order.status}
    if name == "get_request_status":
        code = args["code"].strip().upper()
        if code.startswith("COT-"):
            item = quotes.get_quote(db, code)
        else:
            item = orders.get_order(db, code)
        if item is None or item.customer_id != ctx.customer.id:
            return {"ok": False, "error": "NOT_FOUND"}
        return {"ok": True, "code": item.code, "status": item.status}
    return {"ok": False, "error": "UNKNOWN_TOOL"}
