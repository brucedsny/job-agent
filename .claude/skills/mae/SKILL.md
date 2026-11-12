---
name: mae
description: Perguntas e conversa do dia a dia sobre a mãe (saúde, hospital, seguro, família, documentos) — lê 00_ESTADO_ATUAL e só o tema necessário do 01_FATOS; com "salva" grava os fatos novos nos documentos centrais do Drive.
---

# mae — perguntas e memória do caso

A memória são os documentos centrais na pasta raiz do Drive (id e regra de
busca no CLAUDE.md). Nenhum dado dela entra neste repositório.

## 1. Ler (pare quando bastar)

1. `00_ESTADO_ATUAL` — sempre, primeiro.
2. `01_FATOS` — só o tema da pergunta (ache o título do tema; não leia tudo).
3. Se a pergunta pedir: `02_LINHA_DO_TEMPO` (datas e sequência),
   `03_CONTATOS` (quem é quem, telefones, e-mails), `04_MAPA_DA_PASTA` (onde
   está cada documento).
4. Fonte primária (nota, carta, transcrição) só para o que a ficha não
   resolve, em trechos. Várias fontes ou checar outra IA → subagente
   `fact-checker`.

## 2. Responder

- Exatamente o que foi perguntado, em tópicos coloridos; frases para a equipe
  em inglês curto e simples, com tradução.
- Número, data, remédio, diagnóstico, seguro, dinheiro e família só com fonte
  do `01_FATOS`. Sem fonte → "não confirmado", ou pergunte.
- Divergência → "⚠️ Inconsistência: X diz A; o registro diz B (fonte)".
- Recomendação concreta (comida, remédio, suplemento, exame, atividade,
  visita, documento, contrato) → antes, `/junta` no modo rápido.
- Texto que vai sair → `/escrever`. Folha de visita → `/visita`. Pedido de
  comida → `/cardapio`. Novidades do MyChart, Gmail ou Entrada → `/atualiza`.

## 3. Salvar — quando o usuário disser "salva" ou a conversa trouxer fatos novos

Leia com `mcp__Google_Docs__read_doc` e edite com `mcp__Google_Docs__update_doc`
(`writeControl.requiredRevisionId` = revisão lida; se falhar, releia e refaça).
Use a estrutura e as etiquetas que cada documento já tem.

1. `00_ESTADO_ATUAL` — REESCREVA inteiro, não acrescente: `deleteContentRange`
   de 1 até o `endIndex` do corpo − 1, depois `insertText` no índice 1. Até 2
   páginas; o que deixou de valer sai (o histórico fica na linha do tempo);
   última linha "Atualizado: AAAA-MM-DD HH:MM — fontes".
2. `01_FATOS` — cada fato novo no fim do tema certo (`insertText` no índice em
   que começa o título seguinte): uma linha com fato, data e etiqueta de fonte
   (`[DOC <documento> <data>]`, `[GRAV <arquivo> mm:ss]`, `[EMAIL <remetente>
   <data>]`, `[FAM <quem> <data>]`). Sem confirmação → `[NÃO CONFIRMADO]`.
   Fato errado → corrija no lugar e anote "(corrigido AAAA-MM-DD; antes: …)".
3. `02_LINHA_DO_TEMPO` — evento novo na posição da data:
   `AAAA-MM-DD HH:MM — o que aconteceu — fonte`.
4. `03_CONTATOS` — pessoa ou dado novo: nome, papel, instituição,
   telefone/e-mail, fonte.
5. Responda em uma linha o que foi salvo e onde, sem repetir o conteúdo.
