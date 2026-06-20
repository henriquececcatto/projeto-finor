import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf

# =====================================================
# CONFIGURAÇÕES
# =====================================================

BASE_ICO2 = "01_base_dados_modelo_ICO2.csv"
BASE_ISE = "01_base_dados_modelo_ISE.csv"

RESULTADO_ICO2 = "resultado_gurobi_loop_ICO2.xlsx"
RESULTADO_ISE = "resultado_gurobi_loop_ISE.xlsx"

COLUNA_DATA = "Date"
COLUNA_IBOV = "Retorno_IBOV_Simples"

K_ICO2 = 6
K_ISE = 14

VALOR_INICIAL = 10000

TICKERS_ETF = ["ISUS11.SA", "ECOO11.SA"]


# =====================================================
# FUNÇÃO PARA CALCULAR RETORNO DA CARTEIRA GUROBI
# =====================================================

def calcular_retorno_carteira(base_csv, arquivo_resultado, k, nome_carteira):
    base = pd.read_csv(base_csv, sep=";", decimal=",")
    base[COLUNA_DATA] = pd.to_datetime(base[COLUNA_DATA])

    pesos = pd.read_excel(arquivo_resultado, sheet_name="Pesos")
    pesos_k = pesos[pesos["K"] == k].copy()

    pesos_k = pesos_k.sort_values(by="Peso", ascending=False)

    ativos = pesos_k["Ativo"].tolist()
    pesos_array = pesos_k["Peso"].to_numpy()

    print(f"\nCarteira {nome_carteira} k={k}")
    print("--------------------------------")
    print(pesos_k[["Ativo", "Peso"]])

    base[f"Retorno_{nome_carteira}"] = base[ativos].to_numpy() @ pesos_array

    return base[[COLUNA_DATA, COLUNA_IBOV, f"Retorno_{nome_carteira}"]]


# =====================================================
# 1. CALCULAR RETORNOS DAS CARTEIRAS GUROBI
# =====================================================

dados_ico2 = calcular_retorno_carteira(
    base_csv=BASE_ICO2,
    arquivo_resultado=RESULTADO_ICO2,
    k=K_ICO2,
    nome_carteira="ICO2_k6"
)

dados_ise = calcular_retorno_carteira(
    base_csv=BASE_ISE,
    arquivo_resultado=RESULTADO_ISE,
    k=K_ISE,
    nome_carteira="ISE_k14"
)


# =====================================================
# 2. JUNTAR IBOV, ICO2 K6 E ISE K14
# =====================================================

dados = pd.merge(
    dados_ico2[[COLUNA_DATA, COLUNA_IBOV, "Retorno_ICO2_k6"]],
    dados_ise[[COLUNA_DATA, "Retorno_ISE_k14"]],
    on=COLUNA_DATA,
    how="inner"
)

data_inicio = dados[COLUNA_DATA].min()
data_fim = dados[COLUNA_DATA].max()

print("\nPeríodo da base local:")
print("Início:", data_inicio.date())
print("Fim:", data_fim.date())


# =====================================================
# 3. BAIXAR PREÇOS DOS ETFs PELO YAHOO FINANCE
# =====================================================

print("\nBaixando ETFs pelo Yahoo Finance...")

precos = yf.download(
    TICKERS_ETF,
    start=data_inicio,
    end=data_fim + pd.Timedelta(days=1),
    auto_adjust=True,
    progress=False
)

# Quando baixa vários tickers, o yfinance costuma criar colunas em níveis.
# Queremos os preços de fechamento ajustados.
if isinstance(precos.columns, pd.MultiIndex):
    if "Close" in precos.columns.get_level_values(0):
        precos_close = precos["Close"].copy()
    else:
        raise ValueError("Não encontrei a coluna Close nos dados baixados.")
else:
    precos_close = precos[["Close"]].copy()

precos_close = precos_close.reset_index()
precos_close["Date"] = pd.to_datetime(precos_close["Date"])

print("\nPrévia dos preços dos ETFs:")
print(precos_close.head())


# =====================================================
# 4. CALCULAR RETORNO DIÁRIO DOS ETFs
# =====================================================

retornos_etfs = precos_close.copy()

for ticker in TICKERS_ETF:
    if ticker in retornos_etfs.columns:
        retornos_etfs[f"Retorno_{ticker}"] = retornos_etfs[ticker].pct_change()
    else:
        print(f"Atenção: ticker não encontrado no Yahoo Finance: {ticker}")

colunas_retornos_etfs = [COLUNA_DATA]

for ticker in TICKERS_ETF:
    coluna_retorno = f"Retorno_{ticker}"
    if coluna_retorno in retornos_etfs.columns:
        colunas_retornos_etfs.append(coluna_retorno)

retornos_etfs = retornos_etfs[colunas_retornos_etfs].dropna()


# =====================================================
# 5. JUNTAR TUDO NA MESMA BASE
# =====================================================

dados = pd.merge(
    dados,
    retornos_etfs,
    on=COLUNA_DATA,
    how="inner"
)

print("\nBase final comparativa:")
print(dados.head())
print("\nNúmero de dias após juntar com ETFs:", len(dados))


# =====================================================
# 6. CALCULAR RETORNOS ACUMULADOS
# =====================================================

dados["IBOV_Acumulado"] = (1 + dados[COLUNA_IBOV]).cumprod() - 1
dados["ICO2_k6_Acumulado"] = (1 + dados["Retorno_ICO2_k6"]).cumprod() - 1
dados["ISE_k14_Acumulado"] = (1 + dados["Retorno_ISE_k14"]).cumprod() - 1

if "Retorno_ISUS11.SA" in dados.columns:
    dados["ISUS11_Acumulado"] = (1 + dados["Retorno_ISUS11.SA"]).cumprod() - 1

if "Retorno_ECOO11.SA" in dados.columns:
    dados["ECOO11_Acumulado"] = (1 + dados["Retorno_ECOO11.SA"]).cumprod() - 1


# =====================================================
# 7. FUNÇÃO DE MÉTRICAS
# =====================================================

def calcular_metricas(nome, coluna_retorno):
    retorno = dados[coluna_retorno]

    retorno_total = (1 + retorno).prod() - 1
    retorno_anualizado = (1 + retorno_total) ** (252 / len(retorno)) - 1
    volatilidade_anualizada = retorno.std() * np.sqrt(252)

    if volatilidade_anualizada != 0:
        sharpe = retorno_anualizado / volatilidade_anualizada
    else:
        sharpe = np.nan

    valor_final = VALOR_INICIAL * (1 + retorno_total)

    return {
        "Ativo/Carteira": nome,
        "Retorno Total": retorno_total,
        "Retorno Anualizado": retorno_anualizado,
        "Volatilidade Anualizada": volatilidade_anualizada,
        "Sharpe": sharpe,
        "Valor Final R$ 10.000": valor_final
    }


metricas = []

metricas.append(calcular_metricas("Ibovespa", COLUNA_IBOV))
metricas.append(calcular_metricas("ICO2 k=6", "Retorno_ICO2_k6"))
metricas.append(calcular_metricas("ISE k=14", "Retorno_ISE_k14"))

if "Retorno_ISUS11.SA" in dados.columns:
    metricas.append(calcular_metricas("ETF ISUS11", "Retorno_ISUS11.SA"))

if "Retorno_ECOO11.SA" in dados.columns:
    metricas.append(calcular_metricas("ETF ECOO11", "Retorno_ECOO11.SA"))

metricas_df = pd.DataFrame(metricas)

print("\n====================================")
print("COMPARATIVO DE RETORNOS")
print("====================================")
print(metricas_df)


# =====================================================
# 8. GERAR GRÁFICO
# =====================================================

plt.figure(figsize=(13, 7))

plt.plot(
    dados[COLUNA_DATA],
    dados["IBOV_Acumulado"] * 100,
    label="Ibovespa",
    linewidth=2
)

plt.plot(
    dados[COLUNA_DATA],
    dados["ICO2_k6_Acumulado"] * 100,
    label="Carteira Gurobi ICO2 k=6",
    linewidth=2
)

plt.plot(
    dados[COLUNA_DATA],
    dados["ISE_k14_Acumulado"] * 100,
    label="Carteira Gurobi ISE k=14",
    linewidth=2
)

if "ISUS11_Acumulado" in dados.columns:
    plt.plot(
        dados[COLUNA_DATA],
        dados["ISUS11_Acumulado"] * 100,
        label="ETF ISUS11",
        linewidth=2
    )

if "ECOO11_Acumulado" in dados.columns:
    plt.plot(
        dados[COLUNA_DATA],
        dados["ECOO11_Acumulado"] * 100,
        label="ETF ECOO11",
        linewidth=2
    )

plt.title("Retorno acumulado: carteiras Gurobi vs ETFs sustentáveis vs Ibovespa")
plt.xlabel("Data")
plt.ylabel("Retorno acumulado (%)")
plt.grid(True)
plt.legend()
plt.tight_layout()

nome_grafico = "grafico_comparativo_etfs_gurobi.png"

plt.savefig(nome_grafico, dpi=150)

print("\nGráfico salvo como:", nome_grafico)


# =====================================================
# 9. SALVAR RESULTADOS EM EXCEL
# =====================================================

nome_excel = "comparativo_etfs_gurobi.xlsx"

with pd.ExcelWriter(nome_excel, engine="xlsxwriter") as writer:
    dados.to_excel(writer, sheet_name="Base Comparativa", index=False)
    metricas_df.to_excel(writer, sheet_name="Metricas", index=False)

    workbook = writer.book

    formato_cabecalho = workbook.add_format({
        "bold": True,
        "bg_color": "#D9EAD3",
        "border": 1
    })

    for sheet_name in ["Base Comparativa", "Metricas"]:
        worksheet = writer.sheets[sheet_name]
        worksheet.freeze_panes(1, 0)
        worksheet.set_column(0, 30, 22)

        if sheet_name == "Base Comparativa":
            colunas = dados.columns
        else:
            colunas = metricas_df.columns

        for col_num, coluna in enumerate(colunas):
            worksheet.write(0, col_num, coluna, formato_cabecalho)

print("Excel salvo como:", nome_excel)

print("\nFinalizado com sucesso!")