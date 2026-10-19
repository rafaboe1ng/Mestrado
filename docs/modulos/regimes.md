# Módulo `regimes`

## Propósito
Transformar a série multivariada em `EstadosOperacionais`: por janela, um estado (aquecimento, impressão,
anomalia, resfriamento) e uma marca de anomalia. É a entrada "comportamento da máquina" do grafo.

## Contrato
- Entrada: `SerieMultivariada` (calibração e alvo).
- Saída: `contracts.estados.EstadosOperacionais`, validada. Carrega `metodo` e `config` para proveniência.

## Como funciona hoje
Proposto: média, desvio e inclinação por canal e janela → padronização → k-means (k=4, semente fixa) ajustado
nos jobs de calibração → nomeação dos clusters por heurística declarada (`_nomear`) → anomalia se a janela cai
no cluster de anomalia ou se a distância ao centroide passa do percentil 99 da calibração.
Baseline: desvio da vibração por janela acima de média + 3 desvios (calibração).

## Limites
- A nomeação depende de haver canais chamados `temperatura` e `vibracao`; sem eles, estados saem genéricos.
- k fixo. Com dados reais, k e a largura da janela viram hiperparâmetros a escolher na calibração (ADR).
- Circularidade com o gerador sintético (PLANO, P3).

## O que não funcionou e por quê
- (preencher a cada tentativa: o que mudou, o número antes e depois, o arquivo em `resultados/`)

## Pendências
- Comparar k-means com um método de densidade quando houver dados reais (ADR-003 prevê adaptador).
- Variante "isolada": avaliar atribuição com as janelas do gabarito, separando erro de detecção de erro de atribuição.
