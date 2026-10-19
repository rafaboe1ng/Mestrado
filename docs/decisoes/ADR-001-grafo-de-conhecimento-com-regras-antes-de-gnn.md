# ADR-001 — Grafo de conhecimento com regras explícitas antes de GNN

- **Status**: proposta (2026-10-19). Aguarda aceite de Rafael e João.
- **Contexto**: a reunião de 16/10 falou em "grafos + machine learning" e o artigo do João sobre matriz de
  interferência usa GNN. O abstract do artigo-alvo ("Enabling Self-Reconfigurable Manufacturing Systems through a
  Knowledge Graph-Based Framework") fala em grafo de conhecimento, relações semânticas explícitas, clustering de
  séries de sensores e raciocínio orientado por conhecimento; não menciona GNN.
- **Opções**:
  1. Grafo de conhecimento com vocabulário fechado e regras explícitas (feature → parâmetro), raciocínio por
     travessia e verificação de restrições. Explicável por construção; depende de regras escritas.
  2. GNN treinada para prever parâmetros ou desvios a partir do grafo de design. Aprende relações não escritas;
     precisa de muitos jobs rotulados e explica mal.
  3. Híbrido: 1 agora, 2 como camada opcional quando houver dados reais suficientes.
- **Decisão**: opção 3, começando pela 1. O núcleo (contratos, grafo, raciocínio, régua) não assume GNN.
  Se a GNN entrar, entra com obrigação de prova própria no PLANO e com o mesmo baseline.
- **Consequências**: as regras R1–R5 viram o gargalo de validade (precisam de fonte ou ensaio antes de P9);
  a explicação é um caminho de arestas, o que atende P8 sem pós-processamento; o trabalho fica alinhado ao
  abstract do artigo e a pergunta "GNN entra?" fica explícita para a reunião.
