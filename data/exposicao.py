"""
Cálculos de exposição por setor e RF vs RV.
"""

from __future__ import annotations
import pandas as pd


def calc_exposicao_setor(df_carteira: pd.DataFrame) -> pd.DataFrame:
    """
    df_carteira deve ter: SETOR, Valor Atual R$
    Retorna DataFrame com SETOR, Valor R$, % Setor
    """
    if df_carteira.empty or "SETOR" not in df_carteira.columns:
        return pd.DataFrame(columns=["SETOR", "Valor R$", "% Setor"])

    df = df_carteira[df_carteira["Valor Atual R$"] > 0].copy()
    agr = df.groupby("SETOR", as_index=False)["Valor Atual R$"].sum()
    agr.columns = ["SETOR", "Valor R$"]
    total = agr["Valor R$"].sum()
    agr["% Setor"] = (agr["Valor R$"] / total * 100).round(2) if total > 0 else 0.0
    return agr.sort_values("Valor R$", ascending=False).reset_index(drop=True)


def calc_exposicao_rfxrv(valor_rv: float, df_patrimonio: pd.DataFrame) -> dict:
    """
    valor_rv: soma do Valor Atual de todas as posições em ações
    df_patrimonio: DataFrame com Categoria e Valor R$
    Retorna dict com chaves: rv, rf, outros, total, pct_rv, pct_rf
    """
    rf = 0.0
    outros = 0.0

    if not df_patrimonio.empty and "Categoria" in df_patrimonio.columns:
        for _, row in df_patrimonio.iterrows():
            cat = str(row.get("Categoria", "")).strip()
            try:
                val = float(row.get("Valor R$", 0) or 0)
            except (ValueError, TypeError):
                val = 0.0

            if cat == "Ações B3 (Carteira)":
                continue  # usamos valor_rv calculado
            elif cat == "Renda Fixa / Tesouro":
                rf += val
            else:
                outros += val

    total = valor_rv + rf + outros
    return {
        "rv": valor_rv,
        "rf": rf,
        "outros": outros,
        "total": total,
        "pct_rv": round(valor_rv / total * 100, 2) if total > 0 else 0.0,
        "pct_rf": round(rf / total * 100, 2) if total > 0 else 0.0,
        "pct_outros": round(outros / total * 100, 2) if total > 0 else 0.0,
    }
