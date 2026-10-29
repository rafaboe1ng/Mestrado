# ADR-004 — Alinhar o código à arquitetura do framework do grupo (KINM, CFRM, SKL, KEFC, RAL)

- **Status**: proposta (2026-10-29). Aguarda aceite de Rafael, João e orientador.
- **Contexto**: o artigo de conferência (submissão 13/11) e o mestrado devem ser a continuação do framework do
  JIII (Prioli et al.): KINM normaliza entradas com proveniência; CFRM mapeia entidades em classes e indivíduos
  OWL; SKL guarda ontologias, regras SWRL num único arquivo e o raciocinador; KEFC é dono de todo o gating, com
  códigos de razão fechados e um store persistente de validação por especialista; RAL só recebe passos aprovados
  e recusa o que não consegue serializar; o grafo unificado é exportado em RDF e verificado por uma suíte SPARQL
  fixa. O manuscrito declara que nenhum estado da máquina entra no pipeline. O nosso repositório tinha a mesma
  intenção com nomes e formatos próprios (ADR-001 a ADR-003). Nesta máquina não há Java, logo o Pellet não roda.
- **Opções**:
  1. Portar os nossos módulos para dentro da árvore do João (um `sensor_states.py` e ontologias novas lá).
     Fiel, mas mexe no repositório que está em revisão e exige Java para qualquer teste.
  2. Manter o nosso repositório como está e só escrever um conversor para os formatos dele.
     Barato, mas não exercita o gate nem o store, que são o centro do argumento.
  3. Criar aqui um pacote `framework/` que reproduz a arquitetura e as convenções externas dele (nomes dos
     componentes, formato de regra, formato de passo e de registro de parâmetro, códigos de razão, store,
     arquivos de saída de uma execução, suíte SPARQL), usando os módulos em português como biblioteca
     (`cad_features`, `sensores`, `regimes`, `avaliacao`) e acrescentando o módulo novo de caracterização do
     processo por sensores (SPCM) que escreve estados operacionais no SKL.
- **Decisão**: opção 3. Vocabulário externo em inglês, como o do grupo; núcleo em português permanece.
  Raciocínio: o mesmo arquivo de regras é executado por um motor Python de encadeamento direto sobre os fatos
  asseridos (subconjunto SWRL que o parser dele aceita: `Class(?f)` e `prop(?f, Individuo)`), com
  `reasoning_status` dizendo qual motor rodou; quando houver Java, o mesmo repositório chama o Pellet. Sem
  ontologias ou sem arquivo de regras, falha alto (nenhum plano é emitido), como o `SKLReasonerError` dele.
  Condições numéricas das regras R1–R5 viram classes qualificadoras (`ThinWall`, `SteepOverhang`, `SmallHole`,
  `ThinRib`) asseridas pelo CFRM com identificador de regra de qualificação, porque o formato de regra não tem
  builtins numéricos; classes folha são disjuntas (`StandardWall`/`ThinWall`) para que dois conjuntos de
  parâmetros nunca casem na mesma feature, como na resolução S5 do manuscrito.
  Evidência de sensores entra como fato asserido: um estado anômalo que se sobrepõe à operação de uma feature
  assere `FeatureWithAnomalousDeposition(?f)`; regras condicionadas a essa classe produzem
  `recommendsParameterSet`; o KEFC retém o passo com o código novo `anomalous_operational_state` e anexa a
  recomendação com proveniência sob `parameter_adjustment_suggested`, sem sobrescrever os registros de parâmetro
  aprovados. O especialista fica no laço: nenhum ajuste é aplicado automaticamente.
- **Consequências**: dois vocabulários coexistem (contratos em português, framework em inglês) e a tradução
  fica num único lugar por tipo; o número de condições de retenção passa de 8 para 10 e cada condição nova
  precisa de injeção de falha; os resultados do framework são rotulados com o motor de raciocínio usado; a
  suíte SPARQL e os contadores de nós mudam em relação à referência do grupo, então as comparações com os
  números do JIII são por configuração própria, nunca por reuso dos dele. As obrigações P11 a P14 do PLANO
  cobrem o que esta decisão promete.
