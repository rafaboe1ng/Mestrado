# ADR-002 — Bateria sintética com gabarito fixado antes dos dados reais

- **Status**: proposta (2026-10-19).
- **Contexto**: não há impressora nem sensores definidos. Sem dados, o pipeline não pode ser exercitado, e sem
  pipeline não dá para saber que dados pedir.
- **Opções**:
  1. Esperar os dados reais e só então programar.
  2. Gerar uma bateria sintética determinística, com gabarito gravado antes de rodar, e usá-la só para provar
     P0–P2 e exercitar P3–P8.
  3. Usar um dataset público de impressão 3D com sensores, se houver um com log de operações por feature.
- **Decisão**: opção 2 agora; opção 3 fica como tarefa da fase 1 (revisão). A circularidade está declarada no
  PLANO (P3) e no README da bateria: a anomalia é injetada como aquilo que os métodos procuram.
- **Consequências**: nenhum número sintético pode ser usado como evidência sobre a impressora; toda tabela
  leva o rótulo SINTÉTICO (o exp01 grava `rotulo`); os critérios de P9 só podem ser fixados na fase 3, com o
  protocolo de coleta, e não copiados dos sintéticos.
