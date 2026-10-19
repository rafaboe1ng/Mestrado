# Guia do avaliador externo

Gerado por `docs/gerar_quadro.py` em 2026-10-19T14:16-03:00. **Não editar à mão.**

Para cada obrigação do `PLANO.md`: como reproduzir o número, onde ele está gravado e o que inspecionar à mão.
Tudo que vem da bateria sintética leva o rótulo SINTÉTICO e não vale como evidência sobre a impressora (PLANO, P3).

## P0 — pipeline fecha sobre os contratos

- Reproduzir: `python -m experimentos.exp01_pipeline_sintetico` e depois `python docs/gerar_quadro.py`.
- Número: `resultado.proposto.contratos_violados` em `resultados/exp01_pipeline_sintetico__20261019T141624.json`.
- Critério declarado: ≤ 0. Status atual: **atendida**.

## P1 — grafo integra as tres fontes (cobertura)

- Reproduzir: `python -m experimentos.exp01_pipeline_sintetico` e depois `python docs/gerar_quadro.py`.
- Número: `resultado.proposto.grafo_cobertura_pct` em `resultados/exp01_pipeline_sintetico__20261019T141624.json`.
- Critério declarado: ≥ 100. Status atual: **atendida**.

## P2 — toda aresta tem proveniencia

- Reproduzir: `python -m experimentos.exp01_pipeline_sintetico` e depois `python docs/gerar_quadro.py`.
- Número: `resultado.proposto.grafo_proveniencia_pct` em `resultados/exp01_pipeline_sintetico__20261019T141624.json`.
- Critério declarado: ≥ 100. Status atual: **atendida**.
- Inspeção manual: leia as explicações abaixo e anote, para cada uma, se o caminho faz sentido e se cada passo diz de onde veio (nota 0–2).
  - **job_009** → causa `parede`, regras ['R2'], ajustes [('resfriamento', 40.0, 60.0)], trade-offs {'tempo_pct': 0.0, 'material_pct': 0.0, 'qualidade_pontos': 1.0}
    - job:job_009 -observado_como-> estado:job_009:4: estado 'anomalia' com anomalia entre 300 e 420 s [regimes/kmeans_janelas]
    - estado:job_009:4 -ocorre_durante-> operacao:job_009:op2_parede: sobreposicao de 120 s com a operacao [regimes/kmeans_janelas]
    - operacao:job_009:op2_parede -imprime-> feature:suporte_L@v009:parede: a operacao imprime a feature 'parede' [sensores/meta:job_009]
    - feature:suporte_L@v009:parede -requer-> parametro:resfriamento: regra R2 exige resfriamento >= 60.0 [processo/regra:R2]
    - job:job_009 -usa_parametro-> parametro:resfriamento: o job usou resfriamento = 40.0 [sensores/meta:job_009]
  - **job_010** → causa `parede`, regras ['R1'], ajustes [('velocidade', 80.0, 45.0)], trade-offs {'tempo_pct': 77.78, 'material_pct': 0.0, 'qualidade_pontos': 0.0}
    - job:job_010 -observado_como-> estado:job_010:3: estado 'anomalia' com anomalia entre 300 e 420 s [regimes/kmeans_janelas]
    - estado:job_010:3 -ocorre_durante-> operacao:job_010:op2_parede: sobreposicao de 120 s com a operacao [regimes/kmeans_janelas]
    - operacao:job_010:op2_parede -imprime-> feature:suporte_L@v010:parede: a operacao imprime a feature 'parede' [sensores/meta:job_010]
    - feature:suporte_L@v010:parede -requer-> parametro:velocidade: regra R1 exige velocidade <= 45.0 [processo/regra:R1]
    - job:job_010 -usa_parametro-> parametro:velocidade: o job usou velocidade = 80.0 [sensores/meta:job_010]
  - **job_013** → causa `aba`, regras ['R3'], ajustes [('velocidade', 60.0, 50.0)], trade-offs {'tempo_pct': 20.0, 'material_pct': 0.0, 'qualidade_pontos': 0.0}
    - job:job_013 -observado_como-> estado:job_013:4: estado 'anomalia' com anomalia entre 490 e 550 s [regimes/kmeans_janelas]
    - estado:job_013:4 -ocorre_durante-> operacao:job_013:op3_aba: sobreposicao de 60 s com a operacao [regimes/kmeans_janelas]
    - operacao:job_013:op3_aba -imprime-> feature:suporte_L@v013:aba: a operacao imprime a feature 'aba' [sensores/meta:job_013]
    - feature:suporte_L@v013:aba -requer-> parametro:velocidade: regra R3 exige velocidade <= 50.0 [processo/regra:R3]
    - job:job_013 -usa_parametro-> parametro:velocidade: o job usou velocidade = 60.0 [sensores/meta:job_013]
  - **job_014** → causa `aba`, regras ['R3'], ajustes [('velocidade', 60.0, 50.0)], trade-offs {'tempo_pct': 20.0, 'material_pct': 0.0, 'qualidade_pontos': 0.0}
    - job:job_014 -observado_como-> estado:job_014:3: estado 'anomalia' com anomalia entre 490 e 550 s [regimes/kmeans_janelas]
    - estado:job_014:3 -ocorre_durante-> operacao:job_014:op3_aba: sobreposicao de 60 s com a operacao [regimes/kmeans_janelas]
    - operacao:job_014:op3_aba -imprime-> feature:suporte_L@v014:aba: a operacao imprime a feature 'aba' [sensores/meta:job_014]
    - feature:suporte_L@v014:aba -requer-> parametro:velocidade: regra R3 exige velocidade <= 50.0 [processo/regra:R3]
    - job:job_014 -usa_parametro-> parametro:velocidade: o job usou velocidade = 60.0 [sensores/meta:job_014]
  - **job_015** → causa `aba`, regras ['R3'], ajustes [('velocidade', 60.0, 50.0)], trade-offs {'tempo_pct': 20.0, 'material_pct': 0.0, 'qualidade_pontos': 0.0}
    - job:job_015 -observado_como-> estado:job_015:4: estado 'anomalia' com anomalia entre 490 e 550 s [regimes/kmeans_janelas]
    - estado:job_015:4 -ocorre_durante-> operacao:job_015:op3_aba: sobreposicao de 60 s com a operacao [regimes/kmeans_janelas]
    - operacao:job_015:op3_aba -imprime-> feature:suporte_L@v015:aba: a operacao imprime a feature 'aba' [sensores/meta:job_015]
    - feature:suporte_L@v015:aba -requer-> parametro:velocidade: regra R3 exige velocidade <= 50.0 [processo/regra:R3]
    - job:job_015 -usa_parametro-> parametro:velocidade: o job usou velocidade = 60.0 [sensores/meta:job_015]

## P3 — anomalias por clustering vs limiar simples (sintetico)

- Reproduzir: `python -m experimentos.exp01_pipeline_sintetico` e depois `python docs/gerar_quadro.py`.
- Número: `resultado.proposto.anomalia_f1` em `resultados/exp01_pipeline_sintetico__20261019T141624.json`. Baseline: `resultado.baseline_limiar.anomalia_f1`.
- Critério declarado: ≥ 0.7 e ≥ baseline + 0.1. Status atual: **atendida**.

## P4 — atribuicao da causa pelo grafo

- Reproduzir: `python -m experimentos.exp01_pipeline_sintetico` e depois `python docs/gerar_quadro.py`.
- Número: `resultado.proposto.acuracia_causa` em `resultados/exp01_pipeline_sintetico__20261019T141624.json`. Baseline: `resultado.baseline_geometrico.acuracia_causa`.
- Critério declarado: ≥ 0.8 e ≥ baseline + 0.15. Status atual: **atendida**.

## P5 — ajustes viaveis

- Reproduzir: `python -m experimentos.exp01_pipeline_sintetico` e depois `python docs/gerar_quadro.py`.
- Número: `resultado.proposto.taxa_viavel` em `resultados/exp01_pipeline_sintetico__20261019T141624.json`. Baseline: `resultado.baseline_geometrico.taxa_viavel`.
- Critério declarado: ≥ 1.0. Status atual: **atendida**.

## P6 — ajustes resolvem as regras violadas

- Reproduzir: `python -m experimentos.exp01_pipeline_sintetico` e depois `python docs/gerar_quadro.py`.
- Número: `resultado.proposto.taxa_resolve` em `resultados/exp01_pipeline_sintetico__20261019T141624.json`. Baseline: `resultado.baseline_geometrico.taxa_resolve`.
- Critério declarado: ≥ 0.9 e ≥ baseline + 0.2. Status atual: **atendida**.

## P7 — trade-offs informados pela mesma regua

- Reproduzir: `python -m experimentos.exp01_pipeline_sintetico` e depois `python docs/gerar_quadro.py`.
- Número: `resultado.proposto.taxa_tradeoffs` em `resultados/exp01_pipeline_sintetico__20261019T141624.json`. Baseline: `resultado.baseline_geometrico.taxa_tradeoffs`.
- Critério declarado: ≥ 1.0. Status atual: **atendida**.

## P8 — explicacao completa para toda causa atribuida

- Reproduzir: `python -m experimentos.exp01_pipeline_sintetico` e depois `python docs/gerar_quadro.py`.
- Número: `resultado.proposto.taxa_explicacao_completa` em `resultados/exp01_pipeline_sintetico__20261019T141624.json`.
- Critério declarado: ≥ 1.0. Status atual: **atendida**.
- Inspeção manual: leia as explicações abaixo e anote, para cada uma, se o caminho faz sentido e se cada passo diz de onde veio (nota 0–2).
  - **job_009** → causa `parede`, regras ['R2'], ajustes [('resfriamento', 40.0, 60.0)], trade-offs {'tempo_pct': 0.0, 'material_pct': 0.0, 'qualidade_pontos': 1.0}
    - job:job_009 -observado_como-> estado:job_009:4: estado 'anomalia' com anomalia entre 300 e 420 s [regimes/kmeans_janelas]
    - estado:job_009:4 -ocorre_durante-> operacao:job_009:op2_parede: sobreposicao de 120 s com a operacao [regimes/kmeans_janelas]
    - operacao:job_009:op2_parede -imprime-> feature:suporte_L@v009:parede: a operacao imprime a feature 'parede' [sensores/meta:job_009]
    - feature:suporte_L@v009:parede -requer-> parametro:resfriamento: regra R2 exige resfriamento >= 60.0 [processo/regra:R2]
    - job:job_009 -usa_parametro-> parametro:resfriamento: o job usou resfriamento = 40.0 [sensores/meta:job_009]
  - **job_010** → causa `parede`, regras ['R1'], ajustes [('velocidade', 80.0, 45.0)], trade-offs {'tempo_pct': 77.78, 'material_pct': 0.0, 'qualidade_pontos': 0.0}
    - job:job_010 -observado_como-> estado:job_010:3: estado 'anomalia' com anomalia entre 300 e 420 s [regimes/kmeans_janelas]
    - estado:job_010:3 -ocorre_durante-> operacao:job_010:op2_parede: sobreposicao de 120 s com a operacao [regimes/kmeans_janelas]
    - operacao:job_010:op2_parede -imprime-> feature:suporte_L@v010:parede: a operacao imprime a feature 'parede' [sensores/meta:job_010]
    - feature:suporte_L@v010:parede -requer-> parametro:velocidade: regra R1 exige velocidade <= 45.0 [processo/regra:R1]
    - job:job_010 -usa_parametro-> parametro:velocidade: o job usou velocidade = 80.0 [sensores/meta:job_010]
  - **job_013** → causa `aba`, regras ['R3'], ajustes [('velocidade', 60.0, 50.0)], trade-offs {'tempo_pct': 20.0, 'material_pct': 0.0, 'qualidade_pontos': 0.0}
    - job:job_013 -observado_como-> estado:job_013:4: estado 'anomalia' com anomalia entre 490 e 550 s [regimes/kmeans_janelas]
    - estado:job_013:4 -ocorre_durante-> operacao:job_013:op3_aba: sobreposicao de 60 s com a operacao [regimes/kmeans_janelas]
    - operacao:job_013:op3_aba -imprime-> feature:suporte_L@v013:aba: a operacao imprime a feature 'aba' [sensores/meta:job_013]
    - feature:suporte_L@v013:aba -requer-> parametro:velocidade: regra R3 exige velocidade <= 50.0 [processo/regra:R3]
    - job:job_013 -usa_parametro-> parametro:velocidade: o job usou velocidade = 60.0 [sensores/meta:job_013]
  - **job_014** → causa `aba`, regras ['R3'], ajustes [('velocidade', 60.0, 50.0)], trade-offs {'tempo_pct': 20.0, 'material_pct': 0.0, 'qualidade_pontos': 0.0}
    - job:job_014 -observado_como-> estado:job_014:3: estado 'anomalia' com anomalia entre 490 e 550 s [regimes/kmeans_janelas]
    - estado:job_014:3 -ocorre_durante-> operacao:job_014:op3_aba: sobreposicao de 60 s com a operacao [regimes/kmeans_janelas]
    - operacao:job_014:op3_aba -imprime-> feature:suporte_L@v014:aba: a operacao imprime a feature 'aba' [sensores/meta:job_014]
    - feature:suporte_L@v014:aba -requer-> parametro:velocidade: regra R3 exige velocidade <= 50.0 [processo/regra:R3]
    - job:job_014 -usa_parametro-> parametro:velocidade: o job usou velocidade = 60.0 [sensores/meta:job_014]
  - **job_015** → causa `aba`, regras ['R3'], ajustes [('velocidade', 60.0, 50.0)], trade-offs {'tempo_pct': 20.0, 'material_pct': 0.0, 'qualidade_pontos': 0.0}
    - job:job_015 -observado_como-> estado:job_015:4: estado 'anomalia' com anomalia entre 490 e 550 s [regimes/kmeans_janelas]
    - estado:job_015:4 -ocorre_durante-> operacao:job_015:op3_aba: sobreposicao de 60 s com a operacao [regimes/kmeans_janelas]
    - operacao:job_015:op3_aba -imprime-> feature:suporte_L@v015:aba: a operacao imprime a feature 'aba' [sensores/meta:job_015]
    - feature:suporte_L@v015:aba -requer-> parametro:velocidade: regra R3 exige velocidade <= 50.0 [processo/regra:R3]
    - job:job_015 -usa_parametro-> parametro:velocidade: o job usou velocidade = 60.0 [sensores/meta:job_015]

## P9 — P1-P8 com dados reais

- Reproduzir: `python -m experimentos.exp02_dados_reais` e depois `python docs/gerar_quadro.py`.
- Número: `resultado.proposto.anomalia_f1` em experimento `exp02_dados_reais` ainda não existe. Baseline: `resultado.baseline_limiar.anomalia_f1`.
- Critério declarado: fixar antes da primeira coleta (ROTEIRO, fase 3). Status atual: **pendente**.

## P10 — nucleo independente de dominio (desejavel)

- Reproduzir: `python -m experimentos.exp03_segunda_base` e depois `python docs/gerar_quadro.py`.
- Número: `resultado.arquivos_alterados` em experimento `exp03_segunda_base` ainda não existe.
- Critério declarado: ≤ 0. Status atual: **pendente**.

