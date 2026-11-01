"""Small UI building blocks so every page looks and reads the same way."""
from __future__ import annotations

import html

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from .config import C_DARK, C_PRIMARY
from .data import Filters

_CSS = f"""
<style>
.block-container {{ padding-top: 2rem; max-width: 1250px; }}
h1, h2, h3 {{ color: {C_DARK}; letter-spacing: -0.01em; }}

.page-sub {{ color: #5b6b68; font-size: 1.05rem; margin: -0.6rem 0 1.2rem 0; }}

.kpi {{ background: #f3f6f5; border: 1px solid #e1e8e6; border-left: 5px solid {C_PRIMARY};
        border-radius: 10px; padding: 14px 16px; height: 100%; }}
.kpi .label {{ font-size: .78rem; text-transform: uppercase; letter-spacing: .05em; color: #5b6b68; }}
.kpi .value {{ font-size: 1.85rem; font-weight: 700; color: {C_DARK}; line-height: 1.25; }}
.kpi .note  {{ font-size: .8rem; color: #7a8a87; }}

.callout {{ border-radius: 10px; padding: 14px 18px; margin: .6rem 0 1rem 0; line-height: 1.55; }}
.callout.insight {{ background: #e8f4f1; border-left: 5px solid {C_PRIMARY}; }}
.callout.warn    {{ background: #fff6e0; border-left: 5px solid #e9a800; }}
.callout .title  {{ font-weight: 700; margin-bottom: 2px; }}

.demo-banner {{ background: #fdecea; border: 1px solid #f5b5ab; color: #8a2b1d;
               border-radius: 8px; padding: 8px 12px; font-size: .85rem; margin-bottom: .6rem; }}
[data-testid="stSidebar"] {{ background: #f3f6f5; }}
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def page_header(title: str, question: str) -> None:
    st.title(title)
    st.markdown(f'<div class="page-sub">{html.escape(question)}</div>', unsafe_allow_html=True)


def kpi_row(items: list[tuple[str, str, str]]) -> None:
    """items = [(label, value, small note), ...]"""
    cols = st.columns(len(items))
    for col, (label, value, note) in zip(cols, items):
        col.markdown(
            f'<div class="kpi"><div class="label">{html.escape(label)}</div>'
            f'<div class="value">{html.escape(value)}</div>'
            f'<div class="note">{html.escape(note)}</div></div>',
            unsafe_allow_html=True)


def insight(text: str, title: str = "Key takeaway", kind: str = "insight") -> None:
    st.markdown(f'<div class="callout {kind}"><div class="title">{html.escape(title)}</div>{text}</div>',
                unsafe_allow_html=True)


def warn(text: str, title: str = "Keep in mind") -> None:
    insight(text, title, kind="warn")


def how_to_read(text: str) -> None:
    with st.expander("How to read this chart"):
        st.markdown(text)


def empty_state() -> None:
    st.info("No exams match the current filters. Widen the year range or select more sectors in the sidebar.")


def style_fig(fig: go.Figure, height: int = 420, legend_below: bool = False) -> go.Figure:
    fig.update_layout(
        template="plotly_white", height=height, margin=dict(l=10, r=10, t=50, b=10),
        font=dict(family="sans-serif", size=13, color=C_DARK),
        title=dict(font=dict(size=16)), hoverlabel=dict(font_size=13),
    )
    if legend_below:
        fig.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5))
    return fig


def show(fig: go.Figure, **kw) -> None:
    cfg = {"displaylogo": False}
    fig = style_fig(fig, **kw)
    try:                                    # Streamlit >= 1.50
        st.plotly_chart(fig, width="stretch", config=cfg)
    except TypeError:                       # older Streamlit
        st.plotly_chart(fig, use_container_width=True, config=cfg)


def table(df, **kw) -> None:
    """Full-width dataframe that works on old and new Streamlit versions."""
    try:
        st.dataframe(df, width="stretch", **kw)
    except TypeError:
        st.dataframe(df, use_container_width=True, **kw)


# ---- number formatting ------------------------------------------------------
def n(x) -> str:
    return "-" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{int(round(x)):,}"


def pct(x, d: int = 1) -> str:
    return "-" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{d}f}%"


def current_filters() -> Filters:
    return st.session_state["filters"]
