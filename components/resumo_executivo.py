"""
Página 1 — Resumo executivo com cards de métricas.
"""

import streamlit as st
import pandas as pd
from datetime import datetime


def _fmt_brl(val, prefix="R$ "):
    if val is None:
        return "—"
    return f"{prefix}{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_pct(val):
    if val is None:
        return "—"
    sinal = "+" if val >= 0 else ""
    return f"{sinal}{val:.2f}%"


def _color_result(val):
    if val is None:
        return "#E8F4FD"
    return "#00E676" if val >= 0 else "#FF5252"


def render_card(col, titulo: str, valor: str, sub: str = "", color: str = "#00D4FF"):
    col.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #0D1B2A 0%, #0F2234 100%);
        border: 1px solid {color}33;
        border-top: 2px solid {color};
        border-radius: 8px;
        padding: 18px 20px 14px;
        min-height: 100px;
    ">
        <div style="color: #7A9BB5; font-size: 10px; letter-spacing: 2px; text-transform: uppercase; font-family: 'DM Mono', monospace; margin-bottom: 8px;">{titulo}</div>
        <div style="color: {color}; font-size: 22px; font-weight: 600; font-family: 'DM Mono', monospace; letter-spacing: 0.5px;">{valor}</div>
        <div style="color: #4A6B85; font-size: 11px; margin-top: 6px; font-family: monospace;">{sub}</div>
    </div>
    """, unsafe_allow_html=True)


def render(portfolio_result: dict, df_carteira: pd.DataFrame,
           df_patrimonio: pd.DataFrame, prices: dict,
           ultima_atualizacao):

    st.markdown("## Resumo Executivo")

    # Calcular totais
    total_rv = 0.0
    total_investido = 0.0
    resultado_nao_realizado = 0.0

    positions = portfolio_result.get("positions", {})

    if not df_carteira.empty:
        for _, row in df_carteira.iterrows():
            tk = str(row.get("TICKER", "")).upper()
            pos = positions.get(tk)
            if not pos or pos["qtd"] <= 0:
                continue
            preco_info = prices.get(tk, {})
            preco_atual = preco_info.get("preco")
            if preco_atual is None:
                preco_atual = pos["preco_medio"]  # fallback: custo
            valor_atual = pos["qtd"] * preco_atual
            total_rv += valor_atual
            total_investido += pos["total_investido"]
            resultado_nao_realizado += valor_atual - pos["total_investido"]

    resultado_realizado = portfolio_result.get("resultado_total_realizado", 0.0)

    # Renda Fixa da aba Patrimônio
    rf_total = 0.0
    if not df_patrimonio.empty and "Categoria" in df_patrimonio.columns:
        for _, row in df_patrimonio.iterrows():
            if str(row.get("Categoria", "")) == "Renda Fixa / Tesouro":
                try:
                    rf_total += float(row.get("Valor R$", 0) or 0)
                except (ValueError, TypeError):
                    pass

    patrimonio_total = total_rv + rf_total

    pct_nao_realizado = (resultado_nao_realizado / total_investido * 100) if total_investido > 0 else 0.0

    # Cards
    col1, col2, col3 = st.columns(3)
    col4, col5, _ = st.columns(3)

    render_card(col1, "Renda Fixa / Tesouro", _fmt_brl(rf_total),
                "valor manual da planilha", "#F0B429")
    render_card(col2, "Renda Variável (Ações)", _fmt_brl(total_rv),
                f"custo: {_fmt_brl(total_investido)}", "#00D4FF")
    render_card(col3, "Patrimônio Total", _fmt_brl(patrimonio_total),
                "RF + RV", "#7B2FBE")

    render_card(col4, "Resultado Não Realizado",
                _fmt_brl(resultado_nao_realizado),
                _fmt_pct(pct_nao_realizado),
                _color_result(resultado_nao_realizado))
    render_card(col5, "Resultado Realizado (Vendas)",
                _fmt_brl(resultado_realizado),
                "acumulado histórico",
                _color_result(resultado_realizado))

    # Nota fixa sobre preços manuais
    st.markdown("<br>", unsafe_allow_html=True)
    data_ref = ultima_atualizacao or "—"
    sem_preco = [tk for tk, info in prices.items() if info.get("preco") is None]
    sem_preco_str = f" | Sem preço: {', '.join(sem_preco)}" if sem_preco else ""
    st.markdown(f"""
    <div style="background:#0D1B2A;border:1px solid #1A3550;border-left:3px solid #F0B429;
                border-radius:6px;padding:12px 16px;font-family:monospace;font-size:11px;color:#7A9BB5">
        ⚠ <strong style="color:#F0B429">Preços atualizados manualmente na planilha.</strong>
        Última referência: <span style="color:#E8F4FD">{data_ref}</span>{sem_preco_str}<br>
        <span style="color:#4A6B85">Para preços em tempo real seria necessário plano pago da brapi.dev — não habilitado nesta versão.
        Edite a coluna <em>Preço Atual R$</em> na aba Carteira da planilha e recarregue o dashboard.</span>
    </div>
    """, unsafe_allow_html=True)

    # Erros de parsing
    erros = portfolio_result.get("erros", [])
    if erros:
        with st.expander(f"⚠ {len(erros)} linha(s) ignorada(s) na aba Operações"):
            for e in erros:
                st.markdown(f'<span style="color:#FF9800;font-size:12px;font-family:monospace;">{e}</span>',
                            unsafe_allow_html=True)
