from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from data_loader import (
    EXPECTED_COLUMNS,
    SHEET_NAMES,
    get_value_column,
    load_dashboard_data,
    month_label,
    validate_loaded_data,
)


st.set_page_config(
    page_title="Dashboard Financeiro Pessoal",
    page_icon="💰",
    layout="wide",
)

COLOR_SEQUENCE = ["#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed", "#0891b2", "#4b5563"]


def format_brl(value: float | int | None) -> str:
    if pd.isna(value) or value is None:
        value = 0
    return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_eur(value: float | int | None) -> str:
    if pd.isna(value) or value is None:
        value = 0
    return f"€ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def make_empty_chart(title: str):
    fig = px.line(pd.DataFrame({"x": [], "y": []}), x="x", y="y", title=title)
    fig.update_layout(height=320)
    return fig


def available_months(df: pd.DataFrame) -> list[str]:
    if df.empty or "mes_periodo" not in df.columns:
        return []
    return sorted([month for month in df["mes_periodo"].dropna().unique().tolist() if month])


def filter_by_month(df: pd.DataFrame, selected_months: list[str]) -> pd.DataFrame:
    if df.empty or not selected_months or "mes_periodo" not in df.columns:
        return df.copy()
    return df[df["mes_periodo"].isin(selected_months)].copy()


def filter_options(df: pd.DataFrame, column: str) -> list[str]:
    if df.empty or column not in df.columns:
        return []
    values = df[column].dropna().astype(str)
    return sorted([value for value in values.unique().tolist() if value])


def apply_global_filters(df: pd.DataFrame, months: list[str], origins: list[str], categories: list[str]) -> pd.DataFrame:
    filtered = filter_by_month(df, months)
    if origins and "origem" in filtered.columns:
        filtered = filtered[filtered["origem"].astype(str).isin(origins)]
    if categories and "categoria_dashboard" in filtered.columns:
        filtered = filtered[filtered["categoria_dashboard"].astype(str).isin(categories)]
    return filtered


def metric_card(label: str, value: str, delta: str | None = None):
    st.metric(label=label, value=value, delta=delta)


def personal_costs(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "custo_pessoal_valido" not in df.columns:
        return pd.DataFrame()
    return df[df["custo_pessoal_valido"]].copy()


def monthly_sum(df: pd.DataFrame, value_col: str = "valor_real_dashboard") -> pd.DataFrame:
    if df.empty or value_col not in df.columns or "mes_periodo" not in df.columns:
        return pd.DataFrame(columns=["mes_periodo", "mes_label", "valor"])
    result = (
        df.dropna(subset=["mes_periodo"])
        .groupby("mes_periodo", as_index=False)[value_col]
        .sum()
        .rename(columns={value_col: "valor"})
        .sort_values("mes_periodo")
    )
    result["mes_label"] = result["mes_periodo"].apply(month_label)
    return result


def get_salary_for_month(dim_meses: pd.DataFrame, month: str | None) -> float:
    if dim_meses.empty or not month or "mes_periodo" not in dim_meses.columns:
        return 0.0
    month_row = dim_meses[dim_meses["mes_periodo"] == month]
    if month_row.empty:
        return 0.0
    salary_cols = [col for col in month_row.columns if "salario" in col or "receita" in col]
    if not salary_cols:
        return 0.0
    return float(month_row[salary_cols[0]].fillna(0).sum())


def page_visao_geral(data: dict[str, pd.DataFrame], filtered_transactions: pd.DataFrame, selected_months: list[str]):
    st.title("Visão Geral")
    personal = personal_costs(filtered_transactions)
    month_focus = selected_months[-1] if selected_months else (available_months(personal)[-1] if available_months(personal) else None)
    month_personal = personal[personal["mes_periodo"] == month_focus] if month_focus and "mes_periodo" in personal.columns else personal

    monthly = monthly_sum(personal)
    current_total = float(month_personal.get("valor_real_dashboard", pd.Series(dtype=float)).sum()) if not month_personal.empty else 0.0
    year_total = float(personal.get("valor_real_dashboard", pd.Series(dtype=float)).sum()) if not personal.empty else 0.0
    salary = get_salary_for_month(data.get("dim_meses", pd.DataFrame()), month_focus)
    balance = salary - current_total

    previous_delta = None
    if month_focus and not monthly.empty:
        months = monthly["mes_periodo"].tolist()
        if month_focus in months:
            idx = months.index(month_focus)
            if idx > 0:
                previous = float(monthly.iloc[idx - 1]["valor"])
                previous_delta = format_brl(current_total - previous)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card(f"Gastos pessoais do mês ({month_label(month_focus)})", format_brl(current_total), previous_delta)
    with c2:
        metric_card("Gastos pessoais no ano", format_brl(year_total))
    with c3:
        metric_card("Receita/salário do mês", format_brl(salary))
    with c4:
        metric_card("Saldo estimado do mês", format_brl(balance))

    left, right = st.columns([1.35, 1])
    with left:
        if monthly.empty:
            st.info("Ainda não há dados de custo pessoal para montar a evolução mensal.")
            st.plotly_chart(make_empty_chart("Evolução mensal dos gastos pessoais"), use_container_width=True)
        else:
            fig = px.line(
                monthly,
                x="mes_label",
                y="valor",
                markers=True,
                title="Evolução mensal dos gastos pessoais",
                labels={"mes_label": "Mês", "valor": "Valor em R$"},
                color_discrete_sequence=COLOR_SEQUENCE,
            )
            st.plotly_chart(fig, use_container_width=True)
    with right:
        if personal.empty or "categoria_dashboard" not in personal.columns:
            st.info("Ainda não há categorias disponíveis para o gráfico.")
        else:
            category = (
                personal.groupby("categoria_dashboard", as_index=False)["valor_real_dashboard"]
                .sum()
                .sort_values("valor_real_dashboard", ascending=False)
                .head(12)
            )
            fig = px.bar(
                category,
                x="valor_real_dashboard",
                y="categoria_dashboard",
                orientation="h",
                title="Gastos por categoria",
                labels={"valor_real_dashboard": "Valor em R$", "categoria_dashboard": "Categoria"},
                color_discrete_sequence=COLOR_SEQUENCE,
            )
            fig.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, use_container_width=True)


def page_transacoes(filtered_transactions: pd.DataFrame):
    st.title("Transações")
    df = filtered_transactions.copy()

    search = st.text_input("Pesquisar na descrição", "")
    if search and "descricao_norm" in df.columns:
        df = df[df["descricao_norm"].str.contains(search.lower(), na=False)]

    include_non_personal = st.toggle("Mostrar também linhas fora do custo pessoal", value=True)
    if not include_non_personal:
        df = personal_costs(df)

    preferred_cols = [
        "mes_label",
        "data",
        "descricao",
        "origem",
        "categoria_dashboard",
        "categoria_original_excel",
        "valor_real_dashboard",
        "valor_euro_dashboard",
        "entra_custo_pessoal",
        "parcela_compra",
        "linha_total_manual",
        "is_pagamento_fatura",
    ]
    visible_cols = [col for col in preferred_cols if col in df.columns]
    st.dataframe(df[visible_cols] if visible_cols else df, width="stretch", hide_index=True)


def page_categorias(filtered_transactions: pd.DataFrame):
    st.title("Categorias")
    personal = personal_costs(filtered_transactions)
    if personal.empty or "categoria_dashboard" not in personal.columns:
        st.info("Ainda não há gastos pessoais categorizados para analisar.")
        return

    left, right = st.columns([1, 1])
    with left:
        ranking = (
            personal.groupby("categoria_dashboard", as_index=False)["valor_real_dashboard"]
            .sum()
            .sort_values("valor_real_dashboard", ascending=False)
        )
        fig = px.bar(
            ranking.head(15),
            x="valor_real_dashboard",
            y="categoria_dashboard",
            orientation="h",
            title="Ranking de categorias",
            labels={"valor_real_dashboard": "Valor em R$", "categoria_dashboard": "Categoria"},
            color_discrete_sequence=COLOR_SEQUENCE,
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)
    with right:
        category_options = ranking["categoria_dashboard"].head(8).tolist()
        selected = st.multiselect("Comparar categorias", ranking["categoria_dashboard"].tolist(), default=category_options)
        evolution = (
            personal[personal["categoria_dashboard"].isin(selected)]
            .groupby(["mes_periodo", "categoria_dashboard"], as_index=False)["valor_real_dashboard"]
            .sum()
            .sort_values("mes_periodo")
        )
        evolution["mes_label"] = evolution["mes_periodo"].apply(month_label)
        fig = px.line(
            evolution,
            x="mes_label",
            y="valor_real_dashboard",
            color="categoria_dashboard",
            markers=True,
            title="Evolução mensal por categoria",
            labels={"valor_real_dashboard": "Valor em R$", "mes_label": "Mês", "categoria_dashboard": "Categoria"},
            color_discrete_sequence=COLOR_SEQUENCE,
        )
        st.plotly_chart(fig, use_container_width=True)


def page_origem(filtered_transactions: pd.DataFrame):
    st.title("Origem dos gastos")
    personal = personal_costs(filtered_transactions)
    if personal.empty or "origem" not in personal.columns:
        st.info("Ainda não há origem de gastos suficiente para análise.")
        return

    origin = (
        personal.groupby("origem", as_index=False)["valor_real_dashboard"]
        .sum()
        .sort_values("valor_real_dashboard", ascending=False)
    )
    fig = px.bar(
        origin,
        x="origem",
        y="valor_real_dashboard",
        title="Volume por origem",
        labels={"origem": "Origem", "valor_real_dashboard": "Valor em R$"},
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    st.plotly_chart(fig, use_container_width=True)

    invoice_count = int(filtered_transactions.get("is_pagamento_fatura", pd.Series(dtype=bool)).sum())
    if invoice_count:
        st.info(f"{invoice_count} linha(s) de pagamento de fatura/cartão foram identificadas e ficam fora dos custos pessoais.")


def generic_fact_page(title: str, df: pd.DataFrame, item_fallback: str = "item"):
    st.title(title)
    if df.empty:
        st.info(f"A aba de {title.lower()} está vazia ou não foi carregada.")
        return

    value_col = get_value_column(df)
    if not value_col:
        st.warning("Não encontrei uma coluna de valor para calcular os totais.")
        st.dataframe(df, width="stretch", hide_index=True)
        return

    clean = df[~df.get("linha_total_manual", pd.Series(False, index=df.index))].copy()
    total = float(clean[value_col].fillna(0).sum())
    monthly = monthly_sum(clean, value_col)

    c1, c2 = st.columns(2)
    with c1:
        metric_card("Total acumulado no ano", format_brl(total))
    with c2:
        last_month = monthly.iloc[-1] if not monthly.empty else None
        metric_card("Último mês disponível", format_brl(last_month["valor"] if last_month is not None else 0))

    if not monthly.empty:
        fig = px.line(
            monthly,
            x="mes_label",
            y="valor",
            markers=True,
            title="Evolução mensal",
            labels={"mes_label": "Mês", "valor": "Valor em R$"},
            color_discrete_sequence=COLOR_SEQUENCE,
        )
        st.plotly_chart(fig, use_container_width=True)

    item_col = item_fallback if item_fallback in clean.columns else ("descricao" if "descricao" in clean.columns else None)
    if item_col:
        detail = (
            clean.groupby(["mes_label", item_col], as_index=False)[value_col]
            .sum()
            .sort_values(["mes_label", value_col], ascending=[True, False])
        )
        st.subheader("Detalhe por item")
        st.dataframe(detail, width="stretch", hide_index=True)
    else:
        st.dataframe(clean, width="stretch", hide_index=True)


def page_apostas(data: dict[str, pd.DataFrame], filtered_transactions: pd.DataFrame):
    st.title("Apostas KTO")
    tx = filtered_transactions.copy()
    from_transactions = pd.DataFrame()
    if not tx.empty and {"is_bet_investimento", "is_bet_retorno", "valor_real_dashboard", "mes_periodo"}.issubset(tx.columns):
        bet_rows = tx[(tx["is_bet_investimento"] | tx["is_bet_retorno"]) & ~tx["linha_total_manual"]].copy()
        if not bet_rows.empty:
            invest = (
                bet_rows[bet_rows["is_bet_investimento"]]
                .groupby("mes_periodo", as_index=False)["valor_real_dashboard"]
                .sum()
                .rename(columns={"valor_real_dashboard": "valor_investido"})
            )
            returned = (
                bet_rows[bet_rows["is_bet_retorno"]]
                .groupby("mes_periodo", as_index=False)["valor_real_dashboard"]
                .sum()
                .rename(columns={"valor_real_dashboard": "valor_levantado"})
            )
            from_transactions = pd.merge(invest, returned, on="mes_periodo", how="outer").fillna(0)

    if from_transactions.empty:
        fallback = data.get("fact_apostas_kto", pd.DataFrame())
        value_col = get_value_column(fallback)
        if fallback.empty or not value_col:
            st.info("Ainda não encontrei transações classificadas como bet/bet retorno nem dados úteis na aba fact_apostas_kto.")
            return
        clean = fallback[~fallback.get("linha_total_manual", pd.Series(False, index=fallback.index))].copy()
        type_text = clean.get("tipo_norm", clean.get("descricao_norm", pd.Series("", index=clean.index)))
        clean["valor_investido"] = clean[value_col].where(type_text.str.contains("bet|aposta|invest", na=False), 0)
        clean["valor_levantado"] = clean[value_col].where(type_text.str.contains("retorno|levant|saque", na=False), 0)
        from_transactions = clean.groupby("mes_periodo", as_index=False)[["valor_investido", "valor_levantado"]].sum()

    bets = from_transactions.sort_values("mes_periodo")
    bets["saldo"] = bets["valor_levantado"] - bets["valor_investido"]
    bets["saldo_acumulado"] = bets["saldo"].cumsum()
    bets["mes_label"] = bets["mes_periodo"].apply(month_label)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Investido no ano", format_brl(bets["valor_investido"].sum()))
    with c2:
        metric_card("Levantado no ano", format_brl(bets["valor_levantado"].sum()))
    with c3:
        metric_card("Saldo no ano", format_brl(bets["saldo"].sum()))
    with c4:
        metric_card("Saldo acumulado", format_brl(bets["saldo_acumulado"].iloc[-1] if not bets.empty else 0))

    fig = px.bar(
        bets,
        x="mes_label",
        y=["valor_investido", "valor_levantado"],
        barmode="group",
        title="Investido vs levantado por mês",
        labels={"mes_label": "Mês", "value": "Valor em R$", "variable": "Tipo"},
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Resumo mensal")
    st.dataframe(bets, width="stretch", hide_index=True)


def page_diagnostico(data: dict[str, pd.DataFrame]):
    st.title("Diagnóstico da Base")
    summary = []
    for sheet in SHEET_NAMES:
        df = data.get(sheet, pd.DataFrame())
        summary.append(
            {
                "aba": sheet,
                "linhas": len(df),
                "colunas": ", ".join(df.columns.tolist()) if not df.empty else "",
            }
        )
    st.subheader("Abas carregadas")
    st.dataframe(pd.DataFrame(summary), width="stretch", hide_index=True)

    issues = validate_loaded_data(data)
    st.subheader("Alertas")
    if not issues:
        st.success("Nenhum problema estrutural encontrado nas validações básicas.")
    else:
        for issue in issues:
            if issue.level == "erro":
                st.error(f"{issue.sheet}: {issue.message}")
            else:
                st.warning(f"{issue.sheet}: {issue.message}")

    st.subheader("Colunas esperadas")
    expected = [{"aba": sheet, "colunas_esperadas": ", ".join(cols)} for sheet, cols in EXPECTED_COLUMNS.items()]
    st.dataframe(pd.DataFrame(expected), width="stretch", hide_index=True)


def render_app():
    st.sidebar.title("Filtros")
    result = load_dashboard_data()
    data = result.data

    if result.demo_mode:
        st.warning(
            "Modo demo activo: os dados abaixo são simulados. Configure os secrets para ligar ao Google Sheets real."
        )
        if result.message:
            with st.expander("Detalhe da ligação ao Google Sheets"):
                st.info(result.message)

    transactions = data.get("fact_transacoes", pd.DataFrame())
    if transactions.empty:
        st.warning("A aba fact_transacoes está vazia ou não retornou linhas. As páginas serão exibidas com estados vazios.")

    months = available_months(transactions)
    default_months = months[-1:] if months else []
    selected_months = st.sidebar.multiselect(
        "Mês",
        options=months,
        default=default_months,
        format_func=month_label,
    )

    selected_origins = st.sidebar.multiselect("Origem", options=filter_options(transactions, "origem"))
    selected_categories = st.sidebar.multiselect("Categoria", options=filter_options(transactions, "categoria_dashboard"))

    filtered_transactions = apply_global_filters(transactions, selected_months, selected_origins, selected_categories)

    page = st.sidebar.radio(
        "Página",
        [
            "Visão Geral",
            "Transações",
            "Categorias",
            "Origem dos gastos",
            "Marta",
            "Aluguel/Casa",
            "Apostas KTO",
            "Diagnóstico da Base",
        ],
    )

    if page == "Visão Geral":
        page_visao_geral(data, filtered_transactions, selected_months)
    elif page == "Transações":
        page_transacoes(filtered_transactions)
    elif page == "Categorias":
        page_categorias(filtered_transactions)
    elif page == "Origem dos gastos":
        page_origem(filtered_transactions)
    elif page == "Marta":
        generic_fact_page("Marta", filter_by_month(data.get("fact_marta", pd.DataFrame()), selected_months))
    elif page == "Aluguel/Casa":
        generic_fact_page("Aluguel/Casa", filter_by_month(data.get("fact_aluguel", pd.DataFrame()), selected_months))
    elif page == "Apostas KTO":
        page_apostas(data, filtered_transactions)
    elif page == "Diagnóstico da Base":
        page_diagnostico(data)


if __name__ == "__main__":
    render_app()
