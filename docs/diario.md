# Diário

Por data e autor: o que mudou e o que ficou pendente. Escrito à mão (é o único documento de `docs/` que é).

## 2026-10-23 — Rafael
- Histórico do repositório reescrito para deixar só a pesquisa: material de referência e figuras de apresentação
  saíram de todos os commits e entraram no `.gitignore`. Os hashes gravados nas
  execuções #1 e #2 do exp01 referem-se a commits anteriores à reescrita; o exp01 foi rodado de novo (#3,
  repetição) para religar o resultado ao histórico atual.
- Decisão: ontologia formal (OWL/RDF) fica fora do escopo por enquanto; o vocabulário de `contracts/grafo.py`
  cumpre o papel de parte conceitual.
- Pendências novas: pauta da próxima reunião; fontes para R1–R5; busca de dataset público de impressão 3D com
  sensores; rascunho do protocolo de coleta e dos critérios de P9.

## 2026-10-19 — Rafael
- Movido o material anterior (artigos, figura-problema, resumo das orientações) para uma pasta local fora do git.
- Criado o esqueleto no modelo "cada afirmação aponta para um arquivo que a prova": `PLANO.md` (P0–P10),
  `ROTEIRO.md`, `CONTRIBUTING.md`, contratos, módulos, bateria sintética com gabarito, exp01 com
  proveniência, testes por módulo, diagnóstico por etapa, ADR-001..003, `docs/gerar_quadro.py`.
- Primeiro commit (`7411a66`), 39 testes passando, diagnóstico OK em `job_009`.
- exp01 execução #1 (fora da amostra, SINTÉTICO): proposto F1 0,97 / causa 1,00 / resolve 1,00; baselines de
  atribuição 0,81 e 0,75 na causa e 0,375 em resolver; baseline de limiar F1 0,32. Nove obrigações atendidas
  (P0–P8), duas pendentes (P9 dados reais, P10 domínio).
- O baseline de limiar estava fraco por construção (média + 3 desvios inflada pelas anomalias da calibração).
  Trocado por mediana + 3·MAD e exp01 rodado de novo (execução #2, repetição). Critério de P3 inalterado.
- Observado e registrado em `docs/modulos/regimes.md`: k=4 não separa resfriamento; janela 1 de aquecimento
  vira falso positivo pelo limiar de distância.
- **exp01 execução #2 (repetição): o baseline robusto venceu o k-means na detecção (F1 0,994 vs 0,969).**
  P3 "não atendida" no sintético. Motivo: anomalia sintética é pico num canal só; o limiar é o detector ótimo
  ali. Decisão registrada: não mexer no gerador; P3 se decide com dados reais. O resto (P0–P2, P4–P8) segue
  atendido. Quadro: 8 atendidas, 1 não atendida, 2 pendentes.
- Pendências:
  - obrigações do PLANO estão em status `proposta`; discutir e aceitar na próxima reunião;
  - calibrar k e largura de janela só nos jobs de calibração (ADR); tratar o falso positivo da janela 1;
  - confirmar com João se GNN entra (ADR-001) e qual impressora/sensores (ROTEIRO, fase 0);
  - regras R1–R5 da base FDM/PLA sem fonte: marcar as que forem confirmadas;
  - `cad_features.extrair_de_malha` não implementada (ficha JSON por enquanto).

## 2026-10-16 — Rafael
- Reunião: tema definido (grafos + ML para mapear design → processo; impressão 3D; sensores). Ata com
  "murilloskrzek" = João.
- Figura-problema feita e refeita duas vezes: primeiro genérica, depois no mecanismo do João (alteração de
  design → desvio nos sensores → atribuição da causa), depois direcionada ao abstract do artigo
  (representações fragmentadas vs. grafo de conhecimento), a pedido do Leonardo.
- Pendência registrada: o exemplo de "gasto de material" foi meu e superficial; e a fala "o professor
  quer otimizar o processo" não está confirmada por ele.
