"""Iconos SVG en línea (trazo 1.5, ``currentColor``, retícula 24×24) para el dashboard.

Cada entrada es solo el contenido interno del ``<svg>``; ``icon()`` arma el elemento
completo con el tamaño y color pedidos. Al heredar ``currentColor`` el icono toma el
color del texto que lo rodea salvo que se indique ``color``.
"""

from __future__ import annotations

import html

ICONS: dict[str, str] = {
    "chat": '<path d="M20 12a7.5 7.5 0 0 1-11.1 6.6L4 20l1.4-4.6A7.5 7.5 0 1 1 20 12Z"/>',
    "search": '<circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/>',
    "file-text": (
        '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z"/>'
        '<path d="M14 3v5h5"/><path d="M9 13h6"/><path d="M9 17h6"/><path d="M9 9h1.5"/>'
    ),
    "shopping-bag": (
        '<path d="M5.5 7h13l-1 12.2a2 2 0 0 1-2 1.8h-7a2 2 0 0 1-2-1.8Z"/><path d="M9 10V6a3 3 0 0 1 6 0v4"/>'
    ),
    "check-circle": '<circle cx="12" cy="12" r="8.5"/><path d="m8.5 12.2 2.4 2.3 4.6-4.8"/>',
    "image": (
        '<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><circle cx="9" cy="10" r="1.6"/>'
        '<path d="m20.5 16-4.6-4.6a1 1 0 0 0-1.4 0L6 19.5"/>'
    ),
    "star": ('<path d="m12 3.8 2.5 5.1 5.6.8-4 3.9.9 5.6-5-2.6-5 2.6.9-5.6-4-3.9 5.6-.8Z"/>'),
    "coins": (
        '<ellipse cx="9" cy="7" rx="5.5" ry="2.5"/><path d="M3.5 7v4c0 1.4 2.5 2.5 5.5 2.5s5.5-1.1 5.5-2.5V7"/>'
        '<path d="M9.5 16.4c.9.1 1.8.1 2.7 0"/><path d="M14.5 10.6c3.4.2 6 1.3 6 2.6 0 1.4-2.5 2.5-5.5 2.5"/>'
        '<path d="M20.5 13.2v4c0 1.4-2.5 2.5-5.5 2.5s-5.5-1.1-5.5-2.5v-1.6"/>'
    ),
    "dollar": (
        '<path d="M12 3v18"/>'
        '<path d="M16.5 7.5c0-1.7-2-3-4.5-3s-4.5 1.3-4.5 3 2 2.6 4.5 3 4.5 1.4 4.5 3.3-2 3.2-4.5 3.2-4.5-1.3-4.5-3"/>'
    ),
    "activity": '<path d="M3 12h4l2.5-7 5 14 2.5-7h4"/>',
    "alert-triangle": (
        '<path d="M10.3 4.3 2.9 17.5A2 2 0 0 0 4.6 20.5h14.8a2 2 0 0 0 1.7-3L13.7 4.3a2 2 0 0 0-3.4 0Z"/>'
        '<path d="M12 9.5v4"/><path d="M12 17h.01"/>'
    ),
    "list": (
        '<path d="M9 6h11"/><path d="M9 12h11"/><path d="M9 18h11"/>'
        '<path d="M4.5 6h.01"/><path d="M4.5 12h.01"/><path d="M4.5 18h.01"/>'
    ),
    "box": (
        '<path d="M20.5 7.8 12 3.5 3.5 7.8v8.4l8.5 4.3 8.5-4.3Z"/><path d="m3.5 7.8 8.5 4.3 8.5-4.3"/>'
        '<path d="M12 12.1v8.4"/>'
    ),
    "refresh": (
        '<path d="M19.5 12a7.5 7.5 0 0 1-13 5.1"/><path d="M4.5 12a7.5 7.5 0 0 1 13-5.1"/>'
        '<path d="M17.5 3.5v3.4h-3.4"/><path d="M6.5 20.5v-3.4h3.4"/>'
    ),
    "trending-up": '<path d="m3.5 17 6-6 4 4 7-7.5"/><path d="M15 7.5h5.5V13"/>',
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    "settings": (
        '<circle cx="12" cy="12" r="3"/>'
        '<path d="M12 3.5v2M12 18.5v2M3.5 12h2M18.5 12h2M6 6l1.4 1.4M16.6 16.6 18 18M6 18l1.4-1.4M16.6 7.4 18 6"/>'
    ),
    "info": '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5"/><path d="M12 8h.01"/>',
    "users": (
        '<circle cx="9" cy="8.5" r="3.5"/><path d="M2.5 20c.5-3.4 3.2-5.5 6.5-5.5s6 2.1 6.5 5.5"/>'
        '<path d="M15.5 5.2a3.5 3.5 0 0 1 0 6.6"/><path d="M18 14.9c2 .7 3.3 2.5 3.6 5.1"/>'
    ),
    "bell": ('<path d="M6 9.5a6 6 0 0 1 12 0c0 5 2 6.5 2 6.5H4s2-1.5 2-6.5Z"/><path d="M10.2 19.5a2 2 0 0 0 3.6 0"/>'),
    "wifi-off": '<path d="M3.5 3.5 20.5 20.5"/><path d="M8.5 16.5a5 5 0 0 1 7 0"/><path d="M12 20h.01"/>'
    '<path d="M5 12.5a10 10 0 0 1 4-2.3"/><path d="M14.5 10.2a10 10 0 0 1 4.5 2.3"/>',
}

ALIASES = {
    "quote": "file-text",
    "order": "shopping-bag",
    "sale": "check-circle",
    "simulation": "image",
    "product": "box",
    "cost": "coins",
    "warning": "alert-triangle",
}


def icon(name: str, size: int = 20, color: str | None = None) -> str:
    """Devuelve el ``<svg>`` del icono ``name`` (o uno neutro si no existe)."""
    body = ICONS.get(ALIASES.get(name, name), ICONS["info"])
    stroke = html.escape(color, quote=True) if color else "currentColor"
    px = int(size)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{px}" height="{px}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{stroke}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true" focusable="false">{body}</svg>'
    )
