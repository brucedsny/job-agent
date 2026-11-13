---
name: cardapio
description: Pedido das refeições do hospital para imprimir (PDF bilíngue, pratos em inglês como no cardápio + português), checado contra alergias e dieta. Use para cardápio ou pedido de comida da mãe.
---

# cardapio — pedido de comida para o hospital

## 1. Juntar
- `00_ESTADO_ATUAL`; no `01_FATOS`, o tema de dieta e nutrição (dieta
  prescrita, textura, limite de líquidos, peso, preferências, o que recusou).
- Cardápio do hospital: foto ou PDF mais recente em `60_Cuidados_diarios` ou
  `90_Entrada`. Use o nome exato de cada prato; o que não está no cardápio
  não entra (ou vai como pergunta).
- Datas, horário e telefone do pedido: `03_CONTATOS` ou o cardápio; pergunte
  o que faltar.

## 2. Portão (obrigatório)
`/junta` no modo rápido com o "PORTÃO DE SEGURANÇA" do prompt médico: cada
prato contra alergias, intolerâncias, dieta prescrita (sal, líquidos, açúcar,
textura) e interações com remédios. Portão não abriu → não faça o cardápio;
diga o que falta.

## 3. Preencher `template.html` (desta pasta) numa cópia no scratchpad
- Troque todo `{{…}}`; repita ou apague linhas.
- Metas (uma linha, com fonte) · café da manhã · lanches (hora, lanche,
  bebida) · almoço e jantar por dia · "Please avoid" · perguntas à equipe
  (limite de líquidos, lista de alergias, revisão pela nutricionista).
- `.en`: nome do prato em inglês, como no cardápio. `.pt`: o que é e por quê,
  curto. Perguntas em inglês simples, com tradução, sem nada que só se lê no
  MyChart dela.
- No máximo 2 páginas.

## 4. Checar, gerar, entregar
Como na skill `visita`, seção 4: `fact-checker` →
`node agent/tools/html2pdf.js <in.html> <Cardapio_AAAA-MM-DD.pdf> 0.95` →
`pdfinfo` → `create_file` em `60_Cuidados_diarios` → link e 3 linhas.
