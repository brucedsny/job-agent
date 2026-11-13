---
name: visita
description: Folha de visita ao hospital para imprimir (PDF bilíngue, inglês em negrito para ler em voz alta + português) com perguntas e pedidos à equipe. Use antes de visitar a mãe.
---

# visita — folha para levar ao hospital

## 1. Juntar
- `00_ESTADO_ATUAL`; no `01_FATOS`, os temas de hoje (remédios, exames, alta,
  seguro, cuidados); no `03_CONTATOS`, a equipe atual e o telefone do usuário.
- `last_sync` (descrição de `80_Atualizacoes`) com mais de 12 h → rode
  `/atualiza` antes ou pergunte.
- O que ela pediu e o que levar: listas em `60_Cuidados_diarios`; pergunte o
  que faltar.

## 2. Portão
Cada pedido (comida, objeto, roupa, banho, atividade, exame, remédio) passa
pela `/junta` no modo rápido. Portão não abriu → fica fora da folha.

## 3. Preencher `template.html` (desta pasta) numa cópia no scratchpad
- Troque todo `{{…}}`; repita ou apague itens e seções. Até 7 itens por pessoa.
- `.en`: frase em inglês simples (nível A2–B1), educada ("Could…?"), uma
  ideia por frase. `.pt`: tradução curta.
- `.en` nunca cita o que só se lê no MyChart dela: vira pergunta aberta, e a
  equipe conta.
- Número, data e remédio só do `01_FATOS`, com fonte. Tom de pedido: nada de
  cobrança, ameaça ou lei (salvo pedido do usuário), nem de pedir que alterem
  documentação.
- No máximo 2 páginas. Papel para ENTREGAR à equipe: folha à parte, 1 página,
  só inglês simples, sem números do prontuário; a bilíngue fica com o usuário.

## 4. Checar, gerar, entregar
1. Subagente `fact-checker` sobre o texto da folha; corrija.
2. `node agent/tools/html2pdf.js <folha.html> <Visita_AAAA-MM-DD.pdf> 0.95`;
   `pdfinfo` → até 2 páginas (senão, corte texto ou reduza a escala).
3. `create_file` em `60_Cuidados_diarios`: `base64Content` =
   `sha256:<sha256sum do PDF>:<caminho absoluto>`, `contentMimeType`
   `application/pdf`, `disableConversionToGoogleType: true`.
4. Responda com o link e as 3 coisas mais importantes de hoje. O usuário
   imprime; nada é enviado.
