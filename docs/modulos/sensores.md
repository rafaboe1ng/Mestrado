# Módulo `sensores`

## Propósito
Ler e escrever a `SerieMultivariada` de um job: tempo, canais, valores, parâmetros usados e as operações
que a máquina executava em cada trecho (que feature estava sendo impressa quando).

## Contrato
- Em disco: `serie.csv` (t_s, canais...) e `meta.json` (job, produto, canais, taxa, parâmetros, operações).
- Saída: `contracts.sensores.SerieMultivariada`, validada.
- `janelar(serie, largura_s)` é o único ponto onde a série vira janelas; `regimes` usa isso.

## Como funciona hoje
Só o formato sintético. As operações vêm do gerador; na máquina real virão do log do firmware/fatiador
(G-code comentado por feature ou tempo por camada).

## Limites
- Sem alinhamento de relógios entre sensores externos e log da impressora. Isso vai ser o primeiro problema
  real (fase 4) e merece um teste próprio.
- Sem reamostragem: assume taxa constante.

## O que não funcionou e por quê
- Ainda nada em dados reais.

## Pendências
- Dicionário de sensores (ROTEIRO, fase 3): canal, unidade, taxa, posição, o que mede do processo.
- Adaptador do log real → `OperacaoJob` por feature.
