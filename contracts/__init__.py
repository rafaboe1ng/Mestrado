"""Contratos entre modulos.

Cada fronteira do pipeline e um tipo de dado definido aqui. Um modulo so le o
anterior por esse tipo, e todo objeto que cruza a fronteira passa por ``validar()``.

Fronteiras:
- produto.py       cad_features -> grafo
- processo.py      processo -> grafo, raciocinio
- sensores.py      sensores -> regimes, grafo
- estados.py       regimes -> grafo, avaliacao
- grafo.py         grafo -> raciocinio
- recomendacao.py  raciocinio -> avaliacao
"""
