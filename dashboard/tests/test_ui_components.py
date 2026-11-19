"""Tests de iconos, componentes HTML y constructores de gráficos (sin runtime de Streamlit)."""

import sys
from pathlib import Path

import plotly.graph_objects as go
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import charts  # noqa: E402
import icons  # noqa: E402
import ui  # noqa: E402

REQUIRED_ICONS = [
    "chat",
    "search",
    "file-text",
    "shopping-bag",
    "check-circle",
    "image",
    "star",
    "coins",
    "dollar",
    "activity",
    "alert-triangle",
    "list",
    "box",
    "refresh",
    "trending-up",
    "clock",
    "settings",
]


@pytest.mark.parametrize("name", REQUIRED_ICONS)
def test_icon_returns_inline_svg(name):
    svg = icons.icon(name)
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    assert 'width="20"' in svg and 'height="20"' in svg
    assert 'stroke="currentColor"' in svg and 'stroke-width="1.5"' in svg
    assert 'fill="none"' in svg


def test_icon_size_color_alias_and_fallback():
    svg = icons.icon("box", size=36, color="#6f7d4f")
    assert 'width="36"' in svg and 'stroke="#6f7d4f"' in svg
    assert icons.icon("order") == icons.icon("shopping-bag")
    assert icons.icon("no-existe") == icons.icon("info")
    assert '"><script>' not in icons.icon("star", color='"><script>')


def test_kpi_card_escapes_dynamic_text():
    card = ui.kpi_card("chat", "<b>Ventas</b>", "<script>alert(1)</script>", delta="5 % <i>", hint="a & b")
    assert "<script>" not in card and "&lt;script&gt;" in card
    assert "&lt;b&gt;Ventas&lt;/b&gt;" in card
    assert "5 % &lt;i&gt;" in card
    assert "a &amp; b" in card
    assert "<svg" in card


def test_kpi_card_unknown_tone_falls_back_to_neutral():
    assert "ds-ico neutral" in ui.kpi_card("star", "x", 1, tone="weird")
    assert "ds-ico positive" in ui.kpi_card("star", "x", 1, tone="positive")


def test_status_pill_and_empty_state_escape():
    assert ui.status_pill("<x>", "error") == '<span class="ds-pill error">&lt;x&gt;</span>'
    html = ui.empty_state_html("info", "<t>", "<p>")
    assert "&lt;t&gt;" in html and "&lt;p&gt;" in html


@pytest.mark.parametrize(
    ("pct", "tone"),
    [
        (0, "neutral"),
        (79.9, "neutral"),
        (80, "warning"),
        (99.99, "warning"),
        (100, "error"),
        (250, "error"),
        ("85.5", "warning"),
        (None, "neutral"),
    ],
)
def test_progress_bar_tone_thresholds(pct, tone):
    assert ui.budget_tone(pct) == tone
    assert f'class="ds-fill {tone}"' in ui.progress_bar(pct)


def test_progress_bar_width_is_clamped_and_tone_overridable():
    assert "width:100.00%" in ui.progress_bar(180)
    assert "width:0.00%" in ui.progress_bar(-5)
    assert 'class="ds-fill positive"' in ui.progress_bar(90, tone="positive")


def test_fmt_datetime():
    assert ui.fmt_datetime(None) == "—"
    assert ui.fmt_datetime("no es fecha") == "no es fecha"
    assert ui.fmt_datetime("2026-11-18T15:00:00+00:00") == "18 nov 10:00"  # America/Lima


@pytest.mark.parametrize(
    "build",
    [
        lambda: charts.daily_activity([], ui.SERIES_LABELS),
        lambda: charts.grouped_bars([], {"conversations": "Conversaciones"}),
        lambda: charts.top_products([]),
        lambda: charts.ratings_distribution([]),
        lambda: charts.spend_by_day([], budget=3.5),
        lambda: charts.spend_by_operation([]),
    ],
)
def test_chart_builders_accept_empty_data(build):
    fig = build()
    assert isinstance(fig, go.Figure)
    assert fig.layout.template.layout.paper_bgcolor == "rgba(0,0,0,0)"
    assert fig.layout.template.layout.yaxis.gridcolor == charts.GRID


def test_chart_builders_with_data():
    daily = [{"date": "2026-11-17", "conversations": 2, "inquiries": 5}, {"date": "2026-11-18", "conversations": 4}]
    fig = charts.daily_activity(daily, {"conversations": "Conversaciones", "inquiries": "Consultas"})
    assert len(fig.data) == 2 and fig.data[0].line.color == charts.INK and fig.data[0].line.width == 2
    assert list(fig.data[1].y) == [5, 0]

    top = charts.top_products([{"name": "A", "count": 1}, {"name": "B", "count": 9}])
    assert list(top.data[0].y) == ["A", "B"]  # el mayor queda arriba

    ratings = charts.ratings_distribution([5, "4", 4, None, 9, "x"])
    assert list(ratings.data[0].y) == [0, 0, 0, 2, 1]

    donut = charts.spend_by_operation([{"operation": "chat", "cost_usd": 0.5, "calls": 3}], {"chat": "Chat"})
    assert donut.data[0].hole == pytest.approx(0.78) and list(donut.data[0].labels) == ["Chat"]
    assert "US$ 0.5000" in donut.layout.annotations[0].text

    spend = charts.spend_by_day([{"date": "2026-11-18", "cost_usd": 2.0}], budget=3.5)
    assert list(spend.data[1].y) == [2.0] and len(spend.layout.shapes) == 1


def test_event_helpers():
    assert ui.event_meta("simulation.failed") == ("alert-triangle", "Simulación fallida", "error")
    assert ui.event_meta("otro.tipo")[0] == "activity"
    assert ui.entity_label({"entity_type": "system", "entity_id": None}) == "system"
    assert ui.entity_label({"entity_type": "quote", "entity_id": 3}) == "quote #3"
    html = ui.event_list([{"type": "<b>x</b>", "entity_type": "quote", "entity_id": 1, "created_at": None}])
    assert "&lt;b&gt;x&lt;/b&gt;" in html and "<b>x</b>" not in html
