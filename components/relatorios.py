"""
Página 3 — Relatórios: exposição por setor, RF vs RV, evolução patrimonial.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from data.exposicao import calc_exposicao_setor, calc_exposicao_rfxrv


DARK_BG    = "#0A0F1E"
MID_BG     = "#0D1B2A"
ACCENT     = "#00D4FF"
GOLD       = "#F0B429"
GREEN      = "#00E676"
PURPLE     = "#7B2FBE"
TEXT       = "#E8F4FD"
GRID_COLOR = "#1A3550"

SECTOR_COLORS = [
    "#00D4FF", "#F0B429", "#00E676", "#7B2FBE", "#FF6B6B",
    "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD",
    "#98D8C8", "#F7DC6F", "#BB8FCE",
]


def _plotly_layout(fig: go.Figure, title: str = "") -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(color=TEXT, size=14, family="monospace"), x=0),
        paper_bgcolor=DARK_BG,
        plot_bgcolor=MID_BG,
        font=dict(color=TEXT, family="monospace", size=11),
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(bgcolor=MID_BG, bordercolor=GRID_COLOR, borderwidth=1),
        xaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR),
        yaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR),
    )
    return fig


def render_exposicao_setor(df_carteira: pd.DataFrame):
    st.markdown("### Exposição por Setor")

    df_setor = calc_exposicao_setor(df_carteira)
    if df_setor.empty:
        st.info("Sem dados de setor disponíveis.")
        return

    fig = go.Figure(go.Bar(
        x=df_setor["Valor R$"],
        y=df_setor["SETOR"],
        orientation="h",
        marker=dict(
            color=SECTOR_COLORS[:len(df_setor)],
            opacity=0.85,
        ),
        text=[f"R$ {v:,.0f}  ({p:.1f}%)".replace(",",".")
              for v, p in zip(df_setor["Valor R$"], df_setor["% Setor"])],
        textposition="outside",
        textfont=dict(color=TEXT, size=11),
    ))

    fig.update_layout(
        paper_bgcolor=DARK_BG,
        plot_bgcolor=MID_BG,
        font=dict(color=TEXT, family="monospace", size=11),
        margin=dict(l=10, r=80, t=20, b=10),
        height=max(280, len(df_setor) * 44),
        xaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, tickprefix="R$ ",
                   tickformat=",.0f", color=TEXT),
        yaxis=dict(gridcolor=GRID_COLOR, color=TEXT, autorange="reversed"),
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)


def render_exposicao_rfxrv(df_carteira: pd.DataFrame, df_patrimonio: pd.DataFrame):
    st.markdown("### Renda Fixa vs. Renda Variável")

    valor_rv = df_carteira["Valor Atual R$"].sum() if "Valor Atual R$" in df_carteira.columns else 0.0
    exp = calc_exposicao_rfxrv(valor_rv, df_patrimonio)

    col1, col2 = st.columns([1, 1])

    # Donut
    labels = ["Renda Variável", "Renda Fixa", "Outros"]
    values = [exp["rv"], exp["rf"], exp["outros"]]
    colors = [ACCENT, GOLD, PURPLE]

    labels_f = [l for l, v in zip(labels, values) if v > 0]
    values_f = [v for v in values if v > 0]
    colors_f = [c for c, v in zip(colors, values) if v > 0]

    fig_pie = go.Figure(go.Pie(
        labels=labels_f,
        values=values_f,
        hole=0.55,
        marker=dict(colors=colors_f, line=dict(color=DARK_BG, width=2)),
        textinfo="label+percent",
        textfont=dict(size=12, color=TEXT),
    ))
    fig_pie.update_layout(
        paper_bgcolor=DARK_BG,
        font=dict(color=TEXT, family="monospace"),
        margin=dict(l=10, r=10, t=20, b=10),
        legend=dict(bgcolor=MID_BG, bordercolor=GRID_COLOR),
        height=300,
        showlegend=False,
    )
    col1.plotly_chart(fig_pie, use_container_width=True)

    # Cards resumo
    def brl(v):
        return f"R$ {v:,.2f}".replace(",","X").replace(".",",").replace("X",".")

    col2.markdown(f"""
    <div style="padding:16px;display:flex;flex-direction:column;gap:12px;margin-top:20px">
        <div style="background:#0D1B2A;border-left:3px solid {ACCENT};padding:12px 16px;border-radius:4px">
            <div style="color:#7A9BB5;font-size:10px;font-family:monospace;letter-spacing:2px">RENDA VARIÁVEL</div>
            <div style="color:{ACCENT};font-size:18px;font-family:monospace">{brl(exp['rv'])}</div>
            <div style="color:#4A6B85;font-size:11px">{exp['pct_rv']:.1f}% do patrimônio</div>
        </div>
        <div style="background:#0D1B2A;border-left:3px solid {GOLD};padding:12px 16px;border-radius:4px">
            <div style="color:#7A9BB5;font-size:10px;font-family:monospace;letter-spacing:2px">RENDA FIXA</div>
            <div style="color:{GOLD};font-size:18px;font-family:monospace">{brl(exp['rf'])}</div>
            <div style="color:#4A6B85;font-size:11px">{exp['pct_rf']:.1f}% do patrimônio</div>
        </div>
        <div style="background:#0D1B2A;border-left:3px solid {PURPLE};padding:12px 16px;border-radius:4px">
            <div style="color:#7A9BB5;font-size:10px;font-family:monospace;letter-spacing:2px">PATRIMÔNIO TOTAL</div>
            <div style="color:{TEXT};font-size:18px;font-family:monospace">{brl(exp['total'])}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_evolucao_patrimonio(df_hist: pd.DataFrame):
    st.markdown("### Evolução do Patrimônio")

    if df_hist.empty:
        st.markdown(f"""
        <div style="background:#0D1B2A;border:1px solid #1A3550;border-radius:8px;padding:20px 24px;color:#7A9BB5;font-family:monospace;font-size:13px">
            📊 Histórico disponível a partir de hoje.<br>
            <span style="font-size:11px;color:#4A6B85">Cada vez que o dashboard for aberto, um snapshot é gravado automaticamente. O gráfico crescerá organicamente a partir da primeira abertura.</span>
        </div>
        """, unsafe_allow_html=True)
        return

    fig = go.Figure()

    if "Patrimônio Total" in df_hist.columns:
        fig.add_trace(go.Scatter(
            x=df_hist["Data"], y=df_hist["Patrimônio Total"],
            name="Patrimônio Total",
            line=dict(color=TEXT, width=2),
            fill="tozeroy", fillcolor="rgba(232,244,253,0.04)",
        ))
    if "Valor Total Ações" in df_hist.columns:
        fig.add_trace(go.Scatter(
            x=df_hist["Data"], y=df_hist["Valor Total Ações"],
            name="Renda Variável",
            line=dict(color=ACCENT, width=2),
        ))
    if "Valor Total RF" in df_hist.columns:
        fig.add_trace(go.Scatter(
            x=df_hist["Data"], y=df_hist["Valor Total RF"],
            name="Renda Fixa",
            line=dict(color=GOLD, width=2, dash="dot"),
        ))

    fig.update_layout(
        paper_bgcolor=DARK_BG,
        plot_bgcolor=MID_BG,
        font=dict(color=TEXT, family="monospace", size=11),
        margin=dict(l=10, r=10, t=20, b=10),
        height=320,
        legend=dict(bgcolor=MID_BG, bordercolor=GRID_COLOR, borderwidth=1, orientation="h", y=1.08),
        xaxis=dict(gridcolor=GRID_COLOR, color=TEXT),
        yaxis=dict(gridcolor=GRID_COLOR, color=TEXT, tickprefix="R$ ", tickformat=",.0f"),
        hovermode="x unified",
    )

    data_inicio = df_hist["Data"].min().strftime("%d/%m/%Y") if not df_hist.empty else "—"
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(f'<div style="color:#4A6B85;font-size:10px;font-family:monospace">Histórico disponível a partir de {data_inicio}</div>',
                unsafe_allow_html=True)


def render(df_carteira: pd.DataFrame, df_patrimonio: pd.DataFrame, df_hist: pd.DataFrame):
    st.markdown("## Relatórios")
    st.markdown("---")
    render_exposicao_setor(df_carteira)
    st.markdown("---")
    render_exposicao_rfxrv(df_carteira, df_patrimonio)
    st.markdown("---")
    render_evolucao_patrimonio(df_hist)
