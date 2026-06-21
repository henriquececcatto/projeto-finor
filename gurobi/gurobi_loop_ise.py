import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import gurobipy as gp
from gurobipy import GRB

# =====================================================
# CONFIGURAÇÕES
# =====================================================

ARQUIVO = "01_base_dados_modelo_ISE.csv"

COLUNA_DATA = "Date"
COLUNA_IBOV = "Retorno_IBOV_Simples"

PESO_MINIMO = 0.02
PESO_MAXIMO = 0.30

K_INICIAL = 5
K_FINAL = 20

DIAS_UTEIS_ANO = 252


# =====================================================
# 1. LER A BASE
# =====================================================

df = pd.read_csv(ARQUIVO, sep=";", decimal=",")

df[COLUNA_DATA] = pd.to_datetime(df[COLUNA_DATA])

ativos = [
    coluna for coluna in df.columns
    if coluna not in [COLUNA_DATA, COLUNA_IBOV]
]

retornos_ativos = df[ativos].to_numpy()
retorno_ibov = df[COLUNA_IBOV].to_numpy()

T = retornos_ativos.shape[0]
N = retornos_ativos.shape[1]

print("Base carregada com sucesso!")
print("Número de dias:", T)
print("Número de ativos:", N)


# =====================================================
# 2. FUNÇÃO PARA CALCULAR MÉTRICAS
# =====================================================

def calcular_metricas(retorno_carteira, retorno_ibov):
    erro_ativo = retorno_carteira - retorno_ibov

    tracking_error_diario = np.std(erro_ativo)
    tracking_error_anualizado = tracking_error_diario * np.sqrt(DIAS_UTEIS_ANO)

    retorno_total = np.prod(1 + retorno_carteira) - 1
    retorno_anualizado = (1 + retorno_total) ** (DIAS_UTEIS_ANO / len(retorno_carteira)) - 1

    retorno_ibov_total = np.prod(1 + retorno_ibov) - 1
    retorno_ibov_anualizado = (1 + retorno_ibov_total) ** (DIAS_UTEIS_ANO / len(retorno_ibov)) - 1

    volatilidade_anualizada = np.std(retorno_carteira) * np.sqrt(DIAS_UTEIS_ANO)

    if volatilidade_anualizada != 0:
        sharpe = retorno_anualizado / volatilidade_anualizada
    else:
        sharpe = np.nan

    correlacao = np.corrcoef(retorno_carteira, retorno_ibov)[0, 1]

    return {
        "Retorno Total": retorno_total,
        "Retorno Anualizado": retorno_anualizado,
        "Retorno IBOV Total": retorno_ibov_total,
        "Retorno IBOV Anualizado": retorno_ibov_anualizado,
        "Tracking Error Diário": tracking_error_diario,
        "Tracking Error Anualizado": tracking_error_anualizado,
        "Volatilidade Anualizada": volatilidade_anualizada,
        "Sharpe": sharpe,
        "Correlação com IBOV": correlacao
    }


# =====================================================
# 3. FUNÇÃO PARA OTIMIZAR UMA CARTEIRA COM K ATIVOS
# =====================================================

def otimizar_com_gurobi(k):
    print(f"\nRodando Gurobi para k={k}...")

    modelo = gp.Model(f"index_tracking_ISE_k_{k}")

    # Para não poluir muito a tela
    modelo.Params.OutputFlag = 0

    # Limite de tempo por carteira, em segundos
    modelo.Params.TimeLimit = 120

    # Gap de otimalidade
    modelo.Params.MIPGap = 0.0001

    # Variáveis de peso
    w = modelo.addVars(
        N,
        lb=0.0,
        ub=PESO_MAXIMO,
        vtype=GRB.CONTINUOUS,
        name="w"
    )

    # Variáveis binárias
    z = modelo.addVars(
        N,
        vtype=GRB.BINARY,
        name="z"
    )

    # Soma dos pesos = 100%
    modelo.addConstr(
        gp.quicksum(w[i] for i in range(N)) == 1,
        name="soma_pesos"
    )

    # Exatamente k ativos
    modelo.addConstr(
        gp.quicksum(z[i] for i in range(N)) == k,
        name="quantidade_ativos"
    )

    # Peso mínimo e máximo apenas para ativos escolhidos
    for i in range(N):
        modelo.addConstr(
            w[i] <= PESO_MAXIMO * z[i],
            name=f"peso_max_{i}"
        )

        modelo.addConstr(
            w[i] >= PESO_MINIMO * z[i],
            name=f"peso_min_{i}"
        )

    # Função objetivo: minimizar erro quadrático médio contra o Ibovespa
    objetivo = gp.QuadExpr()

    for t in range(T):
        retorno_carteira_t = gp.quicksum(
            float(retornos_ativos[t, i]) * w[i]
            for i in range(N)
        )

        erro_t = retorno_carteira_t - float(retorno_ibov[t])

        objetivo += erro_t * erro_t

    objetivo = objetivo / T

    modelo.setObjective(objetivo, GRB.MINIMIZE)

    modelo.optimize()

    if modelo.SolCount == 0:
        print(f"Nenhuma solução encontrada para k={k}.")
        return None, None, None

    pesos = np.array([w[i].X for i in range(N)])

    retorno_carteira = retornos_ativos @ pesos

    metricas = calcular_metricas(
        retorno_carteira=retorno_carteira,
        retorno_ibov=retorno_ibov
    )

    print(
        f"k={k} concluído | "
        f"Tracking Error Anualizado: {metricas['Tracking Error Anualizado']:.6f} | "
        f"Correlação: {metricas['Correlação com IBOV']:.6f}"
    )

    return pesos, retorno_carteira, metricas


# =====================================================
# 4. RODAR K = 5 ATÉ 20
# =====================================================

resultados = []
pesos_resultados = []
retornos_carteiras = {}

for k in range(K_INICIAL, K_FINAL + 1):
    pesos, retorno_carteira, metricas = otimizar_com_gurobi(k)

    if pesos is None:
        continue

    ativos_selecionados = []

    for i, peso in enumerate(pesos):
        if peso > 0.000001:
            ativos_selecionados.append(ativos[i])

            pesos_resultados.append({
                "K": k,
                "Ativo": ativos[i],
                "Peso": peso
            })

    resultados.append({
        "K": k,
        "Quantidade de Ativos": len(ativos_selecionados),
        "Ativos Selecionados": ", ".join(ativos_selecionados),
        "Retorno Total": metricas["Retorno Total"],
        "Retorno Anualizado": metricas["Retorno Anualizado"],
        "Retorno IBOV Total": metricas["Retorno IBOV Total"],
        "Retorno IBOV Anualizado": metricas["Retorno IBOV Anualizado"],
        "Tracking Error Diário": metricas["Tracking Error Diário"],
        "Tracking Error Anualizado": metricas["Tracking Error Anualizado"],
        "Volatilidade Anualizada": metricas["Volatilidade Anualizada"],
        "Sharpe": metricas["Sharpe"],
        "Correlação com IBOV": metricas["Correlação com IBOV"]
    })

    retornos_carteiras[k] = retorno_carteira


# =====================================================
# 5. ORGANIZAR RESULTADOS
# =====================================================

resultados_df = pd.DataFrame(resultados)
pesos_df = pd.DataFrame(pesos_resultados)

resultados_df = resultados_df.sort_values(
    by="Tracking Error Anualizado",
    ascending=True
).reset_index(drop=True)

print("\n====================================")
print("RANKING FINAL - GUROBI ISE")
print("====================================")
print(resultados_df)


# =====================================================
# 6. SALVAR EM EXCEL
# =====================================================

nome_excel = "resultado_gurobi_loop_ISE.xlsx"

with pd.ExcelWriter(nome_excel, engine="xlsxwriter") as writer:
    resultados_df.to_excel(writer, sheet_name="Ranking", index=False)
    pesos_df.to_excel(writer, sheet_name="Pesos", index=False)

    workbook = writer.book

    formato_percentual = workbook.add_format({"num_format": "0.00%"})
    formato_numero = workbook.add_format({"num_format": "0.000000"})
    formato_cabecalho = workbook.add_format({
        "bold": True,
        "bg_color": "#D9EAD3",
        "border": 1
    })

    for sheet_name in ["Ranking", "Pesos"]:
        worksheet = writer.sheets[sheet_name]
        worksheet.freeze_panes(1, 0)
        worksheet.set_column(0, 20, 20)

        if sheet_name == "Ranking":
            colunas = resultados_df.columns
        else:
            colunas = pesos_df.columns

        for col_num, valor in enumerate(colunas):
            worksheet.write(0, col_num, valor, formato_cabecalho)

print("\nPlanilha salva como:", nome_excel)


# =====================================================
# 7. GERAR GRÁFICO DAS 5 MELHORES CARTEIRAS
# =====================================================

df["IBOV_Acumulado"] = np.cumprod(1 + retorno_ibov) - 1

plt.figure(figsize=(12, 6))

plt.plot(
    df[COLUNA_DATA],
    df["IBOV_Acumulado"],
    label="Ibovespa",
    linewidth=2
)

top_5 = resultados_df.head(5)

for _, linha in top_5.iterrows():
    k = int(linha["K"])
    retorno_carteira = retornos_carteiras[k]
    acumulado = np.cumprod(1 + retorno_carteira) - 1

    plt.plot(
        df[COLUNA_DATA],
        acumulado,
        label=f"Gurobi k={k}"
    )

plt.title("Retorno acumulado: Gurobi ISE vs Ibovespa")
plt.xlabel("Data")
plt.ylabel("Retorno acumulado")
plt.grid(True)
plt.legend()
plt.tight_layout()

nome_grafico = "grafico_gurobi_loop_ISE.png"

plt.savefig(nome_grafico, dpi=150)

print("Gráfico salvo como:", nome_grafico)

print("\nFinalizado com sucesso!")