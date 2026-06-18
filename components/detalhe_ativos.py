"""
Página 2 — Tabela detalhada de ativos.
"""

import streamlit as st
import pandas as pd


def _fmt_brl(val) -> str:
    try:
        f = float(val)
        return f"R$ {f:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "—"


def _fmt_pct(val) -> str:
    try:
        f = float(val)
        sinal = "+" if f >= 0 else ""
        return f"{sinal}{f:.2f}%"
    except (TypeError, ValueError):
        return "—"


def _color_html(val, text) -> str:
    try:
        f = float(val)
        color = "#00E676" if f >= 0 else "#FF5252"
    except (TypeError, ValueError):
        color = "#E8F4FD"
    return f'<span style="color:{color}">{text}</span>'


def render(portfolio_result: dict, df_carteira_estatica: pd.DataFrame, prices: dict):
    st.markdown("## Detalhe dos Ativos")

    positions = portfolio_result.get("positions", {})

    if df_carteira_estatica.empty:
        st.info("Nenhum ativo cadastrado na aba Carteira do Google Sheets.")
        return

    rows = []
    for _, row in df_carteira_estatica.iterrows():
        tk = str(row.get("TICKER", "")).upper()
        pos = positions.get(tk)

        qtd = pos["qtd"] if pos else 0.0
        preco_medio = pos["preco_medio"] if pos else 0.0
        total_inv = pos["total_investido"] if pos else 0.0
        res_real = pos["resultado_realizado"] if pos else 0.0

        preco_info = prices.get(tk, {})
        preco_atual = preco_info.get("preco")
        tem_erro_preco = preco_info.get("erro") is not None

        valor_atual = (qtd * preco_atual) if preco_atual and qtd > 0 else total_inv
        resultado_r = valor_atual - total_inv
        resultado_pct = (resultado_r / total_inv * 100) if total_inv > 0 else 0.0
        pct_carteira = 0.0  # calculado depois

        rows.append({
            "Ticker": tk,
            "Empresa": str(row.get("EMPRESA", "")),
            "Setor": str(row.get("SETOR", "")),
            "Qtd": qtd,
            "Preço Médio": preco_medio,
            "Total Investido": total_inv,
            "Preço Atual": preco_atual,
            "Valor Atual": valor_atual,
            "Result. R$": resultado_r,
            "Result. %": resultado_pct,
            "DY% 12m": row.get("DY% 12m", ""),
            "Preço Desatualizado": tem_erro_preco and qtd > 0,
        })

    df = pd.DataFrame(rows)

    # % na carteira
    total_rv = df[df["Qtd"] > 0]["Valor Atual"].sum()
    df["% Carteira"] = df["Valor Atual"].apply(
        lambda v: round(v / total_rv * 100, 2) if total_rv > 0 else 0.0
    )

    # Aviso preços desatualizados
    desatual = df[df["Preço Desatualizado"]]
    if not desatual.empty:
        tks = ", ".join(desatual["Ticker"].tolist())
        st.warning(f"⚠ Preço pode estar desatualizado — fonte indisponível: **{tks}**")

    # Filtros
    col_f1, col_f2 = st.columns([2, 1])
    setores = ["Todos"] + sorted(df["Setor"].unique().tolist())
    setor_sel = col_f1.selectbox("Filtrar por setor", setores)
    apenas_posicao = col_f2.checkbox("Apenas com posição", value=True)

    df_vis = df.copy()
    if setor_sel != "Todos":
        df_vis = df_vis[df_vis["Setor"] == setor_sel]
    if apenas_posicao:
        df_vis = df_vis[df_vis["Qtd"] > 0]

    if df_vis.empty:
        st.info("Nenhum ativo para exibir com os filtros aplicados.")
        return

    # Renderizar tabela HTML estilizada
    html_rows = ""
    for _, r in df_vis.iterrows():
        def brl(v):
            try: return f"R$ {float(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")
            except: return "—"
        def pct(v):
            try:
                f = float(v)
                c = "#00E676" if f >= 0 else "#FF5252"
                s = "+" if f >= 0 else ""
                return f'<span style="color:{c}">{s}{f:.2f}%</span>'
            except: return "—"

        pa_str = brl(r["Preço Atual"]) if r["Preço Atual"] else '<span style="color:#FF9800">—*</span>'
        res_html = f'<span style="color:{"#00E676" if r["Result. R$"]>=0 else "#FF5252"}">{brl(r["Result. R$"])}</span>'

        html_rows += f"""<tr>
            <td style="color:#00D4FF;font-weight:600">{r['Ticker']}</td>
            <td>{r['Empresa']}</td>
            <td style="color:#7A9BB5">{r['Setor']}</td>
            <td style="text-align:right">{int(r['Qtd']) if r['Qtd'] > 0 else '—'}</td>
            <td style="text-align:right">{brl(r['Preço Médio'])}</td>
            <td style="text-align:right">{brl(r['Total Investido'])}</td>
            <td style="text-align:right">{pa_str}</td>
            <td style="text-align:right">{brl(r['Valor Atual'])}</td>
            <td style="text-align:right">{res_html}</td>
            <td style="text-align:right">{pct(r['Result. %'])}</td>
            <td style="text-align:right;color:#F0B429">{r['DY% 12m']}%</td>
            <td style="text-align:right;color:#7A9BB5">{r['% Carteira']:.1f}%</td>
        </tr>"""

    th_style = "padding:10px 12px;text-align:right;color:#00D4FF;font-size:11px;letter-spacing:1px;text-transform:uppercase;border-bottom:1px solid #1A3550;background:#0D1B2A;font-family:monospace"
    th_left = th_style.replace("text-align:right", "text-align:left")
    td_style = "padding:9px 12px;border-bottom:1px solid #0F2234;font-size:13px;color:#E8F4FD;font-family:'DM Mono',monospace"

    table_html = f"""
    <div style="overflow-x:auto;border:1px solid #1A3550;border-radius:8px;margin-top:12px">
    <table style="width:100%;border-collapse:collapse;background:#0A0F1E">
    <thead><tr>
        <th style="{th_left}">Ticker</th>
        <th style="{th_left}">Empresa</th>
        <th style="{th_left}">Setor</th>
        <th style="{th_style}">Qtd</th>
        <th style="{th_style}">Preço Médio</th>
        <th style="{th_style}">Total Inv.</th>
        <th style="{th_style}">Preço Atual</th>
        <th style="{th_style}">Valor Atual</th>
        <th style="{th_style}">Result. R$</th>
        <th style="{th_style}">Result. %</th>
        <th style="{th_style}">DY% 12m</th>
        <th style="{th_style}">% Cart.</th>
    </tr></thead>
    <tbody>{html_rows}</tbody>
    </table></div>
    <div style="color:#4A6B85;font-size:10px;margin-top:6px;font-family:monospace">* Preço desatualizado — fonte indisponível</div>
    """

    st.markdown(table_html, unsafe_allow_html=True)

    # Totalizador
    st.markdown(f"""
    <div style="display:flex;gap:24px;margin-top:16px;padding:14px 20px;background:#0D1B2A;border:1px solid #1A3550;border-radius:8px">
        <div><span style="color:#7A9BB5;font-size:10px;font-family:monospace">TOTAL INVESTIDO</span><br>
             <span style="color:#E8F4FD;font-size:16px;font-family:monospace">{"R$ {:,.2f}".format(df_vis["Total Investido"].sum()).replace(",","X").replace(".",",").replace("X",".")}</span></div>
        <div><span style="color:#7A9BB5;font-size:10px;font-family:monospace">VALOR ATUAL</span><br>
             <span style="color:#00D4FF;font-size:16px;font-family:monospace">{"R$ {:,.2f}".format(df_vis["Valor Atual"].sum()).replace(",","X").replace(".",",").replace("X",".")}</span></div>
    </div>
    """, unsafe_allow_html=True)
