# Módulo `cad_features`

## Propósito
Transformar o design do produto em `ProdutoFeatures`: um conjunto de features geométricas tipadas
(base, parede, furo, nervura, aba) com dimensões e adjacências. É a entrada "design" do grafo.

## Contrato
- Entrada: ficha JSON (`carregar_ficha`) ou construção programática (`ficha_exemplo`, `variar`).
- Saída: `contracts.produto.ProdutoFeatures`, validada (`garantir`) antes de sair do módulo.

## Como funciona hoje
A ficha é escrita à mão ou exportada do CAD. `variar(produto, feature, nova_versao, **dims)` produz a
versão alterada do design (o "Δ de design" da figura-problema) sem tocar na original.

## Limites
- `extrair_de_malha` (STL/STEP → features) não está implementada. Reconhecer "parede fina" numa malha
  exige análise de espessura local; `trimesh` está disponível e é o candidato para a fase 3.
- O vocabulário de tipos é o mínimo para o suporte em L. Peças reais vão pedir mais tipos (ADR quando mudar).

## O que não funcionou e por quê
- Ainda nada foi tentado com CAD real. Registrar aqui cada formato/ferramenta testada e o motivo de descartar.

## Pendências
- Escolher a peça de teste real e escrever a ficha a partir do CAD (fase 3).
- Decidir se a adjacência vem do CAD (contato de faces) ou da ficha manual.
