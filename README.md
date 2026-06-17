# Dashboard Financeiro Pessoal

Dashboard em Python com Streamlit para acompanhar a gestão financeira pessoal de 2026 a partir de um Google Sheets privado.

## Objetivo

Esta primeira versão prioriza:

- conexão segura ao Google Sheets via `gspread`;
- credenciais lidas por `st.secrets`;
- cálculos feitos pelo dashboard, sem depender de totais manuais na planilha;
- páginas para visão geral, transações, categorias, origem dos gastos, Marta, Aluguel/Casa, Apostas KTO e diagnóstico da base;
- estrutura simples para evoluir depois para SQLite, Supabase ou outra base.

## Estrutura

```text
app.py
data_loader.py
requirements.txt
.gitignore
README.md
.streamlit/secrets.toml.example
```

## Abas esperadas no Google Sheets

- `fact_transacoes`: fonte principal para análise de gastos.
- `dim_meses`: referência de meses e receita/salário, quando existir.
- `dim_categorias`: referência de categorias.
- `fact_marta`: itens individuais relacionados aos valores que a Marta deve pagar.
- `fact_aluguel`: itens individuais de aluguel/casa.
- `fact_apostas_kto`: apoio para a página de apostas KTO.
- `fact_balanco_mensal`: referência complementar, não usada como fonte principal de cálculo.
- `README_modelo`: documentação do modelo dentro da planilha.

## Regras principais de cálculo

- `fact_transacoes` é a fonte principal para gastos pessoais.
- `categoria_dashboard` é usada como categoria principal.
- `valor_real_dashboard` é a métrica principal em reais.
- `valor_euro_dashboard` é exibida como métrica complementar quando existir.
- Gastos pessoais consideram apenas linhas com `entra_custo_pessoal = Sim`.
- Linhas com termos como total, subtotal, sub total, custo total ou receita líquida são ignoradas nos cálculos.
- Pagamentos de fatura/cartão são identificados e ficam fora dos custos pessoais para evitar duplicação.
- Apostas (`bet` e `bet retorno`) ficam separadas na página Apostas KTO.
- Marta e Aluguel/Casa somam itens individuais e ignoram linhas de total.

## Instalação local

Crie um ambiente virtual e instale as dependências:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configurar secrets

Crie um ficheiro local:

```text
.streamlit/secrets.toml
```

Use `.streamlit/secrets.toml.example` como referência e preencha os valores reais da Google Service Account.

Importante:

- não comite `.streamlit/secrets.toml`;
- não crie `credentials.json` no repositório;
- compartilhe a planilha privada com o `client_email` da Service Account;
- mantenha a Google Sheets API ativa no projeto Google Cloud.

## Rodar localmente

```bash
streamlit run app.py
```

Se as credenciais estiverem ausentes ou inválidas, o app entra automaticamente em modo demo com dados simulados. Nesse caso, aparece o aviso:

```text
Modo demo activo: os dados abaixo são simulados. Configure os secrets para ligar ao Google Sheets real.
```

Assim é possível validar visualmente o dashboard antes de configurar a ligação real ao Google Sheets.

## Publicar no Streamlit Community Cloud

1. Suba o repositório para o GitHub sem credenciais reais.
2. No Streamlit Community Cloud, crie um novo app apontando para `app.py`.
3. Adicione o bloco `[google_service_account]` nos Secrets do app.
4. Confirme que o Google Sheets foi compartilhado com o `client_email`.
5. Faça o deploy.

## Evolução futura

A camada `data_loader.py` concentra conexão, limpeza básica, tratamento de datas, números e flags de exclusão. Isso facilita trocar a origem dos dados futuramente por SQLite, Supabase ou outra base sem reescrever toda a interface.
