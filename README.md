# Mestrado — grafo de conhecimento para reconfiguração em manufatura aditiva

Repositório do mestrado de Rafael. Ponto de partida: o artigo *Enabling Self-Reconfigurable Manufacturing
Systems through a Knowledge Graph-Based Framework: an Additive Manufacturing case study*. Tema: framework baseado
em **grafo de conhecimento** que integra features de design (CAD), conhecimento de processo e estados operacionais
derivados de **sensores**, para detectar desvios, **atribuir a causa** (inclusive a uma alteração de design) e
**recomendar ajustes** de parâmetros com trade-offs explícitos entre material, tempo e qualidade. O mestrado é o
estudo de caso do artigo: impressão 3D (FDM). A tabela que liga cada frase do abstract a um módulo e a uma
obrigação de prova está no início do `PLANO.md`.

Leia nesta ordem:
1. `ROTEIRO.md` — a sequência do trabalho, da próxima reunião até a defesa.
2. `PLANO.md` — as obrigações de prova (P0–P14), com métrica, baseline e critério de aceite declarados antes do código.
3. `CONTRIBUTING.md` — as oito regras de trabalho, em uma página.
4. `docs/diario.md` — o que mudou e o que ficou pendente, por data.

## Estrutura

```
contracts/            um arquivo por fronteira (produto, processo, sensores, estados, grafo, recomendacao)
cad_features/         design -> ProdutoFeatures          docs/modulos/cad_features.md
processo/             base de conhecimento de processo   docs/modulos/processo.md
sensores/             series temporais do job            docs/modulos/sensores.md
regimes/              clustering -> EstadosOperacionais  docs/modulos/regimes.md
grafo/                construcao do grafo                docs/modulos/grafo.md
raciocinio/           atribuicao, ajustes, trade-offs    docs/modulos/raciocinio.md
avaliacao/            a regua unica (proposto e baselines) docs/modulos/avaliacao.md
framework/            arquitetura do framework do grupo (KINM, SPCM, CFRM, SKL, KEFC, RAL,
                      grafo RDF + suite SPARQL) sobre o caso FDM   docs/modulos/framework.md, ADR-004
dados/sintetico/      gerador + bateria com gabarito fixado
experimentos/         proveniencia.py, obrigacoes.json, exp01_..., exp02_framework_fdm.py
resultados/           JSON versionados (nunca editados a mao)
tests/<modulo>/       pytest com marcador por modulo
diagnostico/          o que cada etapa recebeu, entregou e por onde comecar se falhar
docs/decisoes/        ADRs
docs/diario.md        data, autor, o que mudou, pendencias
docs/gerar_quadro.py  gera docs/quadro_validacao.md e docs/guia_avaliador.md a partir dos JSON
```

## Fluxo dos dados

```
CAD (ficha) ───cad_features──> ProdutoFeatures ──────────┐
base FDM/PLA ──processo──────> ConhecimentoProcesso ─────┼─grafo─> GrafoConhecimento ─raciocinio─> Recomendacao
log + sensores ─sensores─────> SerieMultivariada ─regimes─> EstadosOperacionais ─┘                      │
                                                                                                         v
                                                                        gabarito ─────────────> avaliacao (régua)
```

Na arquitetura do grupo (`framework/`, ADR-004) o mesmo material percorre KINM → **SPCM** (estados operacionais a
partir dos sensores, alinhados ao log de operações) → CFRM → SKL (ontologias OWL + um arquivo de regras) → KEFC
(dez condições de retenção, store de validação por especialista) → grafo unificado em RDF com suíte SPARQL → RAL
(perfil de impressão). Sem sensores, a cadeia se comporta como a do grupo; com sensores, um estado anômalo durante a
deposição de uma feature retém o passo e anexa uma recomendação com proveniência, sem alterar o plano aprovado.

## Rodar

```
python -m venv .venv            (ou: uv venv .venv)
.venv/Scripts/python -m pip install numpy owlready2 rdflib networkx pytest
.venv/Scripts/python -m dados.sintetico.gerador            # gera dados/sintetico/ (deterministico, semente fixa)
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m diagnostico.executar               # diagnostico por etapa (job_009 por padrao)
.venv/Scripts/python -m experimentos.exp01_pipeline_sintetico
.venv/Scripts/python -m framework.main --output runs/demo --jobs job_009 job_010   # framework do grupo + SPCM
.venv/Scripts/python -m experimentos.exp02_framework_fdm
.venv/Scripts/python docs/gerar_quadro.py
```

Artigos de referência e figuras de apresentação ficam fora do repositório (`.gitignore`).
