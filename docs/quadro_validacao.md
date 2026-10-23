# Quadro de validação

Gerado por `docs/gerar_quadro.py` em 2026-10-23T15:51-03:00. **Não editar à mão.** Critérios declarados em 2026-10-19 (`experimentos/obrigacoes.json`, espelho do `PLANO.md`).

| Obrigação | Métrica | Valor | Baseline | Critério | Status | Execução | Fonte |
|---|---|---|---|---|---|---|---|
| P0 pipeline fecha sobre os contratos | `proposto.contratos_violados` | 0 | — | ≤ 0 | **atendida** | #3 · repetição · SINTETICO | `resultados/exp01_pipeline_sintetico__20261023T155124.json` |
| P1 grafo integra as tres fontes (cobertura) | `proposto.grafo_cobertura_pct` | 100.000 | — | ≥ 100 | **atendida** | #3 · repetição · SINTETICO | `resultados/exp01_pipeline_sintetico__20261023T155124.json` |
| P2 toda aresta tem proveniencia | `proposto.grafo_proveniencia_pct` | 100.000 | — | ≥ 100 | **atendida** | #3 · repetição · SINTETICO | `resultados/exp01_pipeline_sintetico__20261023T155124.json` |
| P3 anomalias por clustering vs limiar simples (sintetico) | `proposto.anomalia_f1` | 0.969 | 0.994 | ≥ 0.7 e ≥ baseline + 0.1 | **não atendida** | #3 · repetição · SINTETICO | `resultados/exp01_pipeline_sintetico__20261023T155124.json` |
| P4 atribuicao da causa pelo grafo | `proposto.acuracia_causa` | 1.000 | 0.812 | ≥ 0.8 e ≥ baseline + 0.15 | **atendida** | #3 · repetição · SINTETICO | `resultados/exp01_pipeline_sintetico__20261023T155124.json` |
| P5 ajustes viaveis | `proposto.taxa_viavel` | 1.000 | 1.000 | ≥ 1.0 | **atendida** | #3 · repetição · SINTETICO | `resultados/exp01_pipeline_sintetico__20261023T155124.json` |
| P6 ajustes resolvem as regras violadas | `proposto.taxa_resolve` | 1.000 | 0.375 | ≥ 0.9 e ≥ baseline + 0.2 | **atendida** | #3 · repetição · SINTETICO | `resultados/exp01_pipeline_sintetico__20261023T155124.json` |
| P7 trade-offs informados pela mesma regua | `proposto.taxa_tradeoffs` | 1.000 | 1.000 | ≥ 1.0 | **atendida** | #3 · repetição · SINTETICO | `resultados/exp01_pipeline_sintetico__20261023T155124.json` |
| P8 explicacao completa para toda causa atribuida | `proposto.taxa_explicacao_completa` | 1.000 | — | ≥ 1.0 | **atendida** | #3 · repetição · SINTETICO | `resultados/exp01_pipeline_sintetico__20261023T155124.json` |
| P9 P1-P8 com dados reais | `proposto.anomalia_f1` | — | — | fixar antes da primeira coleta (ROTEIRO, fase 3) | **pendente** | — | experimento `exp02_dados_reais` ainda não existe |
| P10 nucleo independente de dominio (desejavel) | `arquivos_alterados` | — | — | ≤ 0 | **pendente** | — | experimento `exp03_segunda_base` ainda não existe |

## Resumo

- atendida: 8
- não atendida: 1
- pendente: 2

## Métodos lado a lado — exp01 (SINTETICO, commit ee689aa4, execução #3)

| método | anomalia_f1 | pureza_media | acuracia_causa | taxa_viavel | taxa_resolve | taxa_tradeoffs | taxa_explicacao_completa | delta_tempo_medio_pct |
|---|---|---|---|---|---|---|---|---|
| proposto | 0.969 | 0.933 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 31.111 |
| baseline_limiar | 0.994 | 0.982 | — | — | — | — | — | — |
| baseline_geometrico | 0.969 | 0.933 | 0.812 | 1.000 | 0.375 | 1.000 | 1.000 | 20.000 |
| baseline_temporal | 0.969 | 0.933 | 0.750 | 1.000 | 0.375 | 1.000 | 1.000 | 20.000 |
