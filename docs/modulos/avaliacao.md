# Módulo `avaliacao`

## Propósito
A régua única. Qualquer método (proposto ou baseline) entra com os mesmos objetos de contrato e sai com as
mesmas métricas. Nenhum método calcula o próprio valor (CONTRIBUTING, regra 7).

## Contrato
- Entrada: por job, `EstadosOperacionais`, `Recomendacao` e `violacoes_apos` (contadas pelo chamador com
  `processo.violacoes`), mais o gabarito.
- Saída: dicionário com agregados e `por_job`.

## Métricas
- Anomalia: precisão, revocação, F1 (micro, por janela). Pureza dos estados.
- Causa: acurácia (feature prevista == feature do gabarito; `None` == `None` conta como acerto).
- Viabilidade, resolução de violações (só nos jobs com violação no gabarito), trade-offs informados,
  explicação completa (só nos jobs com causa atribuída), Δtempo médio.

## Limites
- Micro-F1 favorece jobs longos; com jobs de duração diferente, reportar também por job.
- `causa_correta` é tudo-ou-nada; não dá crédito parcial quando há duas causas.

## O que não funcionou e por quê
- (preencher)

## Pendências
- Intervalos de confiança (bootstrap por job) quando houver jobs suficientes.
