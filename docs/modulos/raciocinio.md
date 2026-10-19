# Módulo `raciocinio`

## Propósito
Do grafo para a `Recomendacao`: detectar que houve anomalia, atribuir a causa a uma feature de design via
caminho no grafo, propor ajustes viáveis e informar trade-offs. É o "raciocínio orientado por conhecimento"
do artigo e o mecanismo que o João descreveu na reunião (alteração de design → desvio → causa).

## Contrato
- Entrada: `GrafoConhecimento` e `job_id`.
- Saída: `contracts.recomendacao.Recomendacao`, validada (causa só com explicação; passos com proveniência).

## Como funciona hoje
`atribuir` percorre job → estado(anomalia) → operação → feature → requer → parâmetro e cruza com
job → usa_parametro. Onde o valor usado viola a restrição, a feature é a causa; o ajuste leva o parâmetro ao
limite da regra (o mais restritivo, se houver várias) dentro da faixa. `tradeoffs` lê as arestas `impacta`.
Baselines com a mesma saída: `baseline_geometrico` (parede mais fina) e `baseline_temporal` (feature ativa).

## Limites
- Só explica desvios que coincidem com uma regra violada. Desvio sem regra fica "sem causa" (correto no
  gabarito sintético; no real, pode ser regra que falta).
- Trade-offs lineares e declarados.

## O que não funcionou e por quê
- (preencher)

## Pendências
- Ranquear causas quando mais de uma feature tem regra violada no mesmo trecho.
- Guia do avaliador: 5 explicações lidas por alguém de fora (P8).
