# Como trabalhamos neste repositório

Regras em uma página. A ideia que une todas: **cada afirmação do texto final aponta para um arquivo que a prova.**

## 1. Prova antes do código
`PLANO.md` lista as obrigações de prova (P0, P1, ...). Cada uma diz o que provar, a métrica, o baseline,
o critério de aceite e a ameaça à validade. O critério é declarado **antes** de rodar; o espelho legível
por máquina fica em `experimentos/obrigacoes.json`. Nunca se ajusta o critério depois de ver o número.
Se um critério precisar mudar, escreve-se uma ADR explicando por quê, e a mudança fica datada.

## 2. Contratos, não módulos soltos
Toda fronteira entre módulos é um tipo em `contracts/`, com `validar()`. Um módulo só lê o anterior por
esse tipo. Nenhum módulo importa o interior de outro módulo; importa `contracts/` e a API pública (`__init__.py`).

## 3. Registro de decisão (ADR)
Escolheu entre alternativas, escreve `docs/decisoes/ADR-nnn-titulo.md`: contexto, opções, decisão,
consequências. Status `proposta` até os dois autores aceitarem; depois `aceita`, `substituída` ou `rejeitada`.

## 4. Um documento por módulo
`docs/modulos/<modulo>.md` com: propósito, contrato de entrada e saída, como funciona hoje, limites,
e a seção obrigatória **"O que não funcionou e por quê"**. Essa seção é a que mais rende na banca.

## 5. Experimentos com proveniência
Todo número vem de um script `experimentos/expNN_*.py` que grava um JSON em `resultados/` via
`experimentos/proveniencia.py`: comando, hash do commit, se havia alteração não commitada, versões,
hash dos dados. Regra: **commitar o código, rodar, commitar o resultado.** Número digitado à mão não existe.

## 6. Verificação em camadas
- testes por módulo em `tests/<modulo>/`, com o marcador do módulo e fixtures pequenas;
- `diagnostico/`: roda sobre os dados (sintéticos hoje, reais depois) e diz o que cada etapa recebeu,
  entregou e por onde começar se falhar;
- bateria de casos com **gabarito fixado antes de rodar** (`dados/sintetico/gabarito.json`, depois a real);
  só a primeira execução sobre um gabarito vale como medida fora da amostra (o JSON do resultado registra isso).

## 7. Baseline sempre, pela mesma régua
Nenhum método calcula o próprio valor. `avaliacao.regua()` avalia o proposto e os baselines com o mesmo código.
Sem baseline, o número bom não diz nada.

## 8. Documentos gerados por script
`docs/quadro_validacao.md` e `docs/guia_avaliador.md` são gerados por `docs/gerar_quadro.py` a partir dos JSON.
Não se editam à mão. O diário (`docs/diario.md`) é escrito à mão, por data e autor: o que mudou e o que ficou pendente.

## Comandos do dia a dia
```
.venv/Scripts/python -m dados.sintetico.gerador        # (re)gera a bateria sintetica; deterministica
.venv/Scripts/python -m pytest -q                      # todos os testes
.venv/Scripts/python -m pytest -q -m regimes           # so um modulo
.venv/Scripts/python -m diagnostico.executar           # diagnostico por etapa sobre um job
.venv/Scripts/python -m experimentos.exp01_pipeline_sintetico
.venv/Scripts/python docs/gerar_quadro.py              # regenera quadro de validacao e guia do avaliador
```
