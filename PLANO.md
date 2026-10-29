# PLANO — obrigações de prova

Projeto: framework baseado em grafo de conhecimento para reconfiguração de processo em manufatura aditiva.
Autores: Rafael (mestrando), João (proposta e coorientação), professor orientador. Leonardo acompanha.

Este documento é a lista do que o trabalho precisa **sustentar**. Cada obrigação tem o que provar, a métrica,
o baseline, o critério de aceite e a ameaça à validade. Os critérios foram declarados em **2026-10-19**, antes
de qualquer execução. O espelho legível por máquina está em `experimentos/obrigacoes.json`; o quadro com o
status de cada obrigação é gerado por `python docs/gerar_quadro.py` em `docs/quadro_validacao.md`.

Convenção de status: `proposta` (escrita, ainda não aceita pelos autores) → `aceita` → `atendida` / `não atendida`.
Hoje todas estão em `proposta`: precisam ser discutidas na próxima reunião.

## Ponto de partida

O artigo *Enabling Self-Reconfigurable Manufacturing Systems through a Knowledge Graph-Based Framework: an
Additive Manufacturing case study* (título e abstract enviados pelo Leonardo em 16/10/2026). O mestrado é a
parte do framework que o abstract chama de estudo de caso: construção do grafo, integração entre domínios e
recomendações de reconfiguração sob variação de geometria e de condições de operação, com os sensores
populando o grafo (a fatia que o João sugeriu na reunião). Cada frase do abstract tem um módulo e uma
obrigação que a sustenta:

| Frase do abstract | Módulo | Obrigação |
|---|---|---|
| representações fragmentadas de design, processo e dados de máquina | o problema (figura-problema, fora do repositório) | — |
| framework com grafo de conhecimento integrando features de CAD, conhecimento de processo e estados de sensores | `grafo/` (fontes: `cad_features/`, `processo/`, `regimes/`) | P1 |
| relações explícitas entre produto, parâmetros, comportamento da máquina e objetivos; rastreabilidade | `contracts/grafo.py` (vocabulário) + proveniência | P2, P8 |
| séries multivariadas de sensores agrupadas em padrões, transições e anomalias, mapeadas ao grafo | `sensores/`, `regimes/` | P3 |
| raciocínio orientado por conhecimento → ajustes viáveis de parâmetros | `raciocinio/` | P4, P5, P6 |
| trade-offs entre consumo de material, tempo e qualidade | arestas `impacta` + `raciocinio.tradeoffs` | P7 |
| estudo de caso em manufatura aditiva sob variação geométrica e operacional | `dados/sintetico/` agora, `dados/reais/` depois | P9 |
| framework independente de domínio | contratos sem termos de FDM no núcleo | P10 |
| decisões explicáveis, adaptativas, auto-reconfiguração | `Recomendacao.explicacao` + laço de volta à máquina (fase 8) | P8 |

## Tese em uma frase

Representar design (features de CAD), conhecimento de processo e estados operacionais derivados de sensores
em **um único grafo de conhecimento com relações explícitas** permite (a) detectar desvios do processo,
(b) atribuir o desvio a uma causa rastreável, inclusive uma alteração de design, e (c) recomendar ajustes
de parâmetros viáveis com trade-offs explícitos entre material, tempo e qualidade, de forma **explicável**.

## Obrigações

### P0 — O pipeline fecha de ponta a ponta sobre os contratos
- **O que provar**: toda fronteira (produto → processo → série → estados → grafo → recomendação) é cruzada por
  um objeto que passa em `validar()`; o experimento roda a bateria inteira sem violação.
- **Métrica**: número de violações de contrato na bateria (`proposto.contratos_violados`).
- **Baseline**: não se aplica (obrigação estrutural).
- **Aceite**: 0 violações.
- **Ameaça à validade**: contratos frouxos passam sempre. Mitigação: `tests/contracts/` exige que casos
  inválidos sejam rejeitados.

### P1 — O grafo integra as três fontes
- **O que provar**: cada feature do produto, cada parâmetro usado no job, cada operação e cada segmento de estado
  aparece como nó do grafo, ligado pelas relações do vocabulário (`contracts/grafo.py`).
- **Métrica**: cobertura (% de entidades esperadas presentes) — `proposto.grafo_cobertura_pct`.
- **Baseline**: não se aplica.
- **Aceite**: 100 %.
- **Ameaça**: vocabulário estreito demais para o caso real (features que a ficha não descreve).
  Mitigação: P9 repete a medida com dados reais; ADR quando o vocabulário mudar.

### P2 — Toda aresta tem proveniência
- **O que provar**: cada relação do grafo diz de onde veio (ficha de CAD, regra de processo, meta do job,
  método de regimes). É o que torna a decisão rastreável.
- **Métrica**: % de arestas com proveniência não vazia — `proposto.grafo_proveniencia_pct`.
- **Baseline**: não se aplica.
- **Aceite**: 100 %.
- **Ameaça**: proveniência genérica satisfaz a métrica sem informar. Mitigação: o guia do avaliador
  pede inspeção manual de uma amostra de caminhos de explicação.

### P3 — Clustering de sensores identifica anomalias melhor que um limiar simples
- **O que provar**: as janelas anômalas detectadas pelo método proposto (k-means sobre janelas multivariadas,
  com limiar de distância) coincidem com as do gabarito mais do que um limiar sobre um único canal.
- **Métrica**: F1 das janelas anômalas (micro, sobre os jobs de avaliação) — `proposto.anomalia_f1`;
  pureza dos estados como métrica secundária.
- **Baseline**: `baseline_limiar.anomalia_f1` (limiar fixo sobre o desvio da vibração, calibrado nos jobs de calibração
  como mediana + 3·MAD). Nota datada de 2026-10-19: a primeira execução usou média + 3 desvios, que as anomalias
  da calibração inflam (F1 0,32); o baseline foi trocado pelo robusto **antes** de qualquer uso do número, sem mexer
  no critério. Registro em `docs/modulos/regimes.md` e no diário.
- **Aceite**: F1 ≥ baseline + 0,10 **e** F1 ≥ 0,70 na bateria sintética.
- **Ameaça (grave)**: circularidade. O gerador sintético injeta a anomalia como pico de vibração e ondulação de
  corrente, exatamente o que ambos os métodos procuram. O resultado sintético prova que o pipeline funciona,
  **não** que o método funciona na impressora. Mitigação: jobs de calibração separados dos de avaliação;
  P9 refaz tudo com dados reais e critérios fixados antes da coleta.

### P4 — O raciocínio sobre o grafo atribui a causa certa
- **O que provar**: quando há anomalia, o caminho job → estado → operação → feature → regra → parâmetro aponta a
  feature de design que o gabarito registra como causa (ou "nenhuma", quando o desvio não tem causa de design).
- **Métrica**: acurácia da causa sobre os jobs de avaliação — `proposto.acuracia_causa`.
- **Baselines**: `baseline_geometrico` (sempre a parede mais fina) e `baseline_temporal` (a feature impressa
  no momento da anomalia, sem regras).
- **Aceite**: acurácia ≥ baseline_geometrico + 0,15 **e** ≥ 0,80.
- **Ameaça**: causalidade sintética simples demais (regra violada ⇒ anomalia com probabilidade alta).
  O baseline temporal tende a empatar na feature e perder nos casos sem causa; isso é esperado e deve ser discutido.

### P5 — Os ajustes recomendados são viáveis
- **O que provar**: todo ajuste proposto respeita a faixa do parâmetro na base de processo.
- **Métrica**: taxa de recomendações viáveis — `proposto.taxa_viavel`.
- **Baseline**: `baseline_geometrico.taxa_viavel` (voltar aos padrões é trivialmente viável).
- **Aceite**: 100 %.
- **Ameaça**: viabilidade na base ≠ viabilidade na máquina. Mitigação: P9.

### P6 — Os ajustes resolvem as regras violadas
- **O que provar**: aplicando os ajustes aos parâmetros do job, nenhuma regra aplicável fica violada.
- **Métrica**: taxa de jobs com violação no gabarito em que as violações zeram após o ajuste — `proposto.taxa_resolve`,
  calculada pela mesma função para todos os métodos.
- **Baseline**: `baseline_geometrico.taxa_resolve` (voltar aos padrões resolve só por acaso).
- **Aceite**: ≥ 0,90 e ≥ baseline + 0,20.
- **Ameaça**: resolver a regra não garante resolver o desvio físico. É uma medida de consistência lógica.

### P7 — Toda recomendação informa os trade-offs pela mesma régua
- **O que provar**: toda recomendação traz Δtempo, Δmaterial e Δqualidade calculados pelo mesmo modelo de custo
  (arestas `impacta` do grafo), para o proposto e para os baselines.
- **Métrica**: taxa de recomendações com os três trade-offs informados — `proposto.taxa_tradeoffs`.
- **Baseline**: idem para baselines.
- **Aceite**: 100 %.
- **Ameaça**: o modelo de custo é declarado, não medido. Mitigação: P9 compara com tempo e massa reais.

### P8 — Toda causa atribuída vem com explicação completa
- **O que provar**: quando o método atribui uma causa, a explicação é um caminho de arestas do grafo, cada passo
  com proveniência.
- **Métrica**: taxa de explicações completas — `proposto.taxa_explicacao_completa`.
- **Baseline**: baselines têm explicação heurística de um passo; a comparação é qualitativa.
- **Aceite**: 100 %.
- **Ameaça**: completa ≠ compreensível. Mitigação: o guia do avaliador pede a leitura de 5 explicações por um
  avaliador externo, com nota de clareza.

### P9 — P1 a P8 se sustentam com dados reais (estudo de caso)
- **O que provar**: repetir P1–P8 sobre a bateria coletada na impressora do laboratório, com variação de geometria
  e de condições de operação.
- **Métrica / baseline**: os mesmos.
- **Aceite**: **a fixar antes da primeira coleta** (ROTEIRO, fase 3). Fica registrado que os valores sintéticos
  não servem de limiar para o real.
- **Ameaça**: poucos jobs reais; gabarito por inspeção visual. Mitigação: protocolo de rotulagem escrito antes
  da coleta, dois rotuladores.

### P10 — O núcleo é independente de domínio (desejável, não obrigatório)
- **O que provar**: uma segunda base de processo (ex.: usinagem) carrega e gera grafo sem alterar código do núcleo.
- **Métrica**: arquivos de código alterados fora de `dados/` e das bases — `exp03.arquivos_alterados`.
- **Aceite**: 0.
- **Ameaça**: um só exemplo não prova generalidade. Sustenta a afirmação do artigo, não a dissertação;
  pode virar trabalho futuro com uma ADR.

### P11 — Estados operacionais entram no SKL como fatos com proveniência (declarada em 2026-10-29)
- **O que provar**: cada estado produzido pelo módulo de sensores é um indivíduo da ontologia de estados com
  método, configuração, janelas e série de origem, e todo estado anômalo resolve por SPARQL a pelo menos uma
  instância de operação do log; quando essa operação deposita uma feature, a ligação chega à feature.
- **Métrica**: `reference.estados_anomalos_ligados_pct` (estados anômalos ligados a uma instância de operação,
  contados por SPARQL sobre o grafo exportado); `estados_anomalos_com_feature_pct` é informativo.
- **Baseline**: não se aplica (estrutural).
- **Aceite**: 100 % nos jobs com log de operações; sem log, o pipeline retém tudo como `missing_knowledge`.
- **Ameaça**: a ligação depende da sobreposição temporal com o log; log errado liga estado à feature errada.
  Mitigação: P9 exige log real e dois rotuladores.

### P12 — O gate retém passos com evidência anômala e só eles (declarada em 2026-10-29)
- **O que provar**: com estados de sensores, o KEFC retém com `anomalous_operational_state` exatamente os
  passos das features cuja deposição teve estado anômalo; na ablação `sensor_states` os mesmos passos são
  aprovados e nenhuma outra decisão muda.
- **Métrica**: `reference.acuracia_evidencia` (por job, o conjunto de features retidas por evidência é igual ao
  conjunto de features cuja deposição se sobrepõe a uma anomalia injetada do gabarito; a concordância com a
  `causa_feature` do gabarito é reportada à parte); `ablation_sensor_states.passos_retidos_por_evidencia` deve ser 0.
- **Baseline**: `ablation_sensor_states` (pipeline sem sensores, como o do grupo).
- **Aceite**: acurácia ≥ 0,80 e ablação com zero retenções por evidência.
- **Ameaça**: circularidade da bateria sintética (P3). O que se prova aqui é o mecanismo do gate, não a
  qualidade da detecção.

### P13 — Toda recomendação de ajuste tem proveniência e não altera o plano aprovado (declarada em 2026-10-29)
- **O que provar**: cada ajuste recomendado nasce de uma regra do arquivo de regras condicionada a uma classe de
  evidência, cita a regra, as ontologias e os estados que o motivaram, e os registros de parâmetro aprovados do
  passo continuam idênticos aos da ablação.
- **Métrica**: `reference.ajustes_com_proveniencia_pct`; `reference.registros_parametro_iguais_a_ablacao`.
- **Baseline**: não se aplica.
- **Aceite**: 100 % e verdadeiro.
- **Ameaça**: as regras de recuperação são escritas por nós, sem ensaio (ameaça transversal 3).

### P14 — Sem conhecimento, nenhum plano (declarada em 2026-10-29)
- **O que provar**: sem arquivo de regras, sem ontologia ou com o raciocinador indisponível, o pipeline falha
  alto e não grava plano nem perfil; com um log de operações ausente, todo passo vai a `missing_knowledge`.
- **Métrica**: testes de injeção de falha em `tests/framework/` (`testes_falha_alta_passando`).
- **Aceite**: todos passam.
- **Ameaça**: um teste que só verifica a exceção não prova que nada foi gravado; os testes verificam a pasta.

## Ameaças transversais

1. **Dados sintéticos ↔ método**: já dito em P3. Toda tabela com dados sintéticos leva o rótulo "sintético".
2. **Autor avaliando o próprio método**: régua única (`avaliacao/`), gabarito fixado antes, e o JSON registra
   se a execução foi a primeira sobre aqueles dados.
3. **Regras de processo escritas por nós**: R1–R5 da base FDM/PLA são práticas comuns, com `fonte` marcada
   "a confirmar". Antes de P9, cada regra precisa de fonte ou ensaio.
4. **Escopo**: GNN não aparece no abstract do artigo nem neste plano. Se entrar, entra por ADR com obrigação própria.
