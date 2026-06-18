"""
Busca preços atuais na brapi.dev com cache e fallback gracioso.
"""

from __future__ import annotations
import streamlit as st
import requests
from datetime import datetime


BRAPI_BASE = "https://brapi.dev/api/quote"
TIMEOUT = 10


def _brapi_token() -> str | None:
    try:
        return st.secrets.get("brapi_token") or st.secrets.get("BRAPI_TOKEN")
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_prices(tickers: tuple[str, ...]) -> dict[str, dict]:
    """
    Retorna {ticker: {preco, variacao_dia_pct, timestamp, erro}}
    Usa endpoint multi-ticker da brapi para minimizar requisições.
    """
    if not tickers:
        return {}

    token = _brapi_token()
    params = {}
    if token:
        params["token"] = token

    results: dict[str, dict] = {}

    # brapi suporta múltiplos tickers separados por vírgula
    joined = ",".join(tickers)
    url = f"{BRAPI_BASE}/{joined}"

    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("results", []):
            tk = item.get("symbol", "").upper()
            results[tk] = {
                "preco": item.get("regularMarketPrice"),
                "variacao_dia_pct": item.get("regularMarketChangePercent"),
                "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "erro": None,
            }
    except requests.exceptions.Timeout:
        for tk in tickers:
            results[tk] = _fallback(tk, "Timeout na brapi.dev")
    except requests.exceptions.RequestException as e:
        for tk in tickers:
            results[tk] = _fallback(tk, f"Erro de conexão: {e}")
    except Exception as e:
        for tk in tickers:
            results[tk] = _fallback(tk, f"Erro inesperado: {e}")

    # Para tickers que não vieram na resposta
    for tk in tickers:
        if tk not in results:
            results[tk] = _fallback(tk, "Ticker não encontrado na brapi.dev")

    return results


def _fallback(ticker: str, motivo: str) -> dict:
    return {
        "preco": None,
        "variacao_dia_pct": None,
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "erro": motivo,
    }


def get_prices_with_cache(tickers: list[str]) -> dict[str, dict]:
    """Wrapper que converte list -> tuple para compatibilidade com cache."""
    return fetch_prices(tuple(sorted(set(t.upper() for t in tickers))))
