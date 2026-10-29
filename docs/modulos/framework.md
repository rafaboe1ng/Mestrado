# Pacote `framework`

## Propósito
Reproduzir a arquitetura do framework do grupo (KINM → CFRM → SKL → KEFC → RAL, grafo unificado exportado em
RDF e verificado por SPARQL) sobre o caso FDM, com o módulo que o mestrado acrescenta, o **SPCM** (Sensor-driven
Process Characterisation Module), encaixado entre a normalização de entradas e o mapeamento semântico. É o código
do artigo de conferência e a base do mestrado (ADR-004). Os módulos em português (`cad_features`, `sensores`,
`regimes`) são usados como biblioteca; o vocabulário externo (códigos de razão, status, nomes de arquivo, termos
RDF) é o do grupo, em inglês.

## Componentes e contratos
| Componente | Arquivo | Entrada | Saída |
|---|---|---|---|
| KINM | `framework/kinm.py` | `ProdutoFeatures`, `SerieMultivariada` | `FeatureRecord` (id 1..N, tipo, dimensões, fonte, confiança), `OperationLogEntry`, `SensorSeriesRecord` |
| SPCM | `framework/spcm.py` | série + log de operações | `OperationalStateRecord` (rótulo, janelas, score, método, configuração, sobreposições com o log) |
| CFRM | `framework/cfrm.py` | registros + repositório SKL | `ReconciledFeature` (classe OWL, classe folha por qualificador Q1–Q4, confiança combinada) e indivíduos asseridos |
| SKL | `framework/skl/` | cinco ontologias geradas por `build_ontologies.py`, um arquivo de regras | repositório raciocinado; `get_operations`, `get_parameter_sets`, `get_recommended_sets` com `rule_ids` e `ontology_sources` |
| KEFC | `framework/kefc.py` | features reconciliadas + repositório | plano: passos com registros de parâmetro `{value, unit, source, rule_id, ontology_sources, input_facts}`, exceções, status |
| Grafo/RDF | `framework/kg.py`, `framework/manufacturing.ttl` | plano, features, estados, log | NetworkX + Turtle; cada nó aponta para o indivíduo da ontologia de caso |
| SPARQL | `framework/sparql_suite.py` | grafo RDF + contexto da execução | 23 consultas fixas; asserções abortam antes do RAL |
| RAL | `framework/ral.py` | passos aprovados | `print_profile.json/.ini`; recusa com `serialisation_input_missing` |
| Runner | `framework/main.py` | `RunConfig` | uma pasta por configuração, uma subpasta por job, `run_summary.json` |

Store de validação por especialista: `framework/expert_validation.py` (get-or-create por `(feature, operação, código)`,
JSON persistente, `APPROVABLE_WITHOUT_NEW_DATA`).

## Como funciona hoje
1. O KINM renumera as features (1..N), traduz tipos e dimensões para o vocabulário em inglês e lê o log de
   operações da série (`OperacaoJob`).
2. O SPCM aplica o modelo de regimes (k-means ajustado na calibração, ou o baseline de limiar robusto) e agrupa as
   janelas em estados contíguos; cada estado registra as entradas do log que sobrepõe por pelo menos
   `min_overlap_s`. A evidência de uma feature é o conjunto dos estados anômalos sobrepostos à operação que a deposita.
3. O CFRM assere `feature_<n>` com a classe e a classe folha (`ThinWall` etc., decididas pelos qualificadores Q1–Q4
   porque o formato de regra não tem builtins numéricos), `madeOfMaterial`, `printedOn`; assere as instâncias de
   operação do log e os estados como indivíduos com proveniência; marca `FeatureWithAnomalousDeposition` quando há
   evidência.
4. O SKL executa o único arquivo de regras. Sem Java, roda o motor de encadeamento direto em Python sobre os mesmos
   fatos; o `reasoning_report` declara `python_forward_chaining`. Cada valor inferido é atribuído à regra pelo casamento
   do consequente e do antecedente (`rule_engine.attribute`), que é o mesmo mecanismo usado para o Pellet.
5. O KEFC monta um passo por (feature, operação), roda as dez condições de retenção na ordem fixa e decide o status
   pelo store. Os dois códigos novos: `anomalous_operational_state` (aprovável sem dados novos, como o achado crítico da
   simulação no framework do grupo) e `parameter_adjustment_suggested` (não aprovável sem dados novos). A recomendação
   fica anexada ao passo com regra, ontologias e estados; os registros aprovados não mudam.
6. O grafo recebe nós de estado e de operação executada com as arestas `OBSERVED_DURING`, `EVIDENCES`, `EXECUTED_AS`;
   tipos de nó e relações desconhecidos levantam erro na exportação em vez de sumir.
7. A suíte SPARQL verifica proveniência (seis registros por passo, cada um com regra e ontologia), a ligação dos
   estados anômalos às operações, as recomendações com evidência, a inércia da ablação e o cruzamento entre o
   conjunto de parâmetros do passo e o que a ontologia de caso inferiu (Q11).
8. O RAL serializa só os passos aprovados; cada valor do perfil cita a regra.

## Limites
- **Pellet não foi executado nesta máquina** (sem Java). O caminho `reasoner="pellet"` registra as regras como
  `Imp` no owlready2 e chama `sync_reasoner_pellet`; está escrito, mas não testado. O artigo declara o motor usado.
- O formato de regra é o subconjunto que o parser do grupo aceita (`Class(?f)` e `prop(?f, Indivíduo)`, uma
  variável). Condições numéricas são classes qualificadoras asseridas pelo CFRM, com identificador próprio (Q1–Q4).
- Os conjuntos de parâmetros (`PARAMETER_SETS`) e as regras de recuperação são prática comum FDM escrita por nós,
  sem ensaio (PLANO, ameaça transversal 3). Os valores de recuperação são placeholders a confirmar.
- O alinhamento estado ↔ feature depende do log de operações; sem log, tudo vai a `missing_knowledge` (P14).
- Os números de nós, passos e requests não são comparáveis aos do caso de usinagem do grupo (22 entidades, 32
  passos); cada configuração tem a sua referência.

## O que não funcionou e por quê
- **2026-10-29, primeira montagem.** A primeira versão dos nomes de arquivo das ontologias
  (`additive_process.owl`) não casava com o último segmento do IRI (`additive-process`), e o owlready2 só resolve
  importações pelo nome do IRI; os arquivos passaram a ser nomeados pelo IRI e carregados por `fileobj` na
  ordem de dependência.
- Em `job_009` o SPCM produz dois estados anômalos e só um se liga a uma feature: o outro cai na fase de
  aquecimento (operação sem feature). A métrica de P11 conta ligação à operação, não à feature; a ligação à
  feature é reportada à parte (`estados_anomalos_com_feature_pct`). O falso positivo da janela de aquecimento
  já está registrado em `docs/modulos/regimes.md`.
- A ablação não pode usar a mesma métrica de acurácia que a referência: sem sensores ela "acerta" exatamente os
  jobs sem anomalia (0,5). Por isso P12 fixa a ablação por `passos_retidos_por_evidencia = 0`, não por acurácia.

## Como rodar
```
.venv/Scripts/python -m framework.skl.build_ontologies                    # regenera framework/skl/knowledge/*.owl
.venv/Scripts/python -m framework.main --output runs/demo --jobs job_009 job_010 --reasoner python
.venv/Scripts/python -m framework.main --output runs/demo_abl --jobs job_009 --no-sensor-evidence
.venv/Scripts/python -m pytest tests/framework -q
.venv/Scripts/python -m experimentos.exp02_framework_fdm && .venv/Scripts/python docs/gerar_quadro.py
```

## Pendências
- Rodar o Pellet numa máquina com Java e comparar as inferências com o motor Python (mesmo arquivo de regras).
- Nome definitivo do módulo e do IRI das ontologias com o grupo (`operational-states` sob `onto.brep.org`).
- Decidir com o grupo se `parameter_adjustment_suggested` deve virar `knowledge_update_suggested` direto.
- Regras de recuperação com fonte ou ensaio antes de qualquer uso fora do sintético.
