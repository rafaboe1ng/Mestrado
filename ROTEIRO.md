# ROTEIRO — a sequência do trabalho

Ordem proposta, do ponto em que estamos até a defesa. Cada fase tem entregas, o que depende dela e o que
precisa ser confirmado com João, Leonardo e o professor. Prazos ficam para a reunião: aqui está a
dependência entre as etapas, não o calendário.

## Fase 0 — Alinhamento (agora → próxima reunião)
Entregas:
- figura-problema direcionada ao artigo (fora do repositório) — feita;
- `PLANO.md` com as obrigações P0–P10 em status `proposta`;
- este roteiro e o esqueleto executável (fase 2) para mostrar o método de trabalho.
Confirmar na reunião:
- o recorte do mestrado dentro do artigo (grafo + sensores + raciocínio, ou só uma parte);
- se GNN entra (ADR-001) ou fica para depois;
- qual impressora, quais sensores existem e quais podem ser adicionados;
- quem aceita as obrigações e os critérios (os autores assinam o PLANO).

## Fase 1 — Fundamentos e revisão (em paralelo com a fase 2)
- grafos e grafos de conhecimento: vocabulário, tipos de nó e relação, consultas, raciocínio por regras;
- clustering de séries temporais multivariadas e detecção de anomalias por regime;
- ler os quatro artigos do João (ordem: GNN/interferência → monitoramento auto-adaptativo → os dois de desmontagem);
- levantar trabalhos sobre grafo de conhecimento em manufatura e sobre monitoramento de impressão 3D por sensores.
Entrega: `docs/revisao.md` com tabela (trabalho, o que representa, de onde vêm os dados, o que recomenda, lacuna).

## Fase 2 — Esqueleto executável com dados sintéticos (feito neste commit)
- contratos, módulos, bateria sintética com gabarito, experimento com proveniência, testes, diagnóstico;
- objetivo: provar P0–P2 e exercitar P3–P8 em ambiente controlado, sabendo da circularidade (PLANO, P3).
Entrega: `resultados/exp01_*.json`, `docs/quadro_validacao.md`.

## Fase 2b — Arquitetura do grupo e artigo de conferência (2026-10-29 → 2026-11-13)
- o código passa a seguir a arquitetura do framework do grupo (ADR-004): pacote `framework/` com KINM, SPCM,
  CFRM, SKL, KEFC, RAL, grafo RDF e suíte SPARQL; obrigações P11–P14; `exp02_framework_fdm`;
- artigo de conferência: rascunho até 06/11, submissão 13/11 (introdução, problem statement, trabalhos relacionados,
  framework preliminar, discussão do caso AM); foco em processo, não em controle de máquina;
- reunião de 02/11: mostrar a execução, o quadro e as dúvidas de arquitetura (nomes, IRIs, política dos códigos novos).
Entrega: `resultados/exp02_*.json`, `docs/modulos/framework.md`, rascunho do artigo (fora do repositório até a submissão).

## Fase 3 — Protocolo de dados reais, antes de coletar
- "dicionário de sensores": canal, unidade, taxa, onde está instalado, o que mede do processo;
- fichas de CAD das peças de teste e as variações de geometria (espessura de parede, ângulo de balanço, ...);
- plano de jobs: quais variações × quais condições de operação; quais violam regras de propósito;
- protocolo de rotulagem do gabarito (como se decide que houve desvio e qual é a causa), com dois rotuladores;
- **fixar os critérios de aceite de P9 aqui**, antes de rodar.
Entrega: `docs/protocolo_coleta.md`, `dados/reais/dicionario_sensores.md`, ADR das escolhas.

## Fase 4 — Instrumentação e coleta
- adaptar `sensores/` ao formato real (log da impressora + sensores externos);
- coletar a bateria; versionar os dados anonimizados (ou os hashes, se forem grandes);
- rodar o diagnóstico sobre cada job assim que for coletado, para pegar problema cedo.
Entrega: `dados/reais/` com gabarito fixado e hash registrado.

## Fase 5 — Regimes com dados reais (P3)
- calibrar nos jobs de calibração, avaliar nos demais; comparar com o baseline de limiar;
- documentar em `docs/modulos/regimes.md` o que não funcionou.

## Fase 6 — Grafo com dados reais (P1, P2)
- revisar o vocabulário do grafo contra as features e operações reais; ADR para cada mudança;
- exportar GraphML para inspeção visual.

## Fase 7 — Raciocínio, atribuição e recomendação (P4–P8)
- confirmar as regras de processo com fonte ou ensaio;
- avaliar atribuição e ajustes com a régua, contra os baselines;
- guia do avaliador externo: 5 explicações lidas por alguém de fora.

## Fase 8 — Laço fechado (opcional)
- aplicar a recomendação na impressora em um job seguinte e medir se o desvio some;
- só se houver tempo e segurança; senão, fica como trabalho futuro com ADR.

## Fase 9 — Consolidação
- `python docs/gerar_quadro.py` com os resultados finais; todas as tabelas da dissertação vêm dos JSON;
- revisar as seções "o que não funcionou" de todos os módulos: viram a discussão.

## Fase 10 — Escrita e defesa
- qualificação conforme o calendário do programa (texto: problema, plano de prova, fases 1–4 feitas);
- artigo com João (o framework) e dissertação (o estudo de caso e a validação);
- defesa: cada afirmação aponta para um arquivo em `resultados/` ou `docs/`.

## Dependências que travam
- Fase 4 depende da fase 3 inteira (sem protocolo, não há gabarito confiável).
- P9 depende de critérios fixados na fase 3; fixados depois, a medida perde valor.
- Fase 7 depende das regras confirmadas; sem fonte, a atribuição é opinião.
