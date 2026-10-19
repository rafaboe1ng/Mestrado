# Módulo `grafo`

## Propósito
Construir o `GrafoConhecimento` a partir das três fontes (produto, processo, série + estados), com
vocabulário fechado de tipos e relações e proveniência em toda aresta. É o que o artigo chama de
"arquitetura semântica unificada".

## Contrato
- Entrada: `ProdutoFeatures`, `ConhecimentoProcesso`, `SerieMultivariada`, `EstadosOperacionais`.
- Saída: `contracts.grafo.GrafoConhecimento`, validada (tipos, domínio/contradomínio, proveniência).

## Vocabulário (hoje)
Nós: produto, feature, parametro, objetivo, regra, job, operacao, estado, maquina.
Relações: tem_feature, adjacente_a, requer, aplica_a, restringe, impacta, executa, executado_em,
usa_parametro, tem_operacao, imprime, observado_como, ocorre_durante.

## Como funciona hoje
`construir()` adiciona as entidades de cada fonte e marca a proveniência (`cad_features/...`,
`processo/regra:R1`, `sensores/meta:job`, `regimes/kmeans_janelas`). Estados contíguos iguais viram um
segmento (`segmentos`). `metricas_integracao()` dá cobertura e proveniência (P1, P2). Exporta JSON e GraphML.

## Limites
- Um grafo por job. Grafo "de frota" (vários jobs, mesmo produto) é a extensão natural para aprender com histórico.
- Sem inferência de relações: tudo que está no grafo foi colocado por uma fonte.

## O que não funcionou e por quê
- (preencher)

## Pendências
- Revisar o vocabulário contra as features e operações reais (fase 6), com ADR por mudança.
