"""
Reconstrução de posição, preço médio e resultado realizado
a partir do histórico de Operações (custo médio — regra RF brasileira).
"""

from __future__ import annotations
import pandas as pd
from datetime import datetime, date


def _parse_number(val) -> float | None:
    """
    Converte um valor para float tratando formatos brasileiros.
    - int/float nativos: retorna direto
    - "9,50"   → 9.5
    - "1.234,56" → 1234.56  (ponto = milhar, vírgula = decimal)
    - "R$ 9,50" → 9.5
    - "9.50"   → 9.5
    Retorna None se não for conversível.
    """
    if val is None or val == "":
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    # Remove símbolos de moeda e espaços
    for sym in ("R$", "$", "€", "£"):
        s = s.replace(sym, "")
    s = s.strip()
    if s == "" or s.lower() in ("nan", "none", "-"):
        return None
    # Detecta formato BR: tem ponto E vírgula → ponto é milhar, vírgula é decimal
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        # Só vírgula → é separador decimal (formato BR)
        s = s.replace(",", ".")
    # Só ponto → já é formato anglo (ex: "9.50") ou milhar sem decimal
    try:
        return float(s)
    except ValueError:
        return None


def _parse_date(val) -> date | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, (datetime, date)):
        return val.date() if isinstance(val, datetime) else val
    if isinstance(val, (int, float)):
        # Excel serial date
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


def calc_portfolio(df_ops: pd.DataFrame) -> dict:
    """
    Recebe DataFrame com colunas:
        Data | Ticker | Empresa | Tipo C/V | Qtd | Preço R$ | Total R$ | Observação

    Retorna dict com:
        positions       -> {ticker: {qtd, preco_medio, total_investido, resultado_realizado}}
        resultado_total_realizado -> float
        erros           -> [str]  linhas ignoradas com motivo
    """
    positions: dict[str, dict] = {}
    resultado_total = 0.0
    erros: list[str] = []

    required = {"Ticker", "Tipo C/V", "Qtd", "Preço R$"}
    missing = required - set(df_ops.columns)
    if missing:
        return {"positions": {}, "resultado_total_realizado": 0.0,
                "erros": [f"Colunas ausentes: {missing}"]}

    df = df_ops.copy()
    df["_data_parsed"] = df["Data"].apply(_parse_date)
    df = df.sort_values("_data_parsed", na_position="last")

    for idx, row in df.iterrows():
        ticker = str(row.get("Ticker", "")).strip().upper()
        tipo   = str(row.get("Tipo C/V", "")).strip().upper()
        qtd_raw = row.get("Qtd")
        preco_raw = row.get("Preço R$")

        # Validações
        if not ticker:
            erros.append(f"Linha {idx+2}: Ticker vazio — ignorada")
            continue
        if qtd_raw is None or (isinstance(qtd_raw, float) and pd.isna(qtd_raw)) or qtd_raw == "":
            erros.append(f"Linha {idx+2} ({ticker}): Qtd vazia — ignorada")
            continue

        qtd = _parse_number(qtd_raw)
        if qtd is None:
            erros.append(f"Linha {idx+2} ({ticker}): Qtd '{qtd_raw}' inválida — ignorada")
            continue

        preco = _parse_number(preco_raw) if preco_raw not in (None, "", "nan") else 0.0
        if preco is None:
            erros.append(f"Linha {idx+2} ({ticker}): Preço '{preco_raw}' inválido — ignorada")
            continue

        if qtd <= 0:
            erros.append(f"Linha {idx+2} ({ticker}): Qtd <= 0 — ignorada")
            continue

        total = qtd * preco  # recalcula sempre; ignora coluna Total R$

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
                    f"Linha {idx+2} ({ticker}): Venda de {qtd} > posição {pos['qtd']:.0f} — ignorada"
                )
                continue
            resultado = qtd * (float(preco) - pos["preco_medio"])
            pos["resultado_realizado"] += resultado
            resultado_total += resultado
            pos["qtd"] -= qtd
            pos["total_investido"] = pos["qtd"] * pos["preco_medio"]
            if pos["qtd"] <= 0:
                pos["qtd"] = 0.0
                pos["preco_medio"] = 0.0
                pos["total_investido"] = 0.0

        else:
            erros.append(f"Linha {idx+2} ({ticker}): Tipo '{tipo}' desconhecido — ignorada")

    # Remover posições zeradas do resultado final mas manter histórico de resultado realizado
    return {
        "positions": positions,
        "resultado_total_realizado": resultado_total,
        "erros": erros,
    }


def get_available_qty(ticker: str, df_ops: pd.DataFrame) -> float:
    result = calc_portfolio(df_ops)
    pos = result["positions"].get(ticker.upper())
    return pos["qtd"] if pos else 0.0
