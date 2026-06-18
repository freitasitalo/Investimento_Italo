"""
Reconstrução de posição, preço médio e resultado realizado
a partir do histórico de Operações (custo médio — regra RF brasileira).
"""

from __future__ import annotations
from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime, date


def _parse_number(val) -> Optional[float]:
    """
    Converte para float tratando formatos brasileiros e tipos nativos.
      9.5        -> 9.5
      "9,50"     -> 9.5
      "1.234,56" -> 1234.56
      "R$ 9,50"  -> 9.5
      None / ""  -> None
    """
    if val is None or val == "":
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        if pd.isna(val):
            return None
        return float(val)
    s = str(val).strip()
    for sym in ("R$", "$", "€", "\xa3"):
        s = s.replace(sym, "")
    s = s.strip()
    if s == "" or s.lower() in ("nan", "none", "-"):
        return None
    if "." in s and "," in s:
        # ponto = milhar, virgula = decimal  (formato BR: "1.234,56")
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        # so virgula = decimal  (formato BR: "9,50")
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _parse_date(val) -> Optional[date]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, (int, float)):
        # serial do Excel/Sheets
        try:
            return (pd.Timestamp("1899-12-30") + pd.Timedelta(days=int(val))).date()
        except Exception:
            return None
    if isinstance(val, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(val.strip(), fmt).date()
            except ValueError:
                continue
    return None


def calc_portfolio(df_ops: pd.DataFrame) -> Dict:
    """
    Recebe DataFrame com colunas:
        Data | Ticker | Empresa | Tipo C/V | Qtd | Preco R$ | Total R$ | Observacao

    Retorna dict:
        positions                 -> {ticker: {qtd, preco_medio, total_investido, resultado_realizado}}
        resultado_total_realizado -> float
        erros                     -> [str]
    """
    positions = {}
    resultado_total = 0.0
    erros = []

    required = {"Ticker", "Tipo C/V", "Qtd", "Preco R$"}
    # Aceita tanto "Preço R$" (com acento) quanto "Preco R$" (sem acento)
    col_preco = None
    for candidate in ("Preço R$", "Preco R$", "PRECO R$", "preco r$"):
        if candidate in df_ops.columns:
            col_preco = candidate
            break

    if col_preco is None or "Ticker" not in df_ops.columns:
        missing = []
        if "Ticker" not in df_ops.columns:
            missing.append("Ticker")
        if col_preco is None:
            missing.append("Preço R$")
        return {"positions": {}, "resultado_total_realizado": 0.0,
                "erros": ["Colunas ausentes: " + str(missing)]}

    df = df_ops.copy()
    df["_data_parsed"] = df["Data"].apply(_parse_date)
    df = df.sort_values("_data_parsed", na_position="last")

    for idx, row in df.iterrows():
        ticker = str(row.get("Ticker", "")).strip().upper()
        tipo = str(row.get("Tipo C/V", "")).strip().upper()
        qtd_raw = row.get("Qtd")
        preco_raw = row.get(col_preco)

        if not ticker:
            erros.append("Linha %d: Ticker vazio - ignorada" % (idx + 2))
            continue

        if qtd_raw is None or qtd_raw == "":
            erros.append("Linha %d (%s): Qtd vazia - ignorada" % (idx + 2, ticker))
            continue
        if isinstance(qtd_raw, float) and pd.isna(qtd_raw):
            erros.append("Linha %d (%s): Qtd vazia - ignorada" % (idx + 2, ticker))
            continue

        qtd = _parse_number(qtd_raw)
        if qtd is None:
            erros.append("Linha %d (%s): Qtd invalida '%s' - ignorada" % (idx + 2, ticker, qtd_raw))
            continue

        preco = _parse_number(preco_raw) if preco_raw not in (None, "", "nan") else 0.0
        if preco is None:
            erros.append("Linha %d (%s): Preco invalido '%s' - ignorada" % (idx + 2, ticker, preco_raw))
            continue

        if qtd <= 0:
            erros.append("Linha %d (%s): Qtd <= 0 - ignorada" % (idx + 2, ticker))
            continue

        total = qtd * preco  # sempre recalculado; ignora coluna Total R$

        if ticker not in positions:
            positions[ticker] = {
                "empresa": str(row.get("Empresa", "")).strip(),
                "qtd": 0.0,
                "preco_medio": 0.0,
                "total_investido": 0.0,
                "resultado_realizado": 0.0,
            }

        pos = positions[ticker]

        if tipo == "C":
            novo_total = pos["qtd"] * pos["preco_medio"] + total
            pos["qtd"] += qtd
            pos["preco_medio"] = novo_total / pos["qtd"] if pos["qtd"] > 0 else 0.0
            pos["total_investido"] = pos["qtd"] * pos["preco_medio"]

        elif tipo == "V":
            if qtd > pos["qtd"]:
                erros.append(
                    "Linha %d (%s): Venda de %g > posicao %g - ignorada"
                    % (idx + 2, ticker, qtd, pos["qtd"])
                )
                continue
            resultado = qtd * (preco - pos["preco_medio"])
            pos["resultado_realizado"] += resultado
            resultado_total += resultado
            pos["qtd"] -= qtd
            pos["total_investido"] = pos["qtd"] * pos["preco_medio"]
            if pos["qtd"] <= 0:
                pos["qtd"] = 0.0
                pos["preco_medio"] = 0.0
                pos["total_investido"] = 0.0

        else:
            erros.append("Linha %d (%s): Tipo '%s' desconhecido - ignorada" % (idx + 2, ticker, tipo))

    return {
        "positions": positions,
        "resultado_total_realizado": resultado_total,
        "erros": erros,
    }


def get_available_qty(ticker: str, df_ops: pd.DataFrame) -> float:
    result = calc_portfolio(df_ops)
    pos = result["positions"].get(ticker.upper())
    return pos["qtd"] if pos else 0.0
