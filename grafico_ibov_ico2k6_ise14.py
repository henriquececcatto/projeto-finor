import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

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


# =====================================================
# FUNÇÃO PARA CALCULAR RETORNO DA CARTEIRA
# =====================================================

def calcular_retorno_carteira(base_csv, arquivo_resultado, k, nome_carteira):
    # Ler base de retornos
    base = pd.read_csv(base_csv, sep=";", decimal=",")
    base[COLUNA_DATA] = pd.to_datetime(base[COLUNA_DATA])

    # Ler pesos do Gurobi
    pesos = pd.read_excel(arquivo_resultado, sheet_name="Pesos")

    # Filtrar apenas a carteira desejada
    pesos_k = pesos[pesos["K"] == k].copy()

    # Ordenar por peso, só para facilitar a leitura
    pesos_k = pesos_k.sort_values(by="Peso", ascending=False)

    ativos = pesos_k["Ativo"].tolist()
    pesos_array = pesos_k["Peso"].to_numpy()

    print(f"\nCarteira {nome_carteira} k={k}")
    print("--------------------------------")
    print(pesos_k[["Ativo", "Peso"]])

    # Calcular retorno diário da carteira
    base[f"Retorno_{nome_carteira}"] = base[ativos].to_numpy() @ pesos_array

    return base[[COLUNA_DATA, COLUNA_IBOV, f"Retorno_{nome_carteira}"]]


# =====================================================
# CALCULAR RETORNOS DAS DUAS CARTEIRAS
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
# JUNTAR AS BASES PELA DATA
# =====================================================

dados = pd.merge(
    dados_ico2[[COLUNA_DATA, COLUNA_IBOV, "Retorno_ICO2_k6"]],
    dados_ise[[COLUNA_DATA, "Retorno_ISE_k14"]],
    on=COLUNA_DATA,
    how="inner"
)


# =====================================================
# CALCULAR RETORNO ACUMULADO
# =====================================================

dados["IBOV_Acumulado"] = (1 + dados[COLUNA_IBOV]).cumprod() - 1
dados["ICO2_k6_Acumulado"] = (1 + dados["Retorno_ICO2_k6"]).cumprod() - 1
dados["ISE_k14_Acumulado"] = (1 + dados["Retorno_ISE_k14"]).cumprod() - 1


# =====================================================
# CALCULAR VALOR FINAL COM R$ 10.000
# =====================================================

valor_final_ibov = VALOR_INICIAL * (1 + dados["IBOV_Acumulado"].iloc[-1])
valor_final_ico2 = VALOR_INICIAL * (1 + dados["ICO2_k6_Acumulado"].iloc[-1])
valor_final_ise = VALOR_INICIAL * (1 + dados["ISE_k14_Acumulado"].iloc[-1])

print("\n====================================")
print("VALOR FINAL COM R$ 10.000")
print("====================================")
print("Ibovespa:    R$", round(valor_final_ibov, 2))
print("ICO2 k=6:    R$", round(valor_final_ico2, 2))
print("ISE k=14:    R$", round(valor_final_ise, 2))


# =====================================================
# GERAR GRÁFICO
# =====================================================

plt.figure(figsize=(12, 6))

plt.plot(
    dados[COLUNA_DATA],
    dados["IBOV_Acumulado"] * 100,
    label="Ibovespa",
    linewidth=2
)

plt.plot(
    dados[COLUNA_DATA],
    dados["ICO2_k6_Acumulado"] * 100,
    label="ICO2 k=6",
    linewidth=2
)

plt.plot(
    dados[COLUNA_DATA],
    dados["ISE_k14_Acumulado"] * 100,
    label="ISE k=14",
    linewidth=2
)

plt.title("Retorno acumulado: Ibovespa vs ICO2 k=6 vs ISE k=14")
plt.xlabel("Data")
plt.ylabel("Retorno acumulado (%)")
plt.grid(True)
plt.legend()
plt.tight_layout()

nome_grafico = "grafico_ibov_ico2k6_ise14.png"

plt.savefig(nome_grafico, dpi=150)

print("\nGráfico salvo como:", nome_grafico)


# =====================================================
# SALVAR BASE DO GRÁFICO EM EXCEL
# =====================================================

nome_excel = "dados_grafico_ibov_ico2k6_ise14.xlsx"

dados.to_excel(nome_excel, index=False)

print("Base do gráfico salva como:", nome_excel)

print("\nFinalizado com sucesso!")