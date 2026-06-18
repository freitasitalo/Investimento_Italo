"""
Grava e lê o histórico diário de patrimônio no Google Sheets.
"""

from __future__ import annotations
import streamlit as st
from data.sheets_client import upsert_historico_diario, get_historico_diario
import pandas as pd


def salvar_snapshot(valor_acoes: float, df_patrimonio: pd.DataFrame) -> None:
    valor_rf = 0.0
    if not df_patrimonio.empty and "Categoria" in df_patrimonio.columns:
        for _, row in df_patrimonio.iterrows():
            if str(row.get("Categoria", "")) == "Renda Fixa / Tesouro":
                try:
                    valor_rf += float(row.get("Valor R$", 0) or 0)
                except (ValueError, TypeError):
                    pass

    patrimonio_total = valor_acoes + valor_rf
    upsert_historico_diario(valor_acoes, valor_rf, patrimonio_total)


def get_historico() -> pd.DataFrame:
    df = get_historico_diario()
    if df.empty:
        return df
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    for col in ["Valor Total Ações", "Valor Total RF", "Patrimônio Total"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("Data").reset_index(drop=True)

