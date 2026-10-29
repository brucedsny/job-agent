---
name: health-sync
description: Rotina de acompanhamento de saúde de um familiar, 2x por dia — baixa só o que é novo do MyChart, do Gmail (hospital, seguro, casa de reabilitação) e da pasta de entrada do Drive (áudios, fotos, PDFs), checa respostas de outras IAs, atualiza a ficha de fatos e escreve uma atualização curta no Drive. Use quando o trigger agendado disparar ou o usuário disser "atualiza".
---

# health-sync — atualização de manhã e de noite

A configuração (IDs das pastas e da ficha, variáveis de login, consulta do
Gmail, agenda) vem no prompt do trigger ou da conversa; sem ela, ache as pastas
pelo título. Nenhum dado de paciente entra neste repositório. O scratchpad
some quando o contêiner reinicia: a memória da rotina é o Drive.

Princípio: **só o que é novo**. Nada novo → grave o marcador e responda em uma
linha, sem documento e sem notificação.

## Passo 0 — Marcador

- `since` = valor `last_sync=<RFC3339>` na descrição da pasta de atualizações
  (`get_file_metadata`). Sem marcador: últimas 24 h.
- Anote `now` (UTC) para gravar no fim.

## Passo 1 — Gmail (sempre; é barato)

- `search_threads` com a consulta da config + `after:<since em epoch>`.
  Ignore "Verification Code". Leia só os threads novos (texto puro).
- Classifique: portal/hospital · seguro · reabilitação · contas · outro.
- Aviso do portal (resultado, nota, documento, mensagem, consulta) → Passo 2.

## Passo 2 — MyChart

Entre quando houver aviso no Passo 1, quando o paciente estiver internado ou em
transição (até 7 dias após alta/transferência), ou às segundas-feiras.

- Suba o explorador em background:
  `python3 agent/mychart_explorer.py --out <scratchpad>/mychart_live --port 8765`
  e faça o login descrito no cabeçalho do arquivo, com as variáveis da config
  (nunca imprima valores). Código MFA: o e-mail "Verification Code" mais
  recente no Gmail.
- Colete só o posterior a `since`: Test Results novos (valor, referência,
  alterado?), notas da internação/visita em curso (`/note_text` na página
  `visits/past-details?csn=…&pageMode=notesfirst`), Messages, Appointments
  (novas/canceladas), Documents/Letters, saldo em Billing.
- `/quit` ao terminar. Login falhou ou o código não chegou em 3 min: registre
  na atualização e siga com o resto, sem insistir em loop.

## Passo 3 — Entrada (15_Inbox e arquivos soltos na pasta raiz)

- `search_files`: `parentId = '<inbox>' and createdTime > '<since>'`.
- Áudio → `download_file_content` para uma pasta nova no scratchpad →
  `pip install -q faster-whisper` (se faltar) →
  `python3 agent/transcribe.py <audio> <saida.txt>` → Doc
  "Transcrição — AAAA-MM-DD — <título>" em 14_Documentos_e_conversas com
  resumo de 5 linhas, citações-chave com minuto e a transcrição completa.
- Foto/PDF → ler; registrar o que é, de quem, datas, valores e prazos (carta
  de seguro: prazo de recurso vira lembrete na agenda).
- Arquivo solto na raiz → depois de processar, mover (`update_file` com
  `parentId`) para 14_Documentos_e_conversas ou para a pasta do plano de saúde.
  Nunca apagar nada do usuário.

## Passo 4 — Respostas de outras IAs (16_Respostas_de_outras_IAs)

Arquivos novos desde `since`, exceto os que começam com "Checagem —" →
subagente `fact-checker` → Doc "Checagem — <título>" na mesma pasta.

## Passo 5 — Ficha de fatos

Se um fato verificado mudou (resultado, diagnóstico, remédio, alta ou
transferência, decisão do seguro, consulta), edite `00_FATOS_VERIFICADOS` no
mesmo documento com `mcp__Google_Docs__update_doc` (`replaceAllText` na linha
que mudou; `insertText` com `endOfSegmentLocation` para itens novos) e atualize
a linha "Atualizado:". Sempre com fonte e data. Confirmado sai de "NÃO
CONFIRMADO"; boato novo entra lá.

## Passo 6 — Atualização (só com novidade)

Doc em 13_Atualizacoes: "Atualização AAAA-MM-DD (manhã|noite)", até 1 página:

- 🔴 **Atenção agora**
- 🟢 **Novidades** (cada uma com fonte)
- ❓ **Perguntar à equipe** (inglês simples)
- ✅ **Fazer** (dono, horário)
- 📎 **Links** (notas completas, transcrições, checagens)

## Passo 7 — Agenda

Consultas novas/alteradas: mesma lógica da skill `check-medico` (etiqueta e
cor do paciente, privado, sem duplicar). Prazos (recurso, pagamento) viram
lembrete.

## Passo 8 — Fechar

- `update_file` na pasta de atualizações: descrição `last_sync=<now>`.
- PushNotification só para resultado alterado, mudança de alta/transferência,
  decisão do seguro, carta com prazo ou mensagem nova da equipe. Uma linha.
- Resposta final: 3–6 linhas + link do Doc. Nada novo → "Sem novidades
  (Gmail, MyChart, Inbox)."

## Limites

- O portal do seguro (Wellmark) não abre a partir da nuvem: use os e-mails do
  seguro e as fotos/PDFs da Inbox; o portal exige uma sessão do Claude no
  computador do usuário.
- Nunca enviar e-mails, mensagens ou formulários sem aprovação.
