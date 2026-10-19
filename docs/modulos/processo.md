# Módulo `processo`

## Propósito
Guardar o conhecimento de processo de forma explícita: parâmetros com faixa, regras
"feature com tal geometria → parâmetro restrito a tal faixa", impactos de parâmetro sobre objetivos
(material, tempo, qualidade). É a entrada "processo" do grafo e a fonte das arestas `requer` e `impacta`.

## Contrato
- Saída: `contracts.processo.ConhecimentoProcesso` (validada).
- Consultas: `regras_aplicaveis(base, produto)` e `violacoes(base, produto, parametros_usados)`.

## Como funciona hoje
`base_fdm_pla()` traz 6 parâmetros, 5 regras (R1–R5) e 5 impactos. Toda regra tem `justificativa` e `fonte`;
hoje a fonte é "prática comum FDM; a confirmar com ensaio ou fonte antes de P9".

## Limites
- As regras são escritas por nós. Enquanto não tiverem fonte ou ensaio, a atribuição de causa (P4) é
  consistência lógica, não evidência física (PLANO, ameaça transversal 3).
- Os impactos são modelos declarados (`tempo ~ 1/velocidade`), não medidos.

## O que não funcionou e por quê
- Ainda não há registro. Anotar aqui cada regra que for derrubada por ensaio e por quê.

## Pendências
- Levantar fontes para R1–R5 (manuais de fatiador, literatura de FDM) ou planejar o ensaio que as confirma.
- Segunda base (ex.: usinagem) para P10, só se houver tempo.
