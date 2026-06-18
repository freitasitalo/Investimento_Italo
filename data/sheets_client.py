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

SHEET_ID = "1BGqSvBGNV-UBGRXc9tq_yR_7VwW3dUbjXF2umkohRLU"

ABA_OPERACOES  = "📋 Operações"
ABA_CARTEIRA   = "📊 Carteira"
ABA_PATRIMONIO = "💰 Patrimônio"
ABA_HISTORICO  = "📈 Histórico Diário"


@st.cache_resource(show_spinner=False)
def _get_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_sheet():
    client = _get_client()
    return client.open_by_key(SHEET_ID)


# ── Leitura ────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def get_operacoes() -> pd.DataFrame:
    ws = _get_sheet().worksheet(ABA_OPERACOES)
    # UNFORMATTED_VALUE retorna o número bruto (9.5) em vez do texto formatado ("9,50")
    records = ws.get_all_records(
        expected_headers=[
            "Data", "Ticker", "Empresa", "Tipo C/V", "Qtd", "Preço R$", "Total R$", "Observação"
        ],
        value_render_option="UNFORMATTED_VALUE",
    )
    return pd.DataFrame(records) if records else pd.DataFrame(
        columns=["Data", "Ticker", "Empresa", "Tipo C/V", "Qtd", "Preço R$", "Total R$", "Observação"]
    )


@st.cache_data(ttl=300, show_spinner=False)
def get_carteira_estatica() -> pd.DataFrame:
    """
    Retorna colunas estáticas do cadastro + preço manual do usuário:
    TICKER, EMPRESA, SETOR, DY% 12m, Preço Atual R$, Data Atualização Preço
    """
    ws = _get_sheet().worksheet(ABA_CARTEIRA)
    records = ws.get_all_records()
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(columns=[
            "TICKER", "EMPRESA", "SETOR", "DY% 12m",
            "Preço Atual R$", "Data Atualização Preço",
        ])
    cols = [c for c in [
        "TICKER", "EMPRESA", "SETOR", "DY% 12m",
        "Preço Atual R$", "Data Atualização Preço",
    ] if c in df.columns]
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


def atualizar_preco_carteira(ticker: str, preco: float) -> None:
    """
    Atualiza 'Preco Atual R$' e 'Data Atualizacao Preco' para o ticker
    na aba Carteira. Encontra a linha pelo TICKER (coluna A) e atualiza
    as colunas correspondentes pelo nome do cabecalho.
    Raises ValueError se o ticker nao for encontrado.
    """
    ws = _get_sheet().worksheet(ABA_CARTEIRA)
    headers = ws.row_values(1)

    # Localiza indices das colunas (1-based para gspread)
    try:
        col_ticker = headers.index("TICKER") + 1
    except ValueError:
        raise ValueError("Coluna TICKER nao encontrada na aba Carteira")

    col_preco = None
    col_data  = None
    for i, h in enumerate(headers, 1):
        if h in ("Preco Atual R$", "Preço Atual R$"):
            col_preco = i
        if h in ("Data Atualizacao Preco", "Data Atualização Preço"):
            col_data = i

    if col_preco is None:
        raise ValueError("Coluna 'Preco Atual R$' nao encontrada na aba Carteira")

    # Encontra a linha do ticker
    ticker_col_vals = ws.col_values(col_ticker)
    row_idx = None
    for i, val in enumerate(ticker_col_vals[1:], start=2):
        if str(val).strip().upper() == ticker.upper():
            row_idx = i
            break

    if row_idx is None:
        raise ValueError("Ticker %s nao encontrado na aba Carteira" % ticker)

    from gspread.utils import rowcol_to_a1
    hoje = date.today().strftime("%d/%m/%Y")

    # Envia como string BR ("39,18") + USER_ENTERED para o Sheets interpretar
    # conforme a locale pt-BR da planilha (vírgula = decimal)
    preco_br = ("%.2f" % preco).replace(".", ",")
    col_preco_a1 = rowcol_to_a1(row_idx, col_preco)
    ws.update([[preco_br]], col_preco_a1, value_input_option="USER_ENTERED")

    if col_data:
        col_data_a1 = rowcol_to_a1(row_idx, col_data)
        ws.update([[hoje]], col_data_a1, value_input_option="USER_ENTERED")

    get_carteira_estatica.clear()


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
