from __future__ import annotations

from html import escape
from typing import Iterable

import plotly.graph_objects as go
import streamlit as st


NAV_ICONS = {
    "Visão Geral": "▦",
    "Transações": "≡",
    "Categorias": "◌",
    "Marta": "◎",
    "Aluguel + contas": "⌂",
    "Apostas KTO": "⊙",
    "Diagnóstico da Base": "⌁",
}

TONE = {
    "blue": {"bg": "#e8f2ff", "fg": "#075985"},
    "green": {"bg": "#dcfce7", "fg": "#15803d"},
    "red": {"bg": "#fee2e2", "fg": "#dc2626"},
    "amber": {"bg": "#fef3c7", "fg": "#d97706"},
    "purple": {"bg": "#f3e8ff", "fg": "#7c3aed"},
    "slate": {"bg": "#eef2f7", "fg": "#475569"},
}


def inject_global_css():
    st.markdown(
        """
        <style>
        :root {
            --app-bg: #f6f8fb;
            --surface: #ffffff;
            --surface-soft: #f8fbff;
            --border: #dfe8f3;
            --border-strong: #cbd8e8;
            --text: #071b3a;
            --muted: #66738a;
            --blue: #075985;
            --blue-dark: #044b73;
            --blue-soft: #e8f2ff;
            --green: #16a34a;
            --red: #dc2626;
            --amber: #d97706;
            --shadow: 0 16px 34px rgba(15, 23, 42, 0.07);
            --shadow-soft: 0 8px 22px rgba(15, 23, 42, 0.045);
            --radius: 14px;
        }

        .stApp {
            background:
                radial-gradient(circle at 22% 8%, rgba(14, 165, 233, 0.08), transparent 31rem),
                linear-gradient(180deg, #fbfdff 0%, var(--app-bg) 100%);
            color: var(--text);
        }

        .block-container {
            max-width: 1500px;
            padding: 1.15rem 2rem 2.4rem;
        }

        [data-testid="stToolbar"],
        [data-testid="stDecoration"] {
            opacity: 0.55;
        }

        h1, h2, h3, p, label {
            letter-spacing: 0;
        }

        h1 {
            color: var(--text);
            font-size: 2.3rem;
            line-height: 1.08;
            font-weight: 850;
            margin: 0;
        }

        h2, h3 {
            color: var(--text);
            font-weight: 800;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
            border-right: 1px solid var(--border);
            box-shadow: 10px 0 34px rgba(15, 23, 42, 0.05);
        }

        [data-testid="stSidebar"] .block-container,
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            padding-top: 1.1rem;
            gap: 0.7rem;
        }

        .fp-brand {
            display: flex;
            align-items: center;
            gap: 0.82rem;
            margin: 0.15rem 0 2rem;
            color: var(--text);
            font-weight: 850;
            font-size: 1.14rem;
        }

        .fp-brand-mark {
            width: 2.6rem;
            height: 2.6rem;
            border-radius: 0.9rem;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #075985 0%, #0e7490 100%);
            color: #fff;
            box-shadow: 0 14px 26px rgba(7, 89, 133, 0.24);
            font-weight: 900;
        }

        .fp-sidebar-label {
            margin: 1.3rem 0 0.35rem;
            color: #77839a;
            text-transform: uppercase;
            letter-spacing: 0.2em;
            font-size: 0.72rem;
            font-weight: 850;
        }

        .fp-help {
            margin-top: 2rem;
            padding-top: 1.1rem;
            border-top: 1px solid var(--border);
            color: var(--muted);
            font-size: 0.86rem;
            line-height: 1.45;
        }

        [data-testid="stSidebar"] div[data-baseweb="select"] > div {
            border-radius: 0.72rem;
            border-color: var(--border);
            box-shadow: none;
            background: white;
            min-height: 2.55rem;
        }

        [data-testid="stSidebar"] span[data-baseweb="tag"] {
            background: var(--blue-soft) !important;
            border: 1px solid #d9eaff !important;
            color: #08476f !important;
            border-radius: 0.55rem !important;
            font-weight: 750 !important;
        }

        [data-testid="stSidebar"] span[data-baseweb="tag"] svg {
            fill: #075985 !important;
        }

        [data-testid="stSidebar"] div[role="radiogroup"] {
            gap: 0.25rem;
        }

        [data-testid="stSidebar"] div[role="radiogroup"] label {
            min-height: 2.35rem;
            border-radius: 0.7rem;
            padding: 0.15rem 0.35rem;
            transition: background 140ms ease, color 140ms ease;
        }

        [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
            background: linear-gradient(135deg, #075985 0%, #064669 100%);
            color: white !important;
            box-shadow: 0 8px 18px rgba(7, 89, 133, 0.22);
        }

        [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p,
        [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) span {
            color: white !important;
        }

        .fp-page-header {
            margin: 1.1rem 0 1.1rem;
        }

        .fp-page-subtitle {
            color: var(--muted);
            font-size: 1rem;
            margin: 0.45rem 0 0;
        }

        .fp-filterbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            padding: 0.72rem 0.85rem 0.72rem 1rem;
            margin-bottom: 1.2rem;
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid var(--border);
            border-radius: 0.8rem;
            box-shadow: var(--shadow-soft);
        }

        .fp-filterbar-main {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.48rem;
            min-width: 0;
        }

        .fp-filterbar-title {
            color: var(--text);
            font-weight: 850;
            white-space: nowrap;
        }

        .fp-filter-chip {
            display: inline-flex;
            align-items: center;
            padding: 0.28rem 0.62rem;
            border-radius: 0.56rem;
            background: #edf5ff;
            border: 1px solid #dbeaff;
            color: #0f3a5e;
            font-weight: 750;
            font-size: 0.86rem;
            white-space: nowrap;
        }

        .fp-filter-sep {
            color: #9aabc0;
            font-weight: 800;
        }

        .fp-clear-button {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.45rem 0.72rem;
            border-radius: 0.55rem;
            border: 1px solid #d5e4f5;
            background: #f8fbff;
            color: #075985;
            font-weight: 800;
            font-size: 0.84rem;
            white-space: nowrap;
        }

        .fp-kpi-card {
            display: flex;
            align-items: center;
            gap: 1rem;
            min-height: 7.1rem;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 1.15rem 1.2rem;
            box-shadow: var(--shadow);
        }

        .fp-kpi-icon {
            width: 3.15rem;
            height: 3.15rem;
            border-radius: 999px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            flex: 0 0 auto;
            font-size: 1.35rem;
            font-weight: 900;
        }

        .fp-kpi-label {
            color: #334155;
            font-size: 0.78rem;
            font-weight: 850;
            margin-bottom: 0.25rem;
        }

        .fp-kpi-value {
            color: var(--text);
            font-size: clamp(1.38rem, 2vw, 1.9rem);
            line-height: 1.1;
            font-weight: 900;
        }

        .fp-kpi-delta {
            color: var(--muted);
            font-size: 0.82rem;
            font-weight: 700;
            margin-top: 0.45rem;
        }

        .fp-kpi-delta.positive { color: var(--green); }
        .fp-kpi-delta.negative { color: var(--red); }

        .fp-card-title {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.75rem;
            margin: 0.2rem 0 0.75rem;
            color: var(--text);
            font-size: 1.05rem;
            font-weight: 850;
        }

        .fp-card-subtitle {
            color: var(--muted);
            font-size: 0.87rem;
            margin: -0.45rem 0 0.85rem;
        }

        .fp-info {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 1rem;
            height: 1rem;
            border-radius: 999px;
            border: 1px solid #b9c7da;
            color: #6b7b93;
            font-size: 0.7rem;
            font-weight: 900;
        }

        .fp-note {
            text-align: center;
            color: var(--muted);
            font-size: 0.9rem;
            margin: 1.15rem 0 0.25rem;
        }

        .fp-banner {
            display: flex;
            align-items: center;
            gap: 1rem;
            min-height: 5.8rem;
            padding: 1.1rem 1.2rem;
            border-radius: var(--radius);
            border: 1px solid #b7ead2;
            background: linear-gradient(135deg, #f1fff8 0%, #ffffff 100%);
            box-shadow: var(--shadow-soft);
        }

        .fp-banner.attention {
            border-color: #fde68a;
            background: linear-gradient(135deg, #fff9ed 0%, #ffffff 100%);
        }

        .fp-banner-icon {
            width: 3rem;
            height: 3rem;
            border-radius: 999px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: #34d399;
            color: white;
            font-size: 1.35rem;
            font-weight: 900;
            flex: 0 0 auto;
        }

        .fp-banner.attention .fp-banner-icon {
            background: #f59e0b;
        }

        .fp-banner-title {
            color: var(--text);
            font-size: 1.1rem;
            font-weight: 900;
        }

        .fp-banner-copy {
            color: var(--muted);
            font-size: 0.9rem;
            margin-top: 0.2rem;
        }

        .fp-table-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            padding: 1rem;
        }

        [data-testid="stMetric"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 1rem;
            box-shadow: var(--shadow-soft);
        }

        div[data-testid="stPlotlyChart"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 1rem 1.05rem 0.55rem;
            box-shadow: var(--shadow);
        }

        [data-testid="stDataFrame"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 0.45rem;
            box-shadow: var(--shadow-soft);
        }

        [data-testid="stDataFrame"] * {
            font-size: 0.9rem;
        }

        .marta-total-table-wrap {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            box-shadow: var(--shadow-soft);
            padding: 0.55rem 0.75rem 0.7rem;
            overflow: hidden;
        }

        .marta-total-table {
            width: 100%;
            border-collapse: collapse;
            color: var(--text);
            font-size: 0.92rem;
        }

        .marta-total-table thead th {
            padding: 0.82rem 0.7rem;
            border-bottom: 1px solid var(--border);
            color: #64748b;
            background: linear-gradient(180deg, #fbfdff 0%, #f7faff 100%);
            font-size: 0.82rem;
            font-weight: 850;
            text-align: left;
        }

        .marta-total-table tbody td {
            padding: 0.76rem 0.7rem;
            border-bottom: 1px solid #edf2f8;
            vertical-align: middle;
        }

        .marta-total-table tbody tr:last-child td {
            border-bottom: 0;
        }

        .marta-total-table td.money {
            text-align: right;
            white-space: nowrap;
            font-weight: 800;
        }

        .marta-total-table td.money.positive,
        .marta-detail-table td.money.positive {
            color: var(--green);
        }

        .marta-total-table td.money.negative,
        .marta-detail-table td.money.negative {
            color: var(--red);
        }

        .marta-total-table td.change {
            text-align: right;
            white-space: nowrap;
        }

        .marta-total-table tfoot td {
            padding: 0.9rem 0.7rem;
            border-top: 1px solid #dbeafe;
            background: linear-gradient(135deg, #eef6ff 0%, #f8fbff 100%);
            color: #0f4aa8;
            font-weight: 950;
        }

        .marta-total-table tfoot td:first-child {
            border-radius: 0.65rem 0 0 0.65rem;
            letter-spacing: 0.01em;
            font-size: 0.82rem;
        }

        .marta-total-table tfoot td:last-child {
            border-radius: 0 0.65rem 0.65rem 0;
        }

        .marta-diff {
            display: block;
            color: #64748b;
            font-size: 0.78rem;
            font-weight: 750;
            line-height: 1.05;
        }

        .marta-pct {
            display: inline-flex;
            align-items: center;
            gap: 0.16rem;
            margin-top: 0.1rem;
            font-size: 0.9rem;
            font-weight: 900;
            line-height: 1.15;
        }

        .marta-pct.positive,
        .marta-diff.positive {
            color: var(--green);
        }

        .marta-pct.negative,
        .marta-diff.negative {
            color: var(--red);
        }

        .marta-dash {
            color: #94a3b8;
            font-weight: 900;
        }

        .marta-detail-table-wrap {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            box-shadow: var(--shadow-soft);
            padding: 0.55rem 0.75rem 0.7rem;
            overflow-x: auto;
        }

        .marta-detail-table {
            width: 100%;
            border-collapse: collapse;
            color: var(--text);
            font-size: 0.9rem;
        }

        .marta-detail-table thead th {
            padding: 0.82rem 0.7rem;
            border-bottom: 1px solid var(--border);
            color: #64748b;
            background: linear-gradient(180deg, #fbfdff 0%, #f7faff 100%);
            font-size: 0.82rem;
            font-weight: 850;
            text-align: left;
        }

        .marta-detail-table tbody td {
            padding: 0.68rem 0.7rem;
            border-bottom: 1px solid #edf2f8;
            vertical-align: top;
        }

        .marta-detail-table td.group {
            width: 9.5rem;
        }

        .marta-detail-table td.money {
            text-align: right;
            white-space: nowrap;
            font-weight: 850;
        }

        .marta-detail-table tr.subtotal td {
            border-bottom: 1px solid #e2e8f0;
            background: #f8fbff;
            color: #0f4aa8;
            font-weight: 900;
        }

        .marta-detail-table tr.subtotal td:first-child {
            background: #f8fbff;
        }

        .marta-detail-table tfoot td {
            padding: 0.95rem 0.7rem;
            border-top: 1px solid #dbeafe;
            background: linear-gradient(135deg, #eef6ff 0%, #f8fbff 100%);
            color: #0f4aa8;
            font-weight: 950;
        }

        .marta-detail-table tfoot td:first-child {
            border-radius: 0.65rem 0 0 0.65rem;
            letter-spacing: 0.01em;
            font-size: 0.82rem;
        }

        .marta-detail-table tfoot td:last-child {
            border-radius: 0 0.65rem 0.65rem 0;
        }

        .marta-group-badge {
            display: inline-flex;
            align-items: center;
            border-radius: 0.45rem;
            padding: 0.26rem 0.48rem;
            font-size: 0.76rem;
            font-weight: 900;
            white-space: nowrap;
        }

        .marta-group-badge.shared {
            color: #0f4aa8;
            background: #dbeafe;
        }

        .marta-group-badge.exclusive {
            color: #047857;
            background: #d1fae5;
        }

        .marta-group-badge.discount {
            color: #dc2626;
            background: #fee2e2;
        }

        .marta-group-badge.other {
            color: #475569;
            background: #e2e8f0;
        }

        .marta-total-table td.money.positive,
        .marta-total-table tfoot td.money.positive,
        .marta-detail-table td.money.positive,
        .marta-detail-table tr.subtotal td.money.positive,
        .marta-detail-table tfoot td.money.positive {
            color: var(--green) !important;
        }

        .marta-total-table td.money.negative,
        .marta-total-table tfoot td.money.negative,
        .marta-detail-table td.money.negative,
        .marta-detail-table tr.subtotal td.money.negative,
        .marta-detail-table tfoot td.money.negative {
            color: var(--red) !important;
        }

        div[data-testid="stExpander"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            box-shadow: var(--shadow-soft);
            overflow: hidden;
        }

        div[data-testid="stExpander"] details summary p {
            font-weight: 850;
            color: var(--text);
        }

        [data-testid="stTextInput"] input {
            border-radius: 0.75rem;
            border-color: var(--border);
            min-height: 2.75rem;
            background: white;
        }

        div[data-baseweb="select"] > div {
            border-radius: 0.75rem;
            border-color: var(--border);
            background: white;
        }

        .stButton > button,
        [data-testid="baseButton-secondary"] {
            border-radius: 0.7rem !important;
            border: 1px solid #d7e6f7 !important;
            background: #f8fbff !important;
            color: #075985 !important;
            font-weight: 800 !important;
            box-shadow: none !important;
        }

        .fp-badge {
            display: inline-flex;
            align-items: center;
            padding: 0.18rem 0.5rem;
            border-radius: 999px;
            background: #e8f2ff;
            color: #075985;
            font-size: 0.78rem;
            font-weight: 800;
        }

        .fp-badge.green { background: #dcfce7; color: #15803d; }
        .fp-badge.red { background: #fee2e2; color: #dc2626; }
        .fp-badge.amber { background: #fef3c7; color: #b45309; }

        @media (max-width: 900px) {
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }
            .fp-filterbar {
                align-items: flex-start;
                flex-direction: column;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar_brand():
    st.sidebar.markdown(
        '<div class="fp-brand"><span class="fp-brand-mark">R$</span><span>Finanças Pessoais</span></div>',
        unsafe_allow_html=True,
    )


def sidebar_section(label: str):
    st.sidebar.markdown(f"<div class='fp-sidebar-label'>{escape(label)}</div>", unsafe_allow_html=True)


def sidebar_help():
    st.sidebar.markdown(
        "<div class='fp-help'>Precisa de ajuda?<br><strong>Ver guia rápido</strong></div>",
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str):
    st.markdown(
        f"""
        <div class="fp-page-header">
            <h1>{escape(title)}</h1>
            <p class="fp-page-subtitle">{escape(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def filter_bar(months: str, origins: str, categories: str, show_clear: bool = False):
    clear_html = '<span class="fp-clear-button">Limpar filtros</span>' if show_clear else ""
    st.markdown(
        (
            '<div class="fp-filterbar"><div class="fp-filterbar-main">'
            '<span class="fp-filterbar-title">Filtros ativos:</span>'
            f'<span class="fp-filter-chip">{escape(months)}</span>'
            '<span class="fp-filter-sep">·</span>'
            f'<span class="fp-filter-chip">{escape(origins)}</span>'
            '<span class="fp-filter-sep">·</span>'
            f'<span class="fp-filter-chip">{escape(categories)}</span>'
            f'</div>{clear_html}</div>'
        ),
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, delta: str | None = None, icon: str = "↗", tone: str = "blue", delta_tone: str = ""):
    palette = TONE.get(tone, TONE["blue"])
    delta_class = f" {delta_tone}" if delta_tone else ""
    delta_html = f"<div class='fp-kpi-delta{delta_class}'>{escape(delta)}</div>" if delta else ""
    st.markdown(
        (
            '<div class="fp-kpi-card">'
            f'<span class="fp-kpi-icon" style="background:{palette["bg"]}; color:{palette["fg"]};">{escape(icon)}</span>'
            '<div>'
            f'<div class="fp-kpi-label">{escape(label)}</div>'
            f'<div class="fp-kpi-value">{escape(value)}</div>'
            f'{delta_html}'
            '</div></div>'
        ),
        unsafe_allow_html=True,
    )


def card_title(title: str, subtitle: str | None = None, info: bool = True):
    info_html = "<span class='fp-info'>i</span>" if info else ""
    subtitle_html = f"<div class='fp-card-subtitle'>{escape(subtitle)}</div>" if subtitle else ""
    st.markdown(
        f'<div class="fp-card-title"><span>{escape(title)} {info_html}</span></div>{subtitle_html}',
        unsafe_allow_html=True,
    )


def note(text: str):
    st.markdown(f"<div class='fp-note'>{escape(text)}</div>", unsafe_allow_html=True)


def status_banner(ok: bool, title: str, copy: str):
    status_class = "" if ok else " attention"
    icon = "✓" if ok else "!"
    st.markdown(
        (
            f'<div class="fp-banner{status_class}">'
            f'<span class="fp-banner-icon">{escape(icon)}</span>'
            '<div>'
            f'<div class="fp-banner-title">{escape(title)}</div>'
            f'<div class="fp-banner-copy">{escape(copy)}</div>'
            '</div></div>'
        ),
        unsafe_allow_html=True,
    )


def chart_layout(
    fig: go.Figure,
    height: int = 380,
    legend: str | None = None,
    show_title: bool = False,
) -> go.Figure:
    top_margin = 22 if not show_title else 58
    bottom_margin = 54
    legend_config = None
    if legend == "top":
        top_margin = 54 if not show_title else 78
        legend_config = {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.04,
            "xanchor": "left",
            "x": 0,
            "title_text": "",
            "font": {"size": 11, "color": "#25324b"},
        }
    elif legend == "bottom":
        bottom_margin = 96
        legend_config = {
            "orientation": "h",
            "yanchor": "top",
            "y": -0.22,
            "xanchor": "left",
            "x": 0,
            "title_text": "",
            "font": {"size": 11, "color": "#25324b"},
        }

    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#25324b", "size": 12},
        title=fig.layout.title if show_title else {"text": ""},
        margin={"l": 54, "r": 34, "t": top_margin, "b": bottom_margin},
        hoverlabel={"bgcolor": "white", "bordercolor": "#d8e3f2", "font": {"color": "#0b1f44"}},
    )
    if legend_config:
        fig.update_layout(legend=legend_config)
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="#dbe5f1", tickfont={"color": "#55657f"})
    fig.update_yaxes(gridcolor="#e7eef7", zerolinecolor="#dbe5f1", tickfont={"color": "#55657f"})
    return fig


def nav_label(page: str) -> str:
    return f"{NAV_ICONS.get(page, '•')}  {page}"


def nav_page_from_label(label: str) -> str:
    for page in NAV_ICONS:
        if label.endswith(page):
            return page
    return label


def comma_join(values: Iterable[str], fallback: str) -> str:
    cleaned = [str(value) for value in values if str(value)]
    if not cleaned:
        return fallback
    if len(cleaned) <= 3:
        return ", ".join(cleaned)
    return f"{cleaned[0]} a {cleaned[-1]}"
