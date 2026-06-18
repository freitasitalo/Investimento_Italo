"""
Fonte de precos atual: leitura direta da coluna 'Preco Atual R$'
na aba Carteira do Google Sheets - preenchida manualmente pelo usuario.
Nenhuma chamada de rede aqui.
"""

from __future__ import annotations
from typing import Dict, Optional, Tuple
from datetime import date, datetime
import pandas as pd


def carregar_precos_atuais(df_carteira: pd.DataFrame) -> Dict[str, dict]:
    """
    Le as colunas 'Preco Atual R$' e 'Data Atualizacao Preco' do DataFrame
    da aba Carteira e retorna um dict por ticker.

    Retorno:
    {
        "ITSA4": {
            "preco": 13.07,
            "data_atualizacao": "18/06/2026",
            "dias_defasagem": 0,
            "erro": None,
        },
        ...
    }
    """
    result = {}

    if df_carteira.empty or "TICKER" not in df_carteira.columns:
        return result

    # Aceita nomes de coluna com ou sem acento
    col_preco = _find_col(df_carteira, ["Preço Atual R$", "Preco Atual R$"])
    col_data  = _find_col(df_carteira, ["Data Atualização Preço", "Data Atualizacao Preco"])

    for _, row in df_carteira.iterrows():
        ticker = str(row.get("TICKER", "")).strip().upper()
        if not ticker:
            continue

        # Preco
        preco_raw = row.get(col_preco) if col_preco else None
        preco = None
        erro = None
        if preco_raw is not None and preco_raw != "":
            parsed = _to_float(preco_raw)
            if parsed is not None and parsed > 0:
                preco = parsed
            elif parsed is not None and parsed <= 0:
                erro = "Preco invalido (<= 0) - atualize na planilha"
            else:
                erro = "Preco nao numerico - atualize na planilha"
        else:
            erro = "Preco nao preenchido - atualize na planilha"

        # Data
        data_raw = row.get(col_data) if col_data else None
        data_str = None
        dias = None
        if data_raw is not None and data_raw != "":
            data_str = str(data_raw).strip()
            dias = dias_desde_atualizacao(data_str)

        result[ticker] = {
            "preco": preco,
            "data_atualizacao": data_str,
            "dias_defasagem": dias,
            "erro": erro,
        }

    return result


def dias_desde_atualizacao(data_str):
    # type: (Optional[str]) -> Optional[int]
    """Dias desde a ultima atualizacao manual. Retorna None se nao parseavel."""
    if not data_str:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            dt = datetime.strptime(data_str.strip(), fmt).date()
            return (date.today() - dt).days
        except ValueError:
            continue
    return None


def status_preco(info: dict) -> Tuple[str, str]:
    """
    Retorna (icone, mensagem) baseado nos dias de defasagem:
      preco=None   -> (bola preta, motivo)
      0-7 dias     -> ("", "")  sem aviso
      8-30 dias    -> aviso leve amarelo
      31+ dias     -> aviso vermelho
    """
    preco = info.get("preco")
    dias = info.get("dias_defasagem")
    erro = info.get("erro")

    if preco is None:
        return "⚫", erro or "Sem preco"
    if dias is None:
        return "⚪", "Data de atualizacao nao informada"
    if dias <= 7:
        return "", ""
    if dias <= 30:
        return "⚠", "Atualizado ha %d dias" % dias
    return "\U0001f534", "Atualizado ha %d dias - atualize na planilha" % dias


def data_mais_antiga(prices: Dict[str, dict]) -> Optional[str]:
    """Data mais antiga entre os tickers com preco preenchido."""
    datas = []
    for info in prices.values():
        if info.get("preco") is not None and info.get("data_atualizacao"):
            d = _parse_data(info["data_atualizacao"])
            if d:
                datas.append(d)
    if not datas:
        return None
    return min(datas).strftime("%d/%m/%Y")


# ── Helpers ────────────────────────────────────────────────────────

def _find_col(df: pd.DataFrame, candidates) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _to_float(val) -> Optional[float]:
    if val is None or val == "":
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        try:
            if pd.isna(val):
                return None
        except Exception:
            pass
        return float(val)
    s = str(val).strip().replace("R$", "").replace("$", "").strip()
    if not s or s.lower() in ("nan", "none", "-"):
        return None
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _parse_data(s: str) -> Optional[date]:
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None
