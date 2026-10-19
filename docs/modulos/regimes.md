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

## Pendências
- Comparar k-means com um método de densidade quando houver dados reais (ADR-003 prevê adaptador).
- Variante "isolada": avaliar atribuição com as janelas do gabarito, separando erro de detecção de erro de atribuição.
