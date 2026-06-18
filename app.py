"""
Dashboard de Carteira de Investimentos
Streamlit + Google Sheets + brapi.dev
"""

import streamlit as st
import pandas as pd
from datetime import datetime

# ── Page config ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Carteira · Investimentos",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS global — tema tech azul escuro ───────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&display=swap');

/* Fundo principal */
html, body, [data-testid="stApp"], .main, .block-container {
    background-color: #0A0F1E !important;
    color: #E8F4FD !important;
    font-family: 'DM Mono', monospace !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #070C17 !important;
    border-right: 1px solid #1A3550 !important;
}
[data-testid="stSidebar"] * { color: #7A9BB5 !important; }
[data-testid="stSidebar"] .stRadio label { color: #E8F4FD !important; }

/* Títulos */
h1, h2, h3 {
    color: #00D4FF !important;
    font-family: 'DM Mono', monospace !important;
    letter-spacing: 1px;
    font-weight: 500;
}
h2 { border-bottom: 1px solid #1A3550; padding-bottom: 8px; }

/* Inputs / Selects */
input, textarea, select,
[data-baseweb="input"] input,
[data-baseweb="select"] * {
    background-color: #0D1B2A !important;
    color: #E8F4FD !important;
    border-color: #1A3550 !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 13px !important;
}
[data-baseweb="input"] {
    border-color: #1A3550 !important;
}

/* Botão primário */
button[kind="primary"], .stButton button[kind="primary"] {
    background: linear-gradient(135deg, #0099CC, #006699) !important;
    color: #E8F4FD !important;
    border: 1px solid #00D4FF33 !important;
    font-family: 'DM Mono', monospace !important;
    letter-spacing: 1px;
    border-radius: 6px;
}
button[kind="primary"]:hover {
    background: linear-gradient(135deg, #00B3EE, #0080BB) !important;
}

/* Botão secundário */
.stButton button {
    background: #0D1B2A !important;
    color: #7A9BB5 !important;
    border: 1px solid #1A3550 !important;
    font-family: 'DM Mono', monospace !important;
    border-radius: 6px;
}

/* Checkbox */
[data-testid="stCheckbox"] label { color: #7A9BB5 !important; font-size: 12px; }

/* Selectbox label */
[data-testid="stSelectbox"] label,
[data-testid="stDateInput"] label,
[data-testid="stNumberInput"] label,
[data-testid="stTextInput"] label {
    color: #7A9BB5 !important;
    font-size: 11px !important;
    letter-spacing: 1px;
    text-transform: uppercase;
}

/* Form */
[data-testid="stForm"] {
    background: #0D1B2A !important;
    border: 1px solid #1A3550 !important;
    border-radius: 8px;
    padding: 20px;
}

/* Expander */
[data-testid="stExpander"] {
    background: #0D1B2A !important;
    border: 1px solid #1A3550 !important;
}

/* Info / Warning / Error */
.stAlert { border-radius: 6px !important; }
[data-testid="stAlert"][data-baseweb="notification"] {
    background: #0D1B2A !important;
}

/* Divider */
hr { border-color: #1A3550 !important; margin: 24px 0; }

/* Metric numbers */
[data-testid="stMetricValue"] {
    color: #00D4FF !important;
    font-family: 'DM Mono', monospace !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #070C17; }
::-webkit-scrollbar-thumb { background: #1A3550; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #00D4FF55; }

/* Remove padding extra do block container */
.block-container { padding-top: 1.5rem !important; }
</style>
""", unsafe_allow_html=True)


# ── Imports internos (após set_page_config) ──────────────────────
from data.sheets_client import (
    get_operacoes, get_carteira_estatica,
    get_patrimonio, get_historico_diario,
)
from data.portfolio_calc import calc_portfolio
from data.price_source import carregar_precos_atuais, data_mais_antiga
from data.snapshot_diario import salvar_snapshot, get_historico
from components import resumo_executivo, detalhe_ativos, relatorios, nova_operacao


# ── Sidebar ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:16px 0 24px">
        <div style="color:#00D4FF;font-size:18px;font-family:'DM Mono',monospace;font-weight:500;letter-spacing:2px">📈 CARTEIRA</div>
        <div style="color:#1A3550;font-size:10px;font-family:monospace;margin-top:2px">SISTEMA DE INVESTIMENTOS</div>
    </div>
    """, unsafe_allow_html=True)

    pagina = st.radio(
        "Navegar",
        ["Resumo Executivo", "Detalhe dos Ativos", "Relatórios", "Lançar Operação"],
        label_visibility="collapsed",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("⟳ Recarregar dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("""
    <div style="margin-top:40px;color:#1A3550;font-size:10px;font-family:monospace">
        Preços: manual (planilha)<br>
        Dados: Google Sheets<br>
        Cache: 5min
    </div>
    """, unsafe_allow_html=True)


# ── Carregamento de dados ─────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_all_data():
    df_ops    = get_operacoes()
    df_cart   = get_carteira_estatica()
    df_pat    = get_patrimonio()
    return df_ops, df_cart, df_pat


with st.spinner("Carregando dados..."):
    try:
        df_ops, df_cart_estatica, df_patrimonio = load_all_data()
        data_ok = True
    except Exception as e:
        st.error(f"Erro ao conectar ao Google Sheets: {e}")
        st.markdown("""
        <div style="background:#0D1B2A;border:1px solid #FF525233;border-radius:8px;padding:20px;color:#7A9BB5;font-family:monospace;font-size:12px">
            Verifique:<br>
            • Credenciais em <code>.streamlit/secrets.toml</code><br>
            • Planilha compartilhada com a Service Account<br>
            • Conexão com a internet
        </div>
        """, unsafe_allow_html=True)
        st.stop()

# Calcular portfólio
portfolio_result = calc_portfolio(df_ops)
positions = portfolio_result.get("positions", {})

# Carregar preços manuais da planilha (sem chamada de rede)
prices: dict = carregar_precos_atuais(df_cart_estatica)
ultima_atualizacao= data_mais_antiga(prices)

# Montar df_carteira calculado (para relatórios)
cart_rows = []
for _, row in df_cart_estatica.iterrows():
    tk = str(row.get("TICKER", "")).upper()
    pos = positions.get(tk)
    qtd = pos["qtd"] if pos else 0.0
    pm  = pos["preco_medio"] if pos else 0.0
    ti  = pos["total_investido"] if pos else 0.0
    pa  = prices.get(tk, {}).get("preco")
    va  = qtd * pa if pa and qtd > 0 else ti
    cart_rows.append({
        "TICKER": tk,
        "EMPRESA": row.get("EMPRESA", ""),
        "SETOR": row.get("SETOR", ""),
        "DY% 12m": row.get("DY% 12m", 0),
        "Qtd Cotas": qtd,
        "Preço Médio R$": pm,
        "Total Investido R$": ti,
        "Preço Atual R$": pa,
        "Valor Atual R$": va,
        "Result. R$": va - ti,
        "Result. %": ((va - ti) / ti * 100) if ti > 0 else 0.0,
    })

df_carteira_calculada = pd.DataFrame(cart_rows)

# Snapshot diário (grava silenciosamente)
try:
    valor_acoes = df_carteira_calculada["Valor Atual R$"].sum()
    salvar_snapshot(valor_acoes, df_patrimonio)
except Exception:
    pass  # não quebrar o dashboard se o snapshot falhar

# Histórico
df_hist = get_historico()


# ── Roteamento de páginas ─────────────────────────────────────────
if pagina == "Resumo Executivo":
    resumo_executivo.render(portfolio_result, df_carteira_calculada,
                            df_patrimonio, prices, ultima_atualizacao)

elif pagina == "Detalhe dos Ativos":
    detalhe_ativos.render(portfolio_result, df_cart_estatica, prices)

elif pagina == "Relatórios":
    relatorios.render(df_carteira_calculada, df_patrimonio, df_hist)

elif pagina == "Lançar Operação":
    nova_operacao.render(df_cart_estatica)
