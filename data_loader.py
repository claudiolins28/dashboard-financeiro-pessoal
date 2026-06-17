from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials


SPREADSHEET_ID = "1qnSVRbC_5wfd4QWbEMj4jyxfjR9jg60IgcSLTNzq2Sk"
ANALYSIS_YEAR = 2026

SHEET_NAMES = [
    "fact_transacoes",
    "dim_meses",
    "dim_categorias",
    "fact_marta",
    "fact_aluguel",
    "fact_apostas_kto",
    "fact_balanco_mensal",
    "README_modelo",
]

EXPECTED_COLUMNS = {
    "fact_transacoes": [
        "mes",
        "descricao",
        "origem",
        "categoria_dashboard",
        "categoria_original_excel",
        "valor_real_dashboard",
        "valor_euro_dashboard",
        "entra_custo_pessoal",
        "parcela_compra",
    ],
    "dim_meses": ["mes"],
    "fact_marta": ["mes"],
    "fact_aluguel": ["mes"],
    "fact_apostas_kto": ["mes"],
}

TOTAL_PATTERN = re.compile(
    r"\b(?:total|subtotal|sub\s*total|custo\s*total|receita\s*liquida|receita\s*líquida|saldo\s*final)\b",
    flags=re.IGNORECASE,
)

MONTHS_PT = {
    "jan": 1,
    "janeiro": 1,
    "fev": 2,
    "fevereiro": 2,
    "mar": 3,
    "marco": 3,
    "março": 3,
    "abr": 4,
    "abril": 4,
    "mai": 5,
    "maio": 5,
    "jun": 6,
    "junho": 6,
    "jul": 7,
    "julho": 7,
    "ago": 8,
    "agosto": 8,
    "set": 9,
    "setembro": 9,
    "out": 10,
    "outubro": 10,
    "nov": 11,
    "novembro": 11,
    "dez": 12,
    "dezembro": 12,
}

MONTH_LABELS = {
    1: "Jan",
    2: "Fev",
    3: "Mar",
    4: "Abr",
    5: "Mai",
    6: "Jun",
    7: "Jul",
    8: "Ago",
    9: "Set",
    10: "Out",
    11: "Nov",
    12: "Dez",
}


@dataclass
class SheetIssue:
    sheet: str
    level: str
    message: str


@dataclass
class DataLoadResult:
    data: dict[str, pd.DataFrame]
    demo_mode: bool
    message: str | None = None


def normalize_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_column_name(name: Any) -> str:
    text = normalize_text(name)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def secrets_available() -> bool:
    try:
        return "google_service_account" in st.secrets
    except Exception:
        return False


def _to_plain_dict(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _to_plain_dict(item) for key, item in value.items()}
    return value


def get_gspread_client() -> gspread.Client:
    if not secrets_available():
        raise RuntimeError(
            "Credenciais não encontradas. Configure [google_service_account] em .streamlit/secrets.toml "
            "ou nos Secrets do Streamlit Community Cloud."
        )

    info = _to_plain_dict(st.secrets["google_service_account"])
    if "private_key" in info:
        info["private_key"] = str(info["private_key"]).replace("\\n", "\n")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    try:
        credentials = Credentials.from_service_account_info(info, scopes=scopes)
        return gspread.authorize(credentials)
    except Exception as exc:
        raise RuntimeError(
            "Não foi possível autenticar na Google Sheets API. Verifique se o secret da Service Account "
            "está completo e se a planilha foi compartilhada com o client_email."
        ) from exc


def _empty_sheet_frame() -> pd.DataFrame:
    return pd.DataFrame()


def _parse_number(value: Any) -> float | None:
    if pd.isna(value) or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return None

    negative = text.startswith("(") and text.endswith(")")
    text = text.replace("R$", "").replace("€", "").replace(" ", "")
    text = text.replace("\u00a0", "")
    text = text.strip("()")

    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")

    text = re.sub(r"[^0-9.\-]", "", text)
    if text in {"", "-", "."}:
        return None

    try:
        number = float(text)
    except ValueError:
        return None
    return -number if negative else number


def _month_from_value(value: Any) -> str | None:
    if pd.isna(value) or value == "":
        return None

    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m")

    if isinstance(value, (int, float)) and 1 <= int(value) <= 12:
        return f"{ANALYSIS_YEAR}-{int(value):02d}"

    text = str(value).strip()
    if not text:
        return None

    parsed = pd.to_datetime(text, dayfirst=True, errors="coerce")
    if pd.notna(parsed):
        return parsed.strftime("%Y-%m")

    normalized = normalize_text(text).replace(".", "")
    if normalized.isdigit() and 1 <= int(normalized) <= 12:
        return f"{ANALYSIS_YEAR}-{int(normalized):02d}"

    for month_name, month_number in MONTHS_PT.items():
        if re.search(rf"\b{re.escape(month_name)}\b", normalized):
            year_match = re.search(r"\b(20\d{2})\b", normalized)
            year = int(year_match.group(1)) if year_match else ANALYSIS_YEAR
            return f"{year}-{month_number:02d}"
    return None


def month_label(month_period: Any) -> str:
    if pd.isna(month_period) or not month_period:
        return "Sem mês"
    try:
        year, month = str(month_period).split("-")[:2]
        return f"{MONTH_LABELS.get(int(month), month)}/{year}"
    except Exception:
        return str(month_period)


def _ensure_month_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "mes" in df.columns:
        df["mes_periodo"] = df["mes"].apply(_month_from_value)
    elif "data" in df.columns:
        dates = pd.to_datetime(df["data"], dayfirst=True, errors="coerce")
        df["mes_periodo"] = dates.dt.strftime("%Y-%m")
    else:
        df["mes_periodo"] = None
    df["mes_label"] = df["mes_periodo"].apply(month_label)
    return df


def _add_text_helpers(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for column in [
        "descricao",
        "origem",
        "categoria_dashboard",
        "categoria_original_excel",
        "entra_custo_pessoal",
        "parcela_compra",
        "item",
        "tipo",
    ]:
        if column in df.columns:
            df[f"{column}_norm"] = df[column].apply(normalize_text)
    return df


def _add_total_flags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    text_columns = [
        col
        for col in [
            "descricao",
            "categoria_dashboard",
            "categoria_original_excel",
            "item",
            "tipo",
        ]
        if col in df.columns
    ]
    if not text_columns:
        df["linha_total_manual"] = False
        return df

    combined = df[text_columns].fillna("").astype(str).agg(" ".join, axis=1).apply(normalize_text)
    df["linha_total_manual"] = combined.str.contains(TOTAL_PATTERN, na=False)
    return df


def _add_transaction_flags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    category = df.get("categoria_dashboard_norm", pd.Series("", index=df.index)).fillna("")
    description = df.get("descricao_norm", pd.Series("", index=df.index)).fillna("")
    origin = df.get("origem_norm", pd.Series("", index=df.index)).fillna("")
    combined = (category + " " + description + " " + origin).apply(normalize_text)
    source_is_bet = (
        df.get("is_bet", pd.Series(False, index=df.index)).apply(normalize_text).isin(["sim", "s", "yes", "true", "1"])
    )
    source_is_bet_retorno = df.get("is_bet_retorno", pd.Series(False, index=df.index)).apply(normalize_text).isin(
        ["sim", "s", "yes", "true", "1"]
    )

    df["is_bet_retorno"] = category.str.fullmatch(
        r"(?:bet retorno|retorno bet|aposta retorno|apostas retorno)", na=False
    ) | source_is_bet_retorno
    df["is_bet_investimento"] = category.str.fullmatch(r"(?:bet|aposta|apostas|kto)", na=False) | source_is_bet
    df.loc[df["is_bet_retorno"], "is_bet_investimento"] = False

    df["is_pagamento_fatura"] = combined.str.contains(
        r"\b(?:fatura|pagamento de fatura|pagamento cartao|pagamento cartão)\b", na=False
    )

    if "entra_custo_pessoal_norm" in df.columns:
        df["entra_custo_pessoal_bool"] = df["entra_custo_pessoal_norm"].isin(["sim", "s", "yes", "true", "1"])
    else:
        df["entra_custo_pessoal_bool"] = False

    value_valid = (
        df["valor_real_dashboard"].notna() if "valor_real_dashboard" in df.columns else pd.Series(False, index=df.index)
    )
    df["custo_pessoal_valido"] = (
        df["entra_custo_pessoal_bool"]
        & value_valid
        & ~df["linha_total_manual"]
        & ~df["is_pagamento_fatura"]
        & ~df["is_bet_investimento"]
        & ~df["is_bet_retorno"]
    )
    df["motivo_exclusao"] = ""
    df.loc[~value_valid, "motivo_exclusao"] = "valor nulo ou inválido"
    df.loc[value_valid & df["linha_total_manual"], "motivo_exclusao"] = "total/subtotal"
    df.loc[value_valid & ~df["linha_total_manual"] & df["is_bet_retorno"], "motivo_exclusao"] = "categoria Bet retorno"
    df.loc[
        value_valid & ~df["linha_total_manual"] & ~df["is_bet_retorno"] & df["is_bet_investimento"],
        "motivo_exclusao",
    ] = "categoria Bet"
    df.loc[
        value_valid
        & ~df["linha_total_manual"]
        & ~df["is_bet_retorno"]
        & ~df["is_bet_investimento"]
        & df["is_pagamento_fatura"],
        "motivo_exclusao",
    ] = "fatura/cartão"
    df.loc[
        value_valid
        & ~df["linha_total_manual"]
        & ~df["is_bet_retorno"]
        & ~df["is_bet_investimento"]
        & ~df["is_pagamento_fatura"]
        & ~df["entra_custo_pessoal_bool"],
        "motivo_exclusao",
    ] = "entra_custo_pessoal = Não"
    return df


def _standardize_sheet(df: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
    if df.empty:
        return _empty_sheet_frame()

    df = df.copy()
    df.columns = [normalize_column_name(col) for col in df.columns]
    df = df.dropna(how="all")
    if sheet_name == "fact_transacoes":
        if "origem" not in df.columns and "fonte" in df.columns:
            df["origem"] = df["fonte"]
        if "descricao" not in df.columns and "nome_custo" in df.columns:
            df["descricao"] = df["nome_custo"]

    for column in [col for col in df.columns if col.startswith("data") or col == "date"]:
        df[column] = pd.to_datetime(df[column], dayfirst=True, errors="coerce")

    numeric_candidates = []
    for col in df.columns:
        if col.startswith(("entra_", "categoria_", "tipo_", "descricao_")):
            continue
        if any(term in col for term in ["valor", "receita", "salario", "aluguel", "saldo"]):
            numeric_candidates.append(col)
            continue
        if "custo" in col and not col.startswith("entra_custo"):
            numeric_candidates.append(col)
    for column in numeric_candidates:
        df[column] = df[column].apply(_parse_number)

    df = _ensure_month_columns(df)
    df = _add_text_helpers(df)
    df = _add_total_flags(df)
    if sheet_name == "fact_transacoes":
        df = _add_transaction_flags(df)

    df["aba_origem"] = sheet_name
    return df


def _read_sheet(spreadsheet: gspread.Spreadsheet, sheet_name: str) -> pd.DataFrame:
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound as exc:
        raise RuntimeError(f"A aba '{sheet_name}' não foi encontrada no Google Sheets.") from exc

    rows = worksheet.get_all_records(numericise_ignore=["all"])
    if not rows:
        return _empty_sheet_frame()
    return pd.DataFrame(rows)


@st.cache_data(ttl=600, show_spinner="Carregando dados do Google Sheets...")
def load_google_sheets(spreadsheet_id: str = SPREADSHEET_ID) -> dict[str, pd.DataFrame]:
    client = get_gspread_client()
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
    except Exception as exc:
        raise RuntimeError(
            "Não foi possível abrir a planilha. Confirme o Spreadsheet ID e compartilhe a planilha com o client_email."
        ) from exc

    data: dict[str, pd.DataFrame] = {}
    for sheet_name in SHEET_NAMES:
        raw = _read_sheet(spreadsheet, sheet_name)
        data[sheet_name] = _standardize_sheet(raw, sheet_name)
    return data


def _demo_rows() -> dict[str, list[dict[str, Any]]]:
    transactions = [
        {
            "mes": "Janeiro",
            "data": "05/01/2026",
            "descricao": "Supermercado Continente",
            "origem": "Conta Corrente",
            "categoria_dashboard": "Mercado",
            "categoria_original_excel": "Supermercado",
            "valor_real_dashboard": "850,00",
            "valor_euro_dashboard": "145,00",
            "entra_custo_pessoal": "Sim",
            "parcela_compra": "1 de 1",
        },
        {
            "mes": "Janeiro",
            "data": "11/01/2026",
            "descricao": "Restaurante fim de semana",
            "origem": "Cartão de Crédito",
            "categoria_dashboard": "Lazer",
            "categoria_original_excel": "Restaurantes",
            "valor_real_dashboard": "320,00",
            "valor_euro_dashboard": "55,00",
            "entra_custo_pessoal": "Sim",
            "parcela_compra": "1 de 1",
        },
        {
            "mes": "Janeiro",
            "data": "18/01/2026",
            "descricao": "Pagamento de fatura cartão",
            "origem": "Conta Corrente",
            "categoria_dashboard": "Cartão de Crédito",
            "categoria_original_excel": "Fatura",
            "valor_real_dashboard": "1170,00",
            "valor_euro_dashboard": "200,00",
            "entra_custo_pessoal": "Sim",
            "parcela_compra": "1 de 1",
        },
        {
            "mes": "Fevereiro",
            "data": "04/02/2026",
            "descricao": "Farmácia",
            "origem": "Conta Corrente",
            "categoria_dashboard": "Saúde",
            "categoria_original_excel": "Farmácia",
            "valor_real_dashboard": "210,00",
            "valor_euro_dashboard": "36,00",
            "entra_custo_pessoal": "Sim",
            "parcela_compra": "1 de 1",
        },
        {
            "mes": "Fevereiro",
            "data": "09/02/2026",
            "descricao": "Curso Python parcelado",
            "origem": "Cartão de Crédito",
            "categoria_dashboard": "Educação",
            "categoria_original_excel": "Cursos",
            "valor_real_dashboard": "180,00",
            "valor_euro_dashboard": "31,00",
            "entra_custo_pessoal": "Sim",
            "parcela_compra": "1 de 3",
        },
        {
            "mes": "Fevereiro",
            "data": "12/02/2026",
            "descricao": "KTO aposta",
            "origem": "Cartão de Crédito",
            "categoria_dashboard": "Bet",
            "categoria_original_excel": "Apostas",
            "valor_real_dashboard": "250,00",
            "valor_euro_dashboard": "43,00",
            "entra_custo_pessoal": "Sim",
            "parcela_compra": "1 de 1",
        },
        {
            "mes": "Fevereiro",
            "data": "20/02/2026",
            "descricao": "KTO levantamento",
            "origem": "Conta Corrente",
            "categoria_dashboard": "Bet retorno",
            "categoria_original_excel": "Apostas retorno",
            "valor_real_dashboard": "140,00",
            "valor_euro_dashboard": "24,00",
            "entra_custo_pessoal": "Não",
            "parcela_compra": "1 de 1",
        },
        {
            "mes": "Março",
            "data": "06/03/2026",
            "descricao": "Mercado mensal",
            "origem": "Conta Corrente",
            "categoria_dashboard": "Mercado",
            "categoria_original_excel": "Supermercado",
            "valor_real_dashboard": "920,00",
            "valor_euro_dashboard": "157,00",
            "entra_custo_pessoal": "Sim",
            "parcela_compra": "1 de 1",
        },
        {
            "mes": "Março",
            "data": "14/03/2026",
            "descricao": "Uber e transportes",
            "origem": "Cartão de Crédito",
            "categoria_dashboard": "Transporte",
            "categoria_original_excel": "Mobilidade",
            "valor_real_dashboard": "260,00",
            "valor_euro_dashboard": "44,00",
            "entra_custo_pessoal": "Sim",
            "parcela_compra": "1 de 1",
        },
        {
            "mes": "Março",
            "data": "31/03/2026",
            "descricao": "Total março",
            "origem": "",
            "categoria_dashboard": "Total",
            "categoria_original_excel": "Total",
            "valor_real_dashboard": "1180,00",
            "valor_euro_dashboard": "201,00",
            "entra_custo_pessoal": "Sim",
            "parcela_compra": "1 de 1",
        },
    ]

    return {
        "fact_transacoes": transactions,
        "dim_meses": [
            {"mes": "Janeiro", "receita_salario": "12000,00"},
            {"mes": "Fevereiro", "receita_salario": "12000,00"},
            {"mes": "Março", "receita_salario": "12500,00"},
        ],
        "dim_categorias": [
            {"categoria_dashboard": "Mercado", "grupo": "Custo variável"},
            {"categoria_dashboard": "Lazer", "grupo": "Custo variável"},
            {"categoria_dashboard": "Saúde", "grupo": "Custo variável"},
            {"categoria_dashboard": "Educação", "grupo": "Investimento pessoal"},
            {"categoria_dashboard": "Transporte", "grupo": "Custo variável"},
            {"categoria_dashboard": "Bet", "grupo": "Apostas"},
            {"categoria_dashboard": "Bet retorno", "grupo": "Apostas"},
        ],
        "fact_marta": [
            {"mes": "Janeiro", "item": "Aluguel", "valor_real_dashboard": "2250,00"},
            {"mes": "Janeiro", "item": "Condomínio", "valor_real_dashboard": "360,00"},
            {"mes": "Janeiro", "item": "IPTU", "valor_real_dashboard": "90,00"},
            {"mes": "Janeiro", "item": "Internet + TV", "valor_real_dashboard": "120,00"},
            {"mes": "Janeiro", "item": "Gympass", "valor_real_dashboard": "180,00"},
            {"mes": "Fevereiro", "item": "Aluguel", "valor_real_dashboard": "2250,00"},
            {"mes": "Fevereiro", "item": "Condomínio", "valor_real_dashboard": "365,00"},
            {"mes": "Fevereiro", "item": "Seguro telemóvel", "valor_real_dashboard": "45,00"},
            {"mes": "Fevereiro", "item": "Luz", "valor_real_dashboard": "160,00"},
            {"mes": "Fevereiro", "item": "Gás", "valor_real_dashboard": "70,00"},
            {"mes": "Fevereiro", "item": "Gympass", "valor_real_dashboard": "180,00"},
            {"mes": "Março", "item": "Aluguel", "valor_real_dashboard": "2250,00"},
            {"mes": "Março", "item": "Condomínio", "valor_real_dashboard": "370,00"},
            {"mes": "Março", "item": "IPTU", "valor_real_dashboard": "90,00"},
            {"mes": "Março", "item": "Internet + TV", "valor_real_dashboard": "120,00"},
            {"mes": "Março", "item": "Luz", "valor_real_dashboard": "150,00"},
            {"mes": "Março", "item": "Gás", "valor_real_dashboard": "65,00"},
            {"mes": "Março", "item": "Gympass", "valor_real_dashboard": "180,00"},
            {"mes": "Março", "item": "Total Marta", "valor_real_dashboard": "2865,00"},
        ],
        "fact_aluguel": [
            {"mes": "Janeiro", "item": "Aluguel", "valor_real_dashboard": "4500,00"},
            {"mes": "Janeiro", "item": "Condomínio", "valor_real_dashboard": "720,00"},
            {"mes": "Janeiro", "item": "IPTU", "valor_real_dashboard": "180,00"},
            {"mes": "Fevereiro", "item": "Aluguel", "valor_real_dashboard": "4500,00"},
            {"mes": "Fevereiro", "item": "Condomínio", "valor_real_dashboard": "730,00"},
            {"mes": "Fevereiro", "item": "Seguro incêndio", "valor_real_dashboard": "65,00"},
            {"mes": "Março", "item": "Aluguel", "valor_real_dashboard": "4500,00"},
            {"mes": "Março", "item": "Condomínio", "valor_real_dashboard": "740,00"},
            {"mes": "Março", "item": "Custo total aluguel", "valor_real_dashboard": "5240,00"},
        ],
        "fact_apostas_kto": [
            {"mes": "Fevereiro", "tipo": "bet", "descricao": "KTO aposta", "valor_real_dashboard": "250,00"},
            {"mes": "Fevereiro", "tipo": "bet retorno", "descricao": "KTO levantamento", "valor_real_dashboard": "140,00"},
            {"mes": "Março", "tipo": "bet", "descricao": "KTO aposta", "valor_real_dashboard": "100,00"},
        ],
        "fact_balanco_mensal": [
            {"mes": "Janeiro", "receita_liquida": "12000,00", "custo_total": "6570,00"},
            {"mes": "Fevereiro", "receita_liquida": "12000,00", "custo_total": "5905,00"},
            {"mes": "Março", "receita_liquida": "12500,00", "custo_total": "6420,00"},
        ],
        "README_modelo": [
            {"secao": "demo", "descricao": "Dados simulados para pré-visualização local sem secrets."}
        ],
    }


def load_demo_data() -> dict[str, pd.DataFrame]:
    rows_by_sheet = _demo_rows()
    data: dict[str, pd.DataFrame] = {}
    for sheet_name in SHEET_NAMES:
        raw = pd.DataFrame(rows_by_sheet.get(sheet_name, []))
        data[sheet_name] = _standardize_sheet(raw, sheet_name)
    return data


def load_dashboard_data(spreadsheet_id: str = SPREADSHEET_ID) -> DataLoadResult:
    try:
        data = load_google_sheets(spreadsheet_id)
        return DataLoadResult(data=data, demo_mode=False)
    except Exception as exc:
        return DataLoadResult(
            data=load_demo_data(),
            demo_mode=True,
            message=str(exc),
        )


def validate_loaded_data(data: dict[str, pd.DataFrame]) -> list[SheetIssue]:
    issues: list[SheetIssue] = []

    for sheet_name in SHEET_NAMES:
        if sheet_name not in data:
            issues.append(SheetIssue(sheet_name, "erro", "Aba não carregada."))
            continue

        df = data[sheet_name]
        expected = EXPECTED_COLUMNS.get(sheet_name, [])
        missing = [column for column in expected if column not in df.columns]
        if missing:
            issues.append(
                SheetIssue(
                    sheet_name,
                    "aviso",
                    "Colunas esperadas ausentes: " + ", ".join(missing),
                )
            )

        if "linha_total_manual" in df.columns and df["linha_total_manual"].any():
            issues.append(
                SheetIssue(
                    sheet_name,
                    "aviso",
                    f"{int(df['linha_total_manual'].sum())} linha(s) parecem total/subtotal e serão ignoradas nos cálculos.",
                )
            )

        if "mes_periodo" in df.columns and df["mes_periodo"].isna().any() and len(df) > 0:
            issues.append(
                SheetIssue(
                    sheet_name,
                    "aviso",
                    f"{int(df['mes_periodo'].isna().sum())} linha(s) sem mês reconhecido.",
                )
            )

        if sheet_name == "fact_transacoes" and not df.empty:
            if "valor_real_dashboard" in df.columns and df["valor_real_dashboard"].isna().any():
                issues.append(
                    SheetIssue(
                        sheet_name,
                        "aviso",
                        f"{int(df['valor_real_dashboard'].isna().sum())} linha(s) sem valor em R$ válido.",
                    )
                )
            if "categoria_dashboard" in df.columns and df["categoria_dashboard"].replace("", pd.NA).isna().any():
                issues.append(
                    SheetIssue(
                        sheet_name,
                        "aviso",
                        "Existem transações sem categoria_dashboard preenchida.",
                    )
                )

    return issues


def get_value_column(df: pd.DataFrame, preferred: str = "valor_real_dashboard") -> str | None:
    if preferred in df.columns:
        return preferred
    candidates = [col for col in df.columns if "valor" in col or "custo" in col]
    return candidates[0] if candidates else None
