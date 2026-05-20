library(dlookr)
library(reglin)
library(broom)
library(ggpubr)
library(olsrr)
library(reglin)
library(rcompanion)
library(dlookr)
library(tidyverse)
library(GGally)
library(openxlsx)

#setando diretório de trabalho
setwd("D:/Bootcamp")
retornos <- read.csv("ibov_retornos_simples.csv")
retornos_log <- read.csv("ibov_retornos_log.csv")

#análise inicial dos dados
str(retornos)
glimpse(retornos)
summary(retornos)

##########identificação de dados ausentes retorno simples###########
diagnose(retornos)
diag_ret <- diagnose(retornos)
print(diag_ret, n = Inf)
write.csv(diag_ret, "diagnostico_retornos.csv", row.names = FALSE)
write.xlsx(diag_ret, "diagnostico_retornos.xlsx")

#filtrando missing percent > 20
clean_retorno <- diag_ret$variables[diag_ret$missing_percent > 20]
retornos_filtrado <- retornos[, !(names(retornos) %in% clean_retorno)]
diag_ret2 <- diagnose(retornos_filtrado)
print(diag_ret2, n = Inf)
glimpse(retornos_filtrado)

summary(retornos_filtrado)

write.xlsx(retornos_filtrado, "retornos_simples_filtrados.xlsx")
write.xlsx(diag_ret2, "diagnostico_retornos_simples_filtrados.xlsx")

#verificando outliers
diagnose_numeric(retornos_filtrado)
outliers <- diagnose_outlier(retornos_filtrado)
outliers
plot_outlier(outliers)

write.xlsx(outliers, "outliers_simples.xlsx")


#criando relatório
#diagnose_web_report(retornos_filtrado)


#verificar correlação entre dados
correlate(retornos_filtrado)
correlate_retornosF <- correlate(retornos_filtrado)
print(correlate_retornosF, n = Inf)

write.xlsx(correlate_retornosF, "correlate_simples.xlsx")

##########identificação de dados ausentes retorno log###########

diagnose(retornos_log)
diag_ret_log <- diagnose(retornos_log)
print(diag_ret_log, n = Inf)
write.csv(diag_ret_log, "diagnostico_retornos_log.csv", row.names = FALSE)
write.xlsx(diag_ret_log, "diagnostico_retornos_log.xlsx")

#filtrando missing percent > 20 retornos_log
clean_retorno_log <- diag_ret_log$variables[diag_ret$missing_percent > 20]
retornos_log_filtrado <- retornos[, !(names(retornos) %in% clean_retorno)]
diag_ret2_log <- diagnose(retornos_log_filtrado)
print(diag_ret2, n = Inf)
glimpse(retornos_log_filtrado)
summary(retornos_log_filtrado)

write.xlsx(retornos_log_filtrado, "retornos_log_filtrados.xlsx")
write.xlsx(diag_ret2_log, "diagnostico_retornos_log_filtrados.xlsx")

#verificando outliers retornos_log
outliers_log <- diagnose_outlier(retornos_log_filtrado)
outliers_log
plot_outlier(outliers_log)

write.xlsx(outliers_log, "outliers_log.xlsx")

#verificar correlação entre dados retornos_log
correlate(retornos_log_filtrado)
correlate_retornosF_log <- correlate(retornos_log_filtrado)
print(correlate_retornosF_log, n = Inf)

