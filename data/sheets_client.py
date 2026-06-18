"""
Autenticação e leitura/escrita no Google Sheets via gspread.
"""

from __future__ import annotations
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import date, datetime


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_NAME = "Carteira_Investimentos"

ABA_OPERACOES = "📋 Operações"
ABA_CARTEIRA  = "📊 Carteira"
ABA_PATRIMONIO = "💰 Patrimônio"
ABA_HISTORICO  = "📈 Histórico Diário"


@st.cache_resource(show_spinner=False)
def _get_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_sheet():
    client = _get_client()
    return client.open(SHEET_NAME)


# ── Leitura ────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def get_operacoes() -> pd.DataFrame:
    ws = _get_sheet().worksheet(ABA_OPERACOES)
    records = ws.get_all_records(expected_headers=[
        "Data", "Ticker", "Empresa", "Tipo C/V", "Qtd", "Preço R$", "Total R$", "Observação"
    ])
    return pd.DataFrame(records) if records else pd.DataFrame(
        columns=["Data", "Ticker", "Empresa", "Tipo C/V", "Qtd", "Preço R$", "Total R$", "Observação"]
    )


@st.cache_data(ttl=300, show_spinner=False)
def get_carteira_estatica() -> pd.DataFrame:
    """Retorna apenas TICKER, EMPRESA, SETOR, DY% 12m — colunas estáticas do cadastro."""
    ws = _get_sheet().worksheet(ABA_CARTEIRA)
    records = ws.get_all_records()
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(columns=["TICKER", "EMPRESA", "SETOR", "DY% 12m"])
    cols = [c for c in ["TICKER", "EMPRESA", "SETOR", "DY% 12m"] if c in df.columns]
    return df[cols]


@st.cache_data(ttl=300, show_spinner=False)
def get_patrimonio() -> pd.DataFrame:
    ws = _get_sheet().worksheet(ABA_PATRIMONIO)
    records = ws.get_all_records()
    return pd.DataFrame(records) if records else pd.DataFrame(
        columns=["Categoria", "Valor R$", "% do Total", "Observação"]
    )


@st.cache_data(ttl=60, show_spinner=False)
def get_historico_diario() -> pd.DataFrame:
    ws = _get_sheet().worksheet(ABA_HISTORICO)
    records = ws.get_all_records()
    return pd.DataFrame(records) if records else pd.DataFrame(
        columns=["Data", "Valor Total Ações", "Valor Total RF", "Patrimônio Total"]
    )


# ── Escrita ────────────────────────────────────────────────────────

def append_operacao(data: date, ticker: str, empresa: str, tipo: str,
                    qtd: float, preco: float, obs: str = "") -> None:
    total = round(qtd * preco, 2)
    ws = _get_sheet().worksheet(ABA_OPERACOES)
    row = [
        data.strftime("%Y-%m-%d"),
        ticker.upper(),
        empresa,
        tipo.upper(),
        qtd,
        round(preco, 2),
        total,
        obs,
    ]
    ws.append_row(row, value_input_option="USER_ENTERED")
    st.cache_data.clear()


def upsert_historico_diario(valor_acoes: float, valor_rf: float, patrimonio_total: float) -> None:
    ws = _get_sheet().worksheet(ABA_HISTORICO)
    hoje = date.today().strftime("%Y-%m-%d")
    records = ws.get_all_values()

    # Procura linha com a data de hoje
    row_idx = None
    for i, row in enumerate(records[1:], start=2):  # skip header
        if row and row[0] == hoje:
            row_idx = i
            break

    new_row = [hoje, round(valor_acoes, 2), round(valor_rf, 2), round(patrimonio_total, 2)]

    if row_idx:
        ws.update(f"A{row_idx}:D{row_idx}", [new_row])
    else:
        ws.append_row(new_row, value_input_option="USER_ENTERED")

    get_historico_diario.clear()
