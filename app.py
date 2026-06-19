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
    normalize_text,
    validate_loaded_data,
)


st.set_page_config(
    page_title="Dashboard Financeiro Pessoal",
    page_icon="💰",
    layout="wide",
)

COLOR_SEQUENCE = ["#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed", "#0891b2", "#4b5563"]

SHARED_HOME_COST_NAMES = {
    "aluguel",
    "condominio",
    "condomínio",
    "cota extra canalizacao ac",
    "cota extra canalização ac",
    "cota extra canalizacao ac 9 de 10",
    "cota extra canalização ac 9 de 10",
    "fundo de reserva",
    "funesbom",
    "iptu",
    "iptu 1 de 10",
    "iptu 10 de 10",
    "seguro incendio",
    "seguro incêndio",
    "seguro de incendio",
    "seguro de incêndio",
    "taxa bancaria",
    "taxa bancária",
    "luz",
    "gas",
    "gás",
    "celular",
    "internet + tv",
}


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


def add_average_line(fig, df: pd.DataFrame, value_col: str, label: str = "Média do período", color: str = "#64748b"):
    if df.empty or value_col not in df.columns:
        return
    average = df[value_col].dropna().mean()
    if pd.isna(average):
        return
    fig.add_hline(
        y=float(average),
        line_dash="dot",
        line_color=color,
        annotation_text=f"{label}: {format_brl(average)}",
        annotation_position="top left",
    )


def add_group_average_lines(fig, df: pd.DataFrame, group_col: str, value_col: str):
    if df.empty or group_col not in df.columns or value_col not in df.columns:
        return
    for idx, (group, group_df) in enumerate(df.groupby(group_col)):
        average = group_df[value_col].dropna().mean()
        if pd.isna(average):
            continue
        color = COLOR_SEQUENCE[idx % len(COLOR_SEQUENCE)]
        fig.add_hline(
            y=float(average),
            line_dash="dot",
            line_color=color,
            opacity=0.6,
            annotation_text=f"Média {group}: {format_brl(average)}",
            annotation_position="top left",
        )


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


def _category_norm(df: pd.DataFrame) -> pd.Series:
    return df.get("categoria_dashboard_norm", pd.Series("", index=df.index)).fillna("")


def _origin_norm(df: pd.DataFrame) -> pd.Series:
    return df.get("origem_norm", pd.Series("", index=df.index)).fillna("")


def _original_category_norm(df: pd.DataFrame) -> pd.Series:
    return df.get("categoria_original_excel_norm", pd.Series("", index=df.index)).fillna("")


def _valid_transaction_base(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=bool)
    value_valid = df.get("valor_real_dashboard", pd.Series(None, index=df.index)).notna()
    return (
        value_valid
        & ~df.get("linha_total_manual", pd.Series(False, index=df.index))
        & ~df.get("is_bet_investimento", pd.Series(False, index=df.index))
        & ~df.get("is_bet_retorno", pd.Series(False, index=df.index))
    )


def _is_credit_card_source(df: pd.DataFrame) -> pd.Series:
    origin = _origin_norm(df)
    return origin.str.contains(r"cartao de credito|cartão de crédito", na=False)


def _is_adjustment_category(df: pd.DataFrame) -> pd.Series:
    category = _category_norm(df)
    return category.str.contains(r"ajuste|abatimento", na=False)


def _is_shared_home_cost(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=bool)
    category = _category_norm(df)
    item_parts = []
    for column in ["nome_custo_norm", "descricao_norm"]:
        if column in df.columns:
            item_parts.append(df[column].fillna(""))
    if "nome_custo" in df.columns:
        item_parts.append(df["nome_custo"].apply(normalize_text))
    if "descricao" in df.columns:
        item_parts.append(df["descricao"].apply(normalize_text))
    item_match = pd.Series(False, index=df.index)
    for item in item_parts:
        item_match = item_match | item.isin(SHARED_HOME_COST_NAMES)
    return category.eq("custo de casa") & item_match


def _apply_personal_share_rules(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    adjusted = df.copy()
    shared_home_mask = _is_shared_home_cost(adjusted)
    value_columns = [
        "valor_real",
        "valor_euro",
        "valor_real_dashboard",
        "valor_euro_dashboard",
    ]
    for column in value_columns:
        if column in adjusted.columns:
            adjusted.loc[shared_home_mask, column] = adjusted.loc[shared_home_mask, column] * 0.5
    return adjusted


def accounting_costs(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    mask = (
        _valid_transaction_base(df)
        & df.get("entra_custo_pessoal_bool", pd.Series(False, index=df.index))
        & ~df.get("is_pagamento_fatura", pd.Series(False, index=df.index))
    )
    return _apply_personal_share_rules(df[mask])


def financial_costs(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    mask = (
        _valid_transaction_base(df)
        & ~_is_credit_card_source(df)
        & ~_is_adjustment_category(df)
        & (
            df.get("entra_custo_pessoal_bool", pd.Series(False, index=df.index))
            | df.get("is_pagamento_fatura", pd.Series(False, index=df.index))
        )
    )
    return _apply_personal_share_rules(df[mask])


def credit_card_statement_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "valor_real_dashboard" not in df.columns or "mes_periodo" not in df.columns:
        return pd.DataFrame(columns=["mes_periodo", "mes_label", "categoria_dashboard", "valor_real_dashboard"])
    mask = _valid_transaction_base(df) & _is_credit_card_source(df)
    card = df[mask].copy()
    if card.empty:
        return pd.DataFrame(columns=["mes_periodo", "mes_label", "categoria_dashboard", "valor_real_dashboard"])
    result = (
        card.dropna(subset=["mes_periodo"])
        .groupby("mes_periodo", as_index=False)["valor_real_dashboard"]
        .sum()
        .rename(columns={"valor_real_dashboard": "valor_real_dashboard"})
    )
    result = result[result["valor_real_dashboard"] != 0].copy()
    result["mes_label"] = result["mes_periodo"].apply(month_label)
    result["categoria_dashboard"] = "Cartão de Crédito"
    return result[["mes_periodo", "mes_label", "categoria_dashboard", "valor_real_dashboard"]]


def accounting_costs_with_card_total(df: pd.DataFrame) -> pd.DataFrame:
    accounting = accounting_costs(df)
    card_total = credit_card_statement_rows(df)
    if card_total.empty:
        return accounting
    return pd.concat([accounting, card_total], ignore_index=True, sort=False)


def financial_category_info(category: str) -> str:
    if category == "Cartão de Crédito":
        return "Valor pago referente à fatura do cartão de crédito do mês anterior, que saiu da conta corrente."
    if category == "Custo de casa":
        return "Custo de casa (aluguel + contas / 2) + outros custos de casa que saíram da conta corrente."
    return "Gasto que saiu da conta corrente."


def accounting_category_info(category: str) -> str:
    if category == "Cartão de Crédito":
        return "Valor total do cartão de crédito do mês corrente."
    if category == "Ajuste/abatimento":
        return "Abatimentos, estornos ou ajustes que reduzem ou corrigem o total do mês."
    if category == "Custo de casa":
        return "Custo total de casa saído da conta corrente + gasto de casa no cartão de crédito desse mês."
    return f"Custo total de {category.lower()} saído da conta corrente + gasto no cartão de crédito desse mês."


def add_category_hover_columns(df: pd.DataFrame, context: str) -> pd.DataFrame:
    if df.empty or "categoria_dashboard" not in df.columns:
        return df.copy()
    result = df.copy()
    info_fn = financial_category_info if context == "financial" else accounting_category_info
    result["categoria_info"] = result["categoria_dashboard"].apply(info_fn)
    result["categoria_display"] = result["categoria_dashboard"].astype(str) + " ⓘ"
    return result


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


def sum_value(df: pd.DataFrame, value_col: str = "valor_real_dashboard") -> float:
    if df.empty or value_col not in df.columns:
        return 0.0
    return float(df[value_col].fillna(0).sum())


def diagnostic_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=columns)
    view = df.copy()
    if "mes_nome" not in view.columns and "mes_label" in view.columns:
        view["mes_nome"] = view["mes_label"]
    available = [column for column in columns if column in view.columns]
    return view[available].head(100)


def build_transaction_diagnostics(transactions: pd.DataFrame) -> dict[str, pd.DataFrame]:
    if transactions.empty:
        empty = pd.DataFrame()
        return {
            "resumo": empty,
            "exclusoes": empty,
            "meses": empty,
            "categorias": empty,
            "origens": empty,
            "incluidas": empty,
            "excluidas": empty,
        }

    tx = transactions.copy()
    value_col = "valor_real_dashboard"
    personal = personal_costs(tx)
    excluded = tx[~tx.get("custo_pessoal_valido", pd.Series(False, index=tx.index))].copy()

    entra = tx.get("entra_custo_pessoal_norm", pd.Series("", index=tx.index)).fillna("")
    is_sim = entra.isin(["sim", "s", "yes", "true", "1"])
    is_nao = entra.isin(["nao", "n", "no", "false", "0"])

    resumo = pd.DataFrame(
        [
            {"métrica": "Linhas carregadas em fact_transacoes", "valor": len(tx)},
            {"métrica": "Linhas com entra_custo_pessoal = Sim", "valor": int(is_sim.sum())},
            {"métrica": "Linhas com entra_custo_pessoal = Não", "valor": int(is_nao.sum())},
            {"métrica": "Soma de valor_real_dashboard antes dos filtros", "valor": sum_value(tx, value_col)},
            {"métrica": "Soma de valor_real_dashboard depois dos filtros de gasto pessoal", "valor": sum_value(personal, value_col)},
        ]
    )

    if excluded.empty:
        exclusoes = pd.DataFrame(columns=["motivo_exclusao", "quantidade_linhas", "soma_valor_real_dashboard"])
    else:
        excluded["motivo_exclusao"] = excluded.get("motivo_exclusao", "").replace("", "outros").fillna("outros")
        exclusoes = (
            excluded.groupby("motivo_exclusao", as_index=False)
            .agg(quantidade_linhas=(value_col, "size"), soma_valor_real_dashboard=(value_col, "sum"))
            .sort_values("soma_valor_real_dashboard", ascending=False)
        )

    bruto_mes = monthly_sum(tx, value_col).rename(columns={"valor": "total_bruto_antes_dos_filtros"})
    pessoal_mes = monthly_sum(personal, value_col).rename(columns={"valor": "total_gasto_pessoal"})
    excluido_mes = monthly_sum(excluded, value_col).rename(columns={"valor": "total_excluido"})
    non_total = ~tx.get("linha_total_manual", pd.Series(False, index=tx.index))
    bet_mes = monthly_sum(
        tx[tx.get("is_bet_investimento", pd.Series(False, index=tx.index)) & non_total],
        value_col,
    ).rename(columns={"valor": "total_bet"})
    bet_retorno_mes = monthly_sum(
        tx[tx.get("is_bet_retorno", pd.Series(False, index=tx.index)) & non_total],
        value_col,
    ).rename(columns={"valor": "total_bet_retorno"})
    meses = bruto_mes[["mes_periodo", "mes_label", "total_bruto_antes_dos_filtros"]]
    for frame, column in [
        (pessoal_mes, "total_gasto_pessoal"),
        (excluido_mes, "total_excluido"),
        (bet_mes, "total_bet"),
        (bet_retorno_mes, "total_bet_retorno"),
    ]:
        meses = meses.merge(frame[["mes_periodo", column]], on="mes_periodo", how="outer")
    meses["mes_label"] = meses["mes_label"].fillna(meses["mes_periodo"].apply(month_label))
    numeric_month_columns = [
        "total_bruto_antes_dos_filtros",
        "total_gasto_pessoal",
        "total_excluido",
        "total_bet",
        "total_bet_retorno",
    ]
    meses[numeric_month_columns] = meses[numeric_month_columns].fillna(0)
    meses = meses.sort_values("mes_periodo")

    if personal.empty or "categoria_dashboard" not in personal.columns:
        categorias = pd.DataFrame(
            columns=["categoria_dashboard", "quantidade_linhas", "soma_valor_real_dashboard", "percentual_gasto_pessoal"]
        )
    else:
        total_personal = sum_value(personal, value_col)
        categorias = (
            personal.groupby("categoria_dashboard", as_index=False)
            .agg(quantidade_linhas=(value_col, "size"), soma_valor_real_dashboard=(value_col, "sum"))
            .sort_values("soma_valor_real_dashboard", ascending=False)
        )
        categorias["percentual_gasto_pessoal"] = (
            categorias["soma_valor_real_dashboard"] / total_personal * 100 if total_personal else 0
        )

    if personal.empty or "origem" not in personal.columns:
        origens = pd.DataFrame(columns=["origem", "quantidade_linhas", "soma_valor_real_dashboard"])
    else:
        origens = (
            personal.groupby("origem", as_index=False)
            .agg(quantidade_linhas=(value_col, "size"), soma_valor_real_dashboard=(value_col, "sum"))
            .sort_values("soma_valor_real_dashboard", ascending=False)
        )

    included_cols = [
        "data",
        "mes_nome",
        "origem",
        "categoria_dashboard",
        "categoria_original_excel",
        "descricao",
        "valor_real_dashboard",
        "entra_custo_pessoal",
        "parcela_compra",
    ]
    excluded_cols = [
        "data",
        "mes_nome",
        "origem",
        "categoria_dashboard",
        "categoria_original_excel",
        "descricao",
        "valor_real_dashboard",
        "entra_custo_pessoal",
        "motivo_exclusao",
    ]

    return {
        "resumo": resumo,
        "exclusoes": exclusoes,
        "meses": meses,
        "categorias": categorias,
        "origens": origens,
        "incluidas": diagnostic_columns(personal, included_cols),
        "excluidas": diagnostic_columns(excluded, excluded_cols),
    }


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


def get_salary_for_months(dim_meses: pd.DataFrame, months: list[str]) -> float:
    if dim_meses.empty or not months or "mes_periodo" not in dim_meses.columns:
        return 0.0
    salary_cols = [col for col in dim_meses.columns if "salario" in col or "receita" in col]
    if not salary_cols:
        return 0.0
    rows = dim_meses[dim_meses["mes_periodo"].isin(months)]
    return float(rows[salary_cols[0]].fillna(0).sum())


def build_monthly_revenue_series(dim_meses: pd.DataFrame, months: list[str]) -> pd.DataFrame:
    columns = ["mes_periodo", "categoria_dashboard", "valor_real_dashboard"]
    if dim_meses.empty or "mes_periodo" not in dim_meses.columns:
        return pd.DataFrame(columns=columns)
    salary_cols = [col for col in dim_meses.columns if "salario" in col or "receita" in col]
    if not salary_cols:
        return pd.DataFrame(columns=columns)
    revenue = dim_meses.copy()
    if months:
        revenue = revenue[revenue["mes_periodo"].isin(months)]
    revenue = revenue.dropna(subset=["mes_periodo"]).copy()
    revenue["categoria_dashboard"] = "Receita mensal"
    revenue["valor_real_dashboard"] = revenue[salary_cols[0]].fillna(0)
    return revenue[columns]


def build_category_revenue_table(personal: pd.DataFrame, dim_meses: pd.DataFrame) -> pd.DataFrame:
    columns = ["Mês", "Categoria", "Valor", "% da receita"]
    if personal.empty or "categoria_dashboard" not in personal.columns:
        return pd.DataFrame(columns=columns)

    months = available_months(personal)
    revenue = build_monthly_revenue_series(dim_meses, months)
    if revenue.empty:
        revenue_by_month = pd.DataFrame(columns=["mes_periodo", "receita_mensal"])
    else:
        revenue_by_month = revenue.rename(columns={"valor_real_dashboard": "receita_mensal"})[
            ["mes_periodo", "receita_mensal"]
        ]

    costs = (
        personal.groupby(["mes_periodo", "categoria_dashboard"], as_index=False)["valor_real_dashboard"]
        .sum()
        .rename(columns={"categoria_dashboard": "Categoria", "valor_real_dashboard": "valor"})
    )
    costs = costs.merge(revenue_by_month, on="mes_periodo", how="left")
    costs["peso_receita"] = costs.apply(
        lambda row: (row["valor"] / row["receita_mensal"] * 100)
        if pd.notna(row.get("receita_mensal")) and row.get("receita_mensal") != 0
        else 0,
        axis=1,
    )
    costs["ordem"] = 1

    revenue_rows = revenue.rename(columns={"valor_real_dashboard": "valor"}).copy()
    if revenue_rows.empty:
        revenue_rows = pd.DataFrame(columns=["mes_periodo", "Categoria", "valor", "peso_receita", "ordem"])
    else:
        revenue_rows["Categoria"] = "Receita mensal"
        revenue_rows["peso_receita"] = 100.0
        revenue_rows["ordem"] = 0

    table = pd.concat(
        [
            revenue_rows[["mes_periodo", "Categoria", "valor", "peso_receita", "ordem"]],
            costs[["mes_periodo", "Categoria", "valor", "peso_receita", "ordem"]],
        ],
        ignore_index=True,
    )
    table["mes_label"] = table["mes_periodo"].apply(month_label)
    table = table.sort_values(["mes_periodo", "ordem", "valor"], ascending=[True, True, False])
    table["Valor"] = table["valor"].apply(format_brl)
    table["% da receita"] = table["peso_receita"].apply(lambda value: f"{float(value):.1f}%".replace(".", ","))
    table["Mês"] = table["mes_label"]
    return table[columns].reset_index(drop=True)


def page_visao_geral(
    data: dict[str, pd.DataFrame],
    filtered_transactions: pd.DataFrame,
    selected_months: list[str],
    annual_transactions: pd.DataFrame | None = None,
):
    st.title("Visão Geral")
    personal = financial_costs(filtered_transactions)
    annual_personal = financial_costs(annual_transactions if annual_transactions is not None else filtered_transactions)
    month_focus = selected_months[-1] if selected_months else (available_months(personal)[-1] if available_months(personal) else None)
    month_personal = personal[personal["mes_periodo"] == month_focus] if month_focus and "mes_periodo" in personal.columns else personal
    multiple_months_selected = len(selected_months) > 1
    period_label = "período" if multiple_months_selected else "mês"

    monthly = monthly_sum(personal)
    if multiple_months_selected:
        current_total = sum_value(personal)
    else:
        current_total = (
            float(month_personal.get("valor_real_dashboard", pd.Series(dtype=float)).sum()) if not month_personal.empty else 0.0
        )
    year_total = float(annual_personal.get("valor_real_dashboard", pd.Series(dtype=float)).sum()) if not annual_personal.empty else 0.0
    salary = (
        get_salary_for_months(data.get("dim_meses", pd.DataFrame()), selected_months)
        if multiple_months_selected
        else get_salary_for_month(data.get("dim_meses", pd.DataFrame()), month_focus)
    )
    balance = salary - current_total

    previous_delta = None
    if not multiple_months_selected and month_focus and not monthly.empty:
        months = monthly["mes_periodo"].tolist()
        if month_focus in months:
            idx = months.index(month_focus)
            if idx > 0:
                previous = float(monthly.iloc[idx - 1]["valor"])
                previous_delta = format_brl(current_total - previous)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card(f"Receita/salário do {period_label}", format_brl(salary))
    with c2:
        if multiple_months_selected:
            metric_card("Gastos financeiros do período", format_brl(current_total))
        else:
            metric_card(f"Gastos financeiros do mês ({month_label(month_focus)})", format_brl(current_total), previous_delta)
    with c3:
        metric_card(f"Saldo estimado do {period_label}", format_brl(balance))
    with c4:
        metric_card("Gastos financeiros no ano", format_brl(year_total))

    left, right = st.columns([1.35, 1])
    with left:
        if monthly.empty:
            st.info("Ainda não há dados de fluxo financeiro para montar a evolução mensal.")
            st.plotly_chart(make_empty_chart("Evolução mensal dos gastos pessoais"), use_container_width=True)
        else:
            monthly["valor_label"] = monthly["valor"].apply(format_brl)
            fig = px.line(
                monthly,
                x="mes_label",
                y="valor",
                markers=True,
                title="Evolução mensal dos gastos financeiros",
                labels={"mes_label": "Mês", "valor": "Valor em R$"},
                text="valor_label",
                color_discrete_sequence=COLOR_SEQUENCE,
            )
            fig.update_traces(textposition="top center", textfont={"size": 12}, cliponaxis=False)
            add_average_line(fig, monthly, "valor")
            max_monthly_value = float(monthly["valor"].max()) if not monthly.empty else 0
            if max_monthly_value > 0:
                fig.update_yaxes(range=[0, max_monthly_value * 1.18])
            st.plotly_chart(fig, use_container_width=True)
    with right:
        if personal.empty or "categoria_dashboard" not in personal.columns:
            st.info("Ainda não há categorias financeiras disponíveis para o gráfico.")
        else:
            category_totals = (
                personal.groupby("categoria_dashboard", as_index=False)["valor_real_dashboard"]
                .sum()
                .sort_values("valor_real_dashboard", ascending=False)
                .head(12)
            )
            top_categories = category_totals["categoria_dashboard"].tolist()
            category_order = top_categories
            selected_category_rows = personal[personal["categoria_dashboard"].isin(top_categories)].copy()
            compare_months = selected_category_rows["mes_periodo"].dropna().nunique() > 1

            if compare_months and "mes_label" in selected_category_rows.columns:
                category = (
                    selected_category_rows.groupby(
                        ["categoria_dashboard", "mes_periodo", "mes_label"],
                        as_index=False,
                    )["valor_real_dashboard"]
                    .sum()
                    .sort_values(["mes_periodo", "valor_real_dashboard"], ascending=[True, False])
                )
                category["valor_label"] = category["valor_real_dashboard"].apply(format_brl)
                category = add_category_hover_columns(category, "financial")
                month_order = (
                    category[["mes_periodo", "mes_label"]]
                    .drop_duplicates()
                    .sort_values("mes_periodo")["mes_label"]
                    .tolist()
                )
                fig = px.bar(
                    category,
                    x="categoria_display",
                    y="valor_real_dashboard",
                    color="mes_label",
                    barmode="group",
                    title="Gastos financeiros por categoria",
                    labels={
                        "valor_real_dashboard": "Valor em R$",
                        "categoria_display": "Categoria",
                        "mes_label": "Mês",
                        "categoria_info": "Como ler",
                    },
                    text="valor_label",
                    hover_data={"categoria_info": True, "categoria_display": False},
                    category_orders={
                        "categoria_display": [f"{category} ⓘ" for category in category_order],
                        "mes_label": month_order,
                    },
                    color_discrete_sequence=COLOR_SEQUENCE,
                )
            else:
                category = category_totals.copy()
                category["valor_label"] = category["valor_real_dashboard"].apply(format_brl)
                category = add_category_hover_columns(category, "financial")
                fig = px.bar(
                    category,
                    x="categoria_display",
                    y="valor_real_dashboard",
                    title="Gastos financeiros por categoria",
                    labels={
                        "valor_real_dashboard": "Valor em R$",
                        "categoria_display": "Categoria",
                        "categoria_info": "Como ler",
                    },
                    text="valor_label",
                    hover_data={"categoria_info": True, "categoria_display": False},
                    category_orders={"categoria_display": [f"{category} ⓘ" for category in category_order]},
                    color_discrete_sequence=COLOR_SEQUENCE,
                )
            fig.update_traces(textposition="outside", cliponaxis=False)
            max_category_value = float(category["valor_real_dashboard"].max()) if not category.empty else 0
            fig.update_layout(margin={"t": 64})
            if max_category_value > 0:
                fig.update_yaxes(range=[0, max_category_value * 1.25])
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
        "parcela_compra",
    ]
    visible_cols = [col for col in preferred_cols if col in df.columns]
    st.dataframe(df[visible_cols] if visible_cols else df, width="stretch", hide_index=True)


def page_categorias(filtered_transactions: pd.DataFrame, dim_meses: pd.DataFrame):
    st.title("Categorias")
    personal = accounting_costs_with_card_total(filtered_transactions)
    if personal.empty or "categoria_dashboard" not in personal.columns:
        st.info("Ainda não há gastos pessoais categorizados para analisar.")
        return
    selected_periods = available_months(personal)
    revenue_series = build_monthly_revenue_series(dim_meses, selected_periods)

    left, right = st.columns([1, 1])
    with left:
        ranking = (
            personal.groupby("categoria_dashboard", as_index=False)["valor_real_dashboard"]
            .sum()
            .sort_values("valor_real_dashboard", ascending=False)
        )
        ranking["valor_label"] = ranking["valor_real_dashboard"].apply(format_brl)
        ranking = add_category_hover_columns(ranking, "accounting")
        fig = px.bar(
            ranking.head(15),
            x="valor_real_dashboard",
            y="categoria_display",
            orientation="h",
            title="Ranking de categorias",
            labels={
                "valor_real_dashboard": "Valor em R$",
                "categoria_display": "Categoria",
                "categoria_info": "Como ler",
            },
            text="valor_label",
            hover_data={"categoria_info": True, "categoria_display": False},
            color_discrete_sequence=COLOR_SEQUENCE,
        )
        max_ranking_value = float(ranking["valor_real_dashboard"].max()) if not ranking.empty else 0
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, margin={"r": 96})
        if max_ranking_value > 0:
            fig.update_xaxes(range=[0, max_ranking_value * 1.25])
        st.plotly_chart(fig, use_container_width=True)
    with right:
        category_options = ranking["categoria_dashboard"].head(8).tolist()
        comparison_options = ranking["categoria_dashboard"].tolist()
        if not revenue_series.empty:
            comparison_options = ["Receita mensal"] + comparison_options
            category_options = ["Receita mensal"] + category_options
        selected = st.multiselect("Comparar categorias", comparison_options, default=category_options)
        show_category_average = st.toggle("Mostrar média do período", value=False, key="show_category_average")
        evolution = (
            personal[personal["categoria_dashboard"].isin(selected)]
            .groupby(["mes_periodo", "categoria_dashboard"], as_index=False)["valor_real_dashboard"]
            .sum()
            .sort_values("mes_periodo")
        )
        if "Receita mensal" in selected and not revenue_series.empty:
            evolution = pd.concat([evolution, revenue_series], ignore_index=True)
            evolution = evolution.sort_values(["mes_periodo", "categoria_dashboard"])
        evolution["mes_label"] = evolution["mes_periodo"].apply(month_label)
        evolution["valor_label"] = evolution["valor_real_dashboard"].apply(format_brl)
        fig = px.line(
            evolution,
            x="mes_label",
            y="valor_real_dashboard",
            color="categoria_dashboard",
            markers=True,
            title="Evolução mensal por categoria",
            labels={"valor_real_dashboard": "Valor em R$", "mes_label": "Mês", "categoria_dashboard": "Categoria"},
            text="valor_label",
            color_discrete_sequence=COLOR_SEQUENCE,
        )
        fig.update_traces(textposition="top center", textfont={"size": 11}, cliponaxis=False)
        if show_category_average:
            add_group_average_lines(fig, evolution, "categoria_dashboard", "valor_real_dashboard")
        if not evolution.empty:
            max_evolution_value = float(evolution["valor_real_dashboard"].max())
            min_evolution_value = float(evolution["valor_real_dashboard"].min())
            upper_padding = abs(max_evolution_value) * 0.18 if max_evolution_value else 1
            lower_padding = abs(min_evolution_value) * 0.18 if min_evolution_value < 0 else 0
            fig.update_yaxes(range=[min(0, min_evolution_value - lower_padding), max_evolution_value + upper_padding])
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Resumo mensal por categoria")
    category_table = build_category_revenue_table(personal, dim_meses)
    if category_table.empty:
        st.info("Ainda não há receita mensal para calcular o peso das categorias.")
    else:
        st.dataframe(category_table, width="stretch", hide_index=True)


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


MARTA_HOUSE_TERMS = (
    "aluguel",
    "aluguer",
    "alugue",
    "condominio",
    "iptu",
    "internet",
    "tv",
    "seguro telemovel",
    "celular",
    "telefone",
    "telemovel",
    "movel",
    "wellhub",
    "gympass",
    "gym pass",
    "luz",
    "gas",
)


def build_marta_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Mês", "Item", "Tipo", "Valor"])

    value_col = get_value_column(df)
    if not value_col:
        return pd.DataFrame(columns=["Mês", "Item", "Tipo", "Valor"])

    clean = df[~df.get("linha_total_manual", pd.Series(False, index=df.index))].copy()
    item_col = get_item_column(clean)
    if not item_col:
        return pd.DataFrame(columns=["Mês", "Item", "Tipo", "Valor"])

    text = clean[item_col].apply(normalize_text)
    house_mask = text.apply(lambda item: any(term in item for term in MARTA_HOUSE_TERMS))
    abatimento_mask = text.str.contains(r"\b(?:wellhub|gym\s*pass|gympass|gypass)\b", na=False, regex=True)
    clean = clean[house_mask | abatimento_mask].copy()
    if clean.empty:
        return pd.DataFrame(columns=["Mês", "Item", "Tipo", "Valor"])

    clean["Tipo"] = "Custo de casa"
    clean.loc[abatimento_mask.loc[clean.index], "Tipo"] = "Abatimento Wellhub"
    clean["ordem"] = 0
    clean.loc[abatimento_mask.loc[clean.index], "ordem"] = 1
    clean["Valor"] = clean[value_col].fillna(0).abs()
    clean.loc[abatimento_mask.loc[clean.index], "Valor"] = -clean.loc[abatimento_mask.loc[clean.index], "Valor"]
    clean["Mês"] = clean.get("mes_label", pd.Series("Sem mês", index=clean.index))
    clean["Item"] = clean[item_col].fillna("").astype(str)

    detail = clean[["Mês", "Item", "Tipo", "Valor", "ordem"]].sort_values(["Mês", "ordem", "Item"])
    totals = (
        detail.groupby("Mês", as_index=False)["Valor"]
        .sum()
        .assign(Item="Total a receber da Marta", Tipo="Total", ordem=2)
    )
    table = pd.concat([detail, totals[["Mês", "Item", "Tipo", "Valor", "ordem"]]], ignore_index=True)
    return table.sort_values(["Mês", "ordem", "Item"]).drop(columns=["ordem"]).reset_index(drop=True)


def page_marta(df: pd.DataFrame):
    st.title("Marta")
    table = build_marta_table(df)
    if table.empty:
        st.info("Não encontrei itens de casa ou Gympass para calcular o valor da Marta neste período.")
        return

    display = table.copy()
    display["Valor"] = display["Valor"].apply(format_brl)
    st.dataframe(display, width="stretch", hide_index=True)


def get_item_column(df: pd.DataFrame, fallback: str = "item") -> str | None:
    for column in [fallback, "rubrica", "item", "descricao", "nome_custo"]:
        if column in df.columns:
            return column
    return None


def build_luz_gas_monthly(df: pd.DataFrame, value_col: str, item_col: str | None) -> pd.DataFrame:
    if df.empty or not item_col or value_col not in df.columns:
        return pd.DataFrame(columns=["mes_periodo", "mes_label", "conta", "valor"])

    utilities = df.copy()
    item_norm = utilities[item_col].apply(normalize_text)
    utilities["conta"] = ""
    utilities.loc[item_norm.str.contains(r"\bluz\b|energia|eletric", na=False), "conta"] = "Luz"
    utilities.loc[item_norm.str.contains(r"\bgas\b|\bgás\b", na=False), "conta"] = "Gás"
    utilities = utilities[utilities["conta"] != ""].copy()
    if utilities.empty:
        return pd.DataFrame(columns=["mes_periodo", "mes_label", "conta", "valor"])

    result = (
        utilities.groupby(["mes_periodo", "mes_label", "conta"], as_index=False)[value_col]
        .sum()
        .rename(columns={value_col: "valor"})
        .sort_values(["mes_periodo", "conta"])
    )
    result["valor"] = result["valor"] * 2
    return result


def build_aluguel_contas_dataset(fact_aluguel: pd.DataFrame, transactions: pd.DataFrame) -> pd.DataFrame:
    columns = ["mes_periodo", "mes_label", "rubrica", "valor_real_dashboard", "fonte_dado", "linha_total_manual"]
    parts: list[pd.DataFrame] = []

    if not fact_aluguel.empty:
        rent = fact_aluguel[~fact_aluguel.get("linha_total_manual", pd.Series(False, index=fact_aluguel.index))].copy()
        value_col = get_value_column(rent)
        item_col = get_item_column(rent, "rubrica")
        if value_col and item_col and {"mes_periodo", "mes_label"}.issubset(rent.columns):
            part = rent[["mes_periodo", "mes_label", item_col, value_col]].copy()
            part = part.rename(columns={item_col: "rubrica", value_col: "valor_real_dashboard"})
            part["fonte_dado"] = "fact_aluguel"
            part["linha_total_manual"] = False
            parts.append(part[columns])

    if not transactions.empty:
        tx = transactions[_original_category_norm(transactions).eq("custos marta")].copy()
        tx = tx[~tx.get("linha_total_manual", pd.Series(False, index=tx.index))].copy()
        item_col = get_item_column(tx, "nome_custo")
        if item_col and {"mes_periodo", "mes_label", "valor_real_dashboard"}.issubset(tx.columns):
            part = tx[["mes_periodo", "mes_label", item_col, "valor_real_dashboard"]].copy()
            part = part.rename(columns={item_col: "rubrica"})
            part["fonte_dado"] = "fact_transacoes / Custos Marta"
            part["linha_total_manual"] = False
            parts.append(part[columns])

    if not parts:
        return pd.DataFrame(columns=columns)
    return pd.concat(parts, ignore_index=True, sort=False)


def generic_fact_page(
    title: str,
    df: pd.DataFrame,
    item_fallback: str = "item",
    utility_df: pd.DataFrame | None = None,
):
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
    item_col = get_item_column(clean, item_fallback)

    c1, c2 = st.columns(2)
    with c1:
        metric_card("Total acumulado no ano", format_brl(total))
    with c2:
        last_month = monthly.iloc[-1] if not monthly.empty else None
        metric_card("Último mês disponível", format_brl(last_month["valor"] if last_month is not None else 0))

    if not monthly.empty:
        chart_left, chart_right = st.columns([1.15, 1]) if title == "Aluguel + contas" else (st.container(), None)
        with chart_left:
            monthly["valor_label"] = monthly["valor"].apply(format_brl)
            fig = px.line(
                monthly,
                x="mes_label",
                y="valor",
                markers=True,
                title="Evolução mensal",
                labels={"mes_label": "Mês", "valor": "Valor em R$"},
                text="valor_label",
                color_discrete_sequence=COLOR_SEQUENCE,
            )
            fig.update_traces(textposition="top center", textfont={"size": 12}, cliponaxis=False)
            add_average_line(fig, monthly, "valor")
            max_monthly_value = float(monthly["valor"].max()) if not monthly.empty else 0
            if max_monthly_value > 0:
                fig.update_yaxes(range=[0, max_monthly_value * 1.18])
            st.plotly_chart(fig, use_container_width=True)
        if chart_right is not None:
            with chart_right:
                utility_source = utility_df.copy() if utility_df is not None else clean
                utility_value_col = get_value_column(utility_source) if not utility_source.empty else None
                utility_item_col = get_item_column(utility_source, item_fallback) if not utility_source.empty else None
                utilities = (
                    build_luz_gas_monthly(utility_source, utility_value_col, utility_item_col)
                    if utility_value_col
                    else pd.DataFrame(columns=["mes_periodo", "mes_label", "conta", "valor"])
                )
                if utilities.empty:
                    st.info("Ainda não encontrei custos de Luz ou Gás para este período.")
                else:
                    utilities["valor_label"] = utilities["valor"].apply(format_brl)
                    fig = px.bar(
                        utilities,
                        x="mes_label",
                        y="valor",
                        color="conta",
                        barmode="group",
                        title="Luz e Gás por mês",
                        labels={"mes_label": "Mês", "valor": "Valor em R$", "conta": "Conta"},
                        text="valor_label",
                        color_discrete_sequence=COLOR_SEQUENCE,
                    )
                    fig.update_traces(textposition="outside", cliponaxis=False)
                    max_utility_value = float(utilities["valor"].max()) if not utilities.empty else 0
                    if max_utility_value > 0:
                        fig.update_yaxes(range=[0, max_utility_value * 1.25])
                    st.plotly_chart(fig, use_container_width=True)

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

    chart_bets = bets.melt(
        id_vars=["mes_periodo", "mes_label"],
        value_vars=["valor_investido", "valor_levantado", "saldo"],
        var_name="tipo",
        value_name="valor",
    )
    chart_bets["tipo"] = chart_bets["tipo"].replace(
        {
            "valor_investido": "Investido",
            "valor_levantado": "Levantado",
            "saldo": "Saldo",
        }
    )
    chart_bets["valor_label"] = chart_bets["valor"].apply(format_brl)
    month_order = bets.sort_values("mes_periodo")["mes_label"].tolist()

    fig = px.bar(
        chart_bets,
        x="mes_label",
        y="valor",
        color="tipo",
        barmode="group",
        title="Investido, levantado e saldo por mês",
        labels={"mes_label": "Mês", "valor": "Valor em R$", "tipo": "Tipo"},
        text="valor_label",
        category_orders={"mes_label": month_order, "tipo": ["Investido", "Levantado", "Saldo"]},
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    if not chart_bets.empty:
        max_bet_value = float(chart_bets["valor"].max())
        min_bet_value = float(chart_bets["valor"].min())
        upper_padding = abs(max_bet_value) * 0.2 if max_bet_value else 1
        lower_padding = abs(min_bet_value) * 0.25 if min_bet_value < 0 else 0
        fig.update_yaxes(range=[min(0, min_bet_value - lower_padding), max_bet_value + upper_padding])
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

    transactions = data.get("fact_transacoes", pd.DataFrame())
    diagnostics = build_transaction_diagnostics(transactions)

    st.subheader("A. Resumo da leitura")
    if diagnostics["resumo"].empty:
        st.info("A aba fact_transacoes está vazia ou não foi carregada.")
    else:
        st.dataframe(diagnostics["resumo"], width="stretch", hide_index=True)

    st.subheader("B. Linhas excluídas dos gastos pessoais")
    if diagnostics["exclusoes"].empty:
        st.success("Nenhuma linha foi excluída dos gastos pessoais.")
    else:
        st.dataframe(diagnostics["exclusoes"], width="stretch", hide_index=True)

    st.subheader("C. Totais por mês")
    if diagnostics["meses"].empty:
        st.info("Ainda não há meses reconhecidos em fact_transacoes.")
    else:
        st.dataframe(diagnostics["meses"], width="stretch", hide_index=True)

    st.subheader("D. Totais por categoria")
    if diagnostics["categorias"].empty:
        st.info("Ainda não há categorias consideradas nos gastos pessoais.")
    else:
        st.dataframe(diagnostics["categorias"], width="stretch", hide_index=True)

    st.subheader("E. Totais por origem")
    if diagnostics["origens"].empty:
        st.info("Ainda não há origens consideradas nos gastos pessoais.")
    else:
        st.dataframe(diagnostics["origens"], width="stretch", hide_index=True)

    st.subheader("F. Amostra das linhas consideradas nos gastos pessoais")
    if diagnostics["incluidas"].empty:
        st.info("Nenhuma linha entrou no cálculo de gastos pessoais.")
    else:
        st.dataframe(diagnostics["incluidas"], width="stretch", hide_index=True)

    st.subheader("G. Amostra das linhas excluídas")
    if diagnostics["excluidas"].empty:
        st.info("Nenhuma linha foi excluída dos gastos pessoais.")
    else:
        st.dataframe(diagnostics["excluidas"], width="stretch", hide_index=True)

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
    annual_transactions = apply_global_filters(transactions, [], selected_origins, selected_categories)
    balance_transactions = filter_by_month(transactions, selected_months)
    annual_balance_transactions = transactions.copy()

    page = st.sidebar.radio(
        "Página",
        [
            "Visão Geral",
            "Transações",
            "Categorias",
            "Marta",
            "Aluguel + contas",
            "Apostas KTO",
            "Diagnóstico da Base",
        ],
    )

    if page == "Visão Geral":
        page_visao_geral(data, balance_transactions, selected_months, annual_balance_transactions)
    elif page == "Transações":
        page_transacoes(filtered_transactions)
    elif page == "Categorias":
        page_categorias(filtered_transactions, data.get("dim_meses", pd.DataFrame()))
    elif page == "Marta":
        page_marta(filter_by_month(data.get("fact_marta", pd.DataFrame()), selected_months))
    elif page == "Aluguel + contas":
        aluguel_contas = build_aluguel_contas_dataset(
            data.get("fact_aluguel", pd.DataFrame()),
            transactions,
        )
        generic_fact_page(
            "Aluguel + contas",
            filter_by_month(aluguel_contas, selected_months),
            utility_df=filter_by_month(data.get("fact_marta", pd.DataFrame()), selected_months),
        )
    elif page == "Apostas KTO":
        page_apostas(data, filtered_transactions)
    elif page == "Diagnóstico da Base":
        page_diagnostico(data)


if __name__ == "__main__":
    render_app()
