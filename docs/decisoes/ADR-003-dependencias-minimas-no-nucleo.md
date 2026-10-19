# ADR-003 — Dependências mínimas no núcleo (numpy; k-means e grafo próprios)

- **Status**: proposta (2026-10-19).
- **Contexto**: o Python da máquina é gerenciado (PEP 668) e não aceita `pip install` global; scikit-learn,
  pandas e PyYAML não estavam disponíveis; networkx e trimesh estavam. O projeto precisa rodar em qualquer
  máquina dos autores e na banca.
- **Opções**:
  1. Depender de scikit-learn (clustering), networkx (grafo), pandas (séries).
  2. Núcleo só com numpy: k-means próprio (~40 linhas, semente fixa), grafo como dicionários tipados com
     validação de vocabulário, séries como arrays. Bibliotecas externas só em adaptadores opcionais.
- **Decisão**: opção 2 para o núcleo, com `.venv` do projeto (`numpy`, `pytest`). Exportação GraphML é escrita
  à mão para inspeção em ferramentas externas.
- **Consequências**: menos atrito de instalação e proveniência mais simples (uma versão de numpy a registrar);
  se o clustering real pedir algo além de k-means (DBSCAN, HDBSCAN, misturas), entra por adaptador e por ADR,
  comparado ao k-means pela mesma régua.
