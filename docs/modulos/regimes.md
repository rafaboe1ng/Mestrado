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
- **2026-10-19, exp01 execução #1** (`resultados/exp01_pipeline_sintetico__20261019T141624.json`, SINTÉTICO):
  - Com k=4 o k-means **não separou o resfriamento**: dividiu a impressão em dois clusters (`impressao`,
    `impressao_2`), provavelmente por velocidade, que desloca a média de corrente e de vibração. Não afeta a
    detecção de anomalia, mas derruba a pureza (0,93) e mostra que a heurística de nomeação depende de k.
    Pendente: calibrar k (4, 5) e a largura da janela (10 s, 20 s) só nos jobs de calibração, e registrar por ADR.
  - A **janela 1 (rampa de aquecimento)** foi marcada como anomalia pelo limiar de distância (percentil 99) em
    vários jobs: é a janela com a maior inclinação de temperatura do job inteiro. Falso positivo sistemático
    no início. Opções: não aplicar o critério de distância à fase de aquecimento, ou percentil 99,5.
  - O **baseline de limiar com média + 3 desvios deu F1 0,32**: as janelas anômalas presentes na calibração
    inflam média e desvio e o limiar sobe demais, perdendo revocação. Comparar o método com um baseline
    assim é fácil demais. A partir da execução #2 o baseline oficial é **mediana + 3·MAD** (`robusto=True`);
    o critério de P3 não mudou, o baseline ficou mais forte. A primeira execução fica no histórico.
- **2026-10-19, exp01 execução #2** (`resultados/exp01_pipeline_sintetico__20261019T141826.json`, SINTÉTICO, repetição):
  - Com o baseline robusto, **o limiar simples venceu**: F1 0,994 e pureza 0,98 contra 0,969 e 0,93 do k-means.
    **P3 fica "não atendida" na bateria sintética.** Isso não é um bug a esconder; é a circularidade do PLANO (P3)
    aparecendo: a anomalia sintética é um pico num único canal, então um limiar nesse canal é o detector ótimo.
    O k-means perde precisão nos outliers de distância (janela 1 de aquecimento) e não ganha nada na detecção
    porque não há anomalia multivariada na bateria.
  - O que isso diz sobre o método: o valor do clustering, se existir, está em (a) anomalias que só aparecem na
    combinação de canais, (b) estados e transições (padrões operacionais) que um limiar não dá, e (c) o mapeamento
    desses estados para o grafo. Nada disso é testável nesta bateria. **Decisão: não ajustar o gerador para o
    método vencer.** P3 só se decide com dados reais (P9), e a bateria sintética passa a provar só P0–P2 e a
    exercitar P4–P8, como a ADR-002 já dizia.
  - Melhorias legítimas no método, para testar na calibração real e não aqui: não aplicar o critério de distância à
    fase de aquecimento; k=5; janela de 20 s; e um baseline multivariado (limiar por canal com voto) como segundo baseline.

## Pendências
- Comparar k-means com um método de densidade quando houver dados reais (ADR-003 prevê adaptador).
- Variante "isolada": avaliar atribuição com as janelas do gabarito, separando erro de detecção de erro de atribuição.
