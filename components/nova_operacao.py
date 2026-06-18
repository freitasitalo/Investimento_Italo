"""
Página 4 — Formulário de lançamento de nova operação.
"""

from __future__ import annotations
import streamlit as st
import pandas as pd
from datetime import date
from data.portfolio_calc import calc_portfolio, get_available_qty
from data.sheets_client import append_operacao, get_operacoes


def render(df_carteira_estatica: pd.DataFrame):
    st.markdown("## Lançar Nova Operação")

    # Lista de tickers cadastrados
    tickers_cadastrados = []
    empresa_map: dict[str, str] = {}
    if not df_carteira_estatica.empty:
        tickers_cadastrados = sorted(df_carteira_estatica["TICKER"].dropna().str.upper().tolist())
        for _, row in df_carteira_estatica.iterrows():
            empresa_map[str(row.get("TICKER", "")).upper()] = str(row.get("EMPRESA", ""))

    st.markdown("""
    <div style="background:#0D1B2A;border:1px solid #1A3550;border-radius:8px;padding:16px 20px;margin-bottom:20px">
        <span style="color:#7A9BB5;font-size:11px;font-family:monospace">
        Nova linha será adicionada à aba <span style="color:#00D4FF">📋 Operações</span> no Google Sheets.
        O cálculo de preço médio e posição é atualizado automaticamente após gravação.
        </span>
    </div>
    """, unsafe_allow_html=True)

    with st.form("form_nova_operacao", clear_on_submit=False):
        col1, col2 = st.columns(2)

        data_op = col1.date_input("Data da operação", value=date.today(),
                                   max_value=date.today())
        tipo = col2.selectbox("Tipo", ["Compra", "Venda"])

        col3, col4 = st.columns([2, 1])
        usar_livre = col3.checkbox("Ticker não cadastrado (campo livre)")

        if usar_livre:
            ticker_raw = col3.text_input("Ticker", placeholder="Ex: MGLU3").upper().strip()
            empresa = col4.text_input("Empresa", placeholder="Nome da empresa")
        else:
            if tickers_cadastrados:
                ticker_raw = col3.selectbox("Ticker", tickers_cadastrados)
                empresa = empresa_map.get(ticker_raw, "")
                col4.markdown(f"""
                <div style="margin-top:28px;color:#7A9BB5;font-size:12px;font-family:monospace">{empresa}</div>
                """, unsafe_allow_html=True)
            else:
                ticker_raw = col3.text_input("Ticker (nenhum cadastrado ainda)")
                empresa = col4.text_input("Empresa")

        col5, col6 = st.columns(2)
        qtd = col5.number_input("Quantidade", min_value=1, step=1, value=1)
        preco = col6.number_input("Valor unitário (R$)", min_value=0.01, step=0.01,
                                   format="%.2f", value=0.01)

        obs = st.text_input("Observação (opcional)", "")

        submitted = st.form_submit_button("Pré-visualizar operação →",
                                          use_container_width=True)

    if not submitted:
        return

    # ── Validações ──────────────────────────────────────────────
    ticker = ticker_raw.upper().strip() if ticker_raw else ""
    erros_val: list[str] = []

    if not ticker:
        erros_val.append("Ticker não pode ser vazio.")
    if qtd <= 0:
        erros_val.append("Quantidade deve ser maior que zero.")
    if preco <= 0:
        erros_val.append("Valor unitário deve ser maior que zero.")

    qtd_disponivel = 0.0
    if tipo == "Venda" and ticker:
        df_ops = get_operacoes()
        qtd_disponivel = get_available_qty(ticker, df_ops)
        if qtd > qtd_disponivel:
            erros_val.append(
                f"Venda de {qtd} cotas inválida — posição atual de {ticker}: **{qtd_disponivel:.0f} cotas**."
            )

    if erros_val:
        for e in erros_val:
            st.error(e)
        return

    # ── Preview de confirmação ───────────────────────────────────
    total = round(qtd * preco, 2)
    def brl(v):
        return f"R$ {v:,.2f}".replace(",","X").replace(".",",").replace("X",".")

    qtd_restante_str = ""
    if tipo == "Venda":
        restante = qtd_disponivel - qtd
        qtd_restante_str = f" → saldo após venda: **{restante:.0f} cotas**"

    cor_tipo = "#00E676" if tipo == "Compra" else "#FF5252"

    st.markdown(f"""
    <div style="background:#0D1B2A;border:1px solid #1A3550;border-radius:8px;padding:20px 24px;margin:16px 0">
        <div style="color:#7A9BB5;font-size:10px;letter-spacing:2px;font-family:monospace;margin-bottom:12px">CONFIRMAR OPERAÇÃO</div>
        <div style="display:flex;gap:32px;flex-wrap:wrap">
            <div>
                <div style="color:#4A6B85;font-size:10px;font-family:monospace">TIPO</div>
                <div style="color:{cor_tipo};font-size:16px;font-family:monospace;font-weight:600">{tipo.upper()}</div>
            </div>
            <div>
                <div style="color:#4A6B85;font-size:10px;font-family:monospace">TICKER</div>
                <div style="color:#00D4FF;font-size:16px;font-family:monospace;font-weight:600">{ticker}</div>
            </div>
            <div>
                <div style="color:#4A6B85;font-size:10px;font-family:monospace">QUANTIDADE</div>
                <div style="color:#E8F4FD;font-size:16px;font-family:monospace">{qtd:,}</div>
            </div>
            <div>
                <div style="color:#4A6B85;font-size:10px;font-family:monospace">PREÇO UNIT.</div>
                <div style="color:#E8F4FD;font-size:16px;font-family:monospace">{brl(preco)}</div>
            </div>
            <div>
                <div style="color:#4A6B85;font-size:10px;font-family:monospace">TOTAL</div>
                <div style="color:#F0B429;font-size:20px;font-family:monospace;font-weight:700">{brl(total)}</div>
            </div>
        </div>
        <div style="color:#7A9BB5;font-size:12px;font-family:monospace;margin-top:10px">{qtd_restante_str}</div>
    </div>
    """, unsafe_allow_html=True)

    col_ok, col_cancel = st.columns([1, 1])

    if col_ok.button("✓ Confirmar e gravar", type="primary", use_container_width=True):
        try:
            append_operacao(
                data=data_op,
                ticker=ticker,
                empresa=empresa,
                tipo="C" if tipo == "Compra" else "V",
                qtd=float(qtd),
                preco=float(preco),
                obs=obs,
            )
            st.success(f"✓ Operação de {tipo.lower()} de **{qtd} {ticker}** a {brl(preco)} gravada com sucesso!")
            st.balloons()
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Erro ao gravar no Google Sheets: {e}")

    if col_cancel.button("✗ Cancelar", use_container_width=True):
        st.rerun()
