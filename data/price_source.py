"""
Fonte de preços atual: leitura direta da coluna 'Preço Atual R$'
na aba Carteira do Google Sheets — preenchida manualmente pelo usuário.
Nenhuma chamada de rede aqui.
"""

from __future__ import annotations
from datetime import date, datetime
import pandas as pd


def carregar_precos_atuais(df_carteira: pd.DataFrame) -> dict[str, dict]:
    """
    Lê as colunas 'Preço Atual R$' e 'Data Atualização Preço' do DataFrame
    da aba Carteira e retorna um dict por ticker.

    Formato de retorno:
    {
        "ITSA4": {
            "preco": 13.07,                  # None se vazio/inválido
            "data_atualizacao": "18/06/2026", # None se vazio
            "dias_defasagem": 0,              # None se data ausente
            "erro": None,                     # mensagem se preco=None
        },
        ...
    }
    """
    result: dict[str, dict] = {}

    if df_carteira.empty or "TICKER" not in df_carteira.columns:
        return result

    for _, row in df_carteira.iterrows():
        ticker = str(row.get("TICKER", "")).strip().upper()
        if not ticker:
            continue

        # Preço
        preco_raw = row.get("Preço Atual R$")
        preco: float | None = None
        erro: str | None = None
        if preco_raw is not None and preco_raw != "":
            try:
                preco = float(str(preco_raw).replace(",", "."))
                if preco <= 0:
                    preco = None
                    erro = "Preço inválido (≤ 0) — atualize na planilha"
            except (ValueError, TypeError):
                erro = "Preço não numérico — atualize na planilha"
        else:
            erro = "Preço não preenchido — atualize na planilha"

        # Data de atualização
        data_raw = row.get("Data Atualização Preço")
        data_str: str | None = None
        dias: int | None = None
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


def dias_desde_atualizacao(data_atualizacao_str: str | None) -> int | None:
    """
    Calcula quantos dias se passaram desde a última atualização manual.
    Aceita dd/mm/aaaa, aaaa-mm-dd e dd-mm-aaaa.
    Retorna None se a string for None ou não parseável.
    """
    if not data_atualizacao_str:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            dt = datetime.strptime(data_atualizacao_str.strip(), fmt).date()
            return (date.today() - dt).days
        except ValueError:
            continue
    return None


def status_preco(info: dict) -> tuple[str, str]:
    """
    Retorna (icone, mensagem) baseado nos dias de defasagem.
    Usado pelos componentes de exibição.

    Regras:
      - preco=None         → ⚫ sem preço
      - 0–7 dias           → sem aviso
      - 8–30 dias          → ⚠ aviso leve (amarelo)
      - 31+ dias           → 🔴 aviso visível (vermelho)
    """
    preco = info.get("preco")
    dias = info.get("dias_defasagem")
    erro = info.get("erro")

    if preco is None:
        return "⚫", erro or "Sem preço"
    if dias is None:
        return "⚪", "Data de atualização não informada"
    if dias <= 7:
        return "", ""
    if dias <= 30:
        return "⚠", f"Atualizado há {dias} dias"
    return "🔴", f"Atualizado há {dias} dias — atualize na planilha"


def data_mais_antiga(prices: dict[str, dict]) -> str | None:
    """
    Retorna a data de atualização mais antiga entre todos os tickers
    com preço preenchido. Usado no aviso geral do Resumo Executivo.
    """
    datas = []
    for info in prices.values():
        if info.get("preco") is not None and info.get("data_atualizacao"):
            d = _parse_data(info["data_atualizacao"])
            if d:
                datas.append(d)
    if not datas:
        return None
    mais_antiga = min(datas)
    return mais_antiga.strftime("%d/%m/%Y")


def _parse_data(s: str) -> date | None:
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None
