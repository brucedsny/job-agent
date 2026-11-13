---
name: atualiza
description: Atualização do caso da mãe — só o novo desde o last_sync no MyChart, Gmail e 90_Entrada; agenda de consultas, documentos centrais e resumo em 80_Atualizacoes. Use para "atualiza"/"atualize" ou no agendamento.
---

# atualiza — só o que é novo

Nada novo → grave o marcador e responda em uma linha, sem documento nem
notificação. O scratchpad some quando o contêiner reinicia: a memória é o
Drive. Esta skill não envia nada a ninguém. Antes de perguntar algo ao
usuário, procure no Gmail (inclusive Wave Notes), nos documentos centrais e
nas últimas `80_Atualizacoes`; nunca pergunte o que já está registrado.

## 0. Preparar
- `since` = `last_sync=<RFC3339>` na descrição da pasta `80_Atualizacoes`
  (`get_file_metadata`); sem marcador, últimas 24 h. Anote `now` (UTC).
- Leia `00_ESTADO_ATUAL` (onde ela está, o que está pendente).
- Preflight sem imprimir valores: credenciais `MYCHART_*` e `WELLMARK_*` (`[ -n "${VAR:-}" ]`);
  rede: `curl -sS -o /dev/null -w "%{http_code}" --max-time 15 https://mychart.uihealthcare.org/mychart/Authentication/Login`
  (erro de túnel ou 403 do proxy → peça para liberar `mychart.uihealthcare.org`
  no ambiente e siga sem MyChart); `python3 -c "import playwright"`, senão
  `python3 -m pip install -r agent/requirements.txt` (nunca `playwright install`).
- Disparo automático sem nada para rodar: avise uma vez o que falta e encerre.

## 1. Gmail (sempre)
- `search_threads` com `after:<since em epoch>`:
  `from:(uihealthcare.org OR uiowa.edu OR wellmark.com OR clinixhealthcare.com OR iowacourts.gov OR iid.iowa.gov) -subject:"Verification Code"`,
  e outra pelo primeiro nome da mãe e pelos domínios extras do `03_CONTATOS`
  (casa de cuidado, advogado etc.).
- Wave Notes: `from:support@wave.co "Wave Notes" after:<since em epoch>`. Das
  que falam da mãe, grave só os fatos dela (passo 5); notas de saúde do
  próprio usuário nunca entram no caso.
- Leia só threads novos. Classifique: hospital/portal · HIM (prontuário) ·
  seguro · CLINIX (revisão externa) · tribunal · casa de cuidado · contas.
- Aviso do portal → passo 2. Prazo (recurso, audiência, pagamento) → passo 3.

## 2. MyChart
Entre se o usuário pediu, se houve aviso do portal, se ela está internada ou
em transição (até 7 dias após alta ou transferência), ou às segundas.
- Explorador e login como no CLAUDE.md. Anote a hora antes de pedir o código;
  use o e-mail `from:donotreply-mychart@uihealthcare.org subject:"Verification Code" newer_than:1h`
  mais recente depois dela (a saudação "Hello <nome>" diz de qual conta é;
  expira em ~30 min). Falhou ou o código não chegou em 3 min → registre e
  siga; no máximo 2 tentativas por conta.
- Só o posterior a `since`: Test Results (valor, referência, alterado?),
  notas da internação ou visita (`/note_text` em
  `visits/past-details?csn=…&pageMode=notesfirst`; uma por vez com
  `agent/tools/readnote.sh`), Messages, Documents/Letters, saldo em Billing e
  a página Visits (`/text`: traz "Upcoming", "Future" e "Past" juntas). `/quit`.
- Se existirem `MYCHART_MAE_*` e `MYCHART_EU_*`, a conta `eu` é a do usuário:
  às segundas, `python3 agent/mychart.py --account eu --out <scratchpad>/eu`
  em background; em `status.json` = `waiting_mfa`, grave o código em
  `<out>/mfa_code.txt`; `error` → leia `detail` e os `login_*`; use
  `visits_upcoming.txt` e `visits_past.txt` (os `.png` se o texto for ambíguo).

## 2b. Wellmark (portal do seguro)
Rode se o usuário pediu, se chegou e-mail do Wellmark desde `since` ou às
segundas (cada login dispara um código de verificação).
- `python3 agent/wellmark.py --out <scratchpad>/wellmark_dl --since <since>`
  em background. `status.json` = `waiting_mfa` com `mfa_channel: email` →
  código do e-mail mais recente do Wellmark (`from:wellmark.com newer_than:1h`)
  em `<out>/mfa_code.txt`.
- Exit 6 (MFA por SMS) ou 7 (CAPTCHA, bot check ou "Loading" sem fim; veja
  `blocked.txt`): uma linha no resumo e siga com e-mails e cartas. Nunca
  contorne. SMS só com o usuário presente (`--allow-sms`; ele passa o código).
- `index.json`: suba para `30_Seguro_Wellmark_e_contas` só os `file` cujo nome
  ainda não existe lá nem em `PLANO DE SAUDE` (pule os `same_text_as`):
  `create_file` com `base64Content` = `sha256:<sha256>:<caminho absoluto>`,
  `application/pdf` e `disableConversionToGoogleType`. Atualize o Doc
  `30_INDICE_WELLMARK` (data, tipo, título, status, arquivo).
- Autorização ou carta nova, ou claim `Denied` novo → `00_ESTADO_ATUAL` e
  `01_FATOS` (seção Seguro); prazo de recurso da carta → passo 3.

## 3. Agenda
- Calendário "Saúde" (`list_calendars`; sem ele, o principal — diga uma vez
  que criá-lo separa os eventos). `America/Chicago`, `visibility: private`.
  Cores em `agent/config.json`: `[Mãe]` 11, `[Eu]` 9, lembretes 5.
- Etiqueta pelo paciente da página ("Welcome, X!" / `patient_name`) comparado
  com o `03_CONTATOS`, não pela variável usada; divergiu → diga uma vez.
- Consulta futura: data, chegada, início, especialidade, profissional, local,
  telefone. `list_events` de hoje a +12 meses; mesmo dia + etiqueta +
  especialidade = já existe (séries recorrentes contam pelas instâncias).
  - Não existe → `create_event` "`<etiqueta> <Especialidade> — <Profissional>`",
    início na chegada, `colorId`, `location`, descrição (chegada, início,
    telefone, "Fonte: MyChart"), `overrideReminders` popup 1440 e 120.
  - Mudou → `update_event`. Sumiu do MyChart → pergunte antes de apagar, salvo
    cancelamento explícito na página.
- Internação ou PS em andamento (visita passada sem fim): as consultas desses
  dias provavelmente não acontecem — avise no resumo e na descrição do evento.
- Especialidade de acompanhamento com consulta passada e nenhuma futura
  (ignore PS, internação, telefonema, mensagem): sem `📞 <etiqueta> Marcar:
  <Especialidade>` entre −30 e +30 dias → evento de dia inteiro na próxima
  segunda, colorId 5, com a última consulta e o telefone de marcação.
- Prazo de carta ou e-mail → lembrete de dia inteiro, colorId 5, sem duplicar.

## 4. Drive `90_Entrada` (e arquivos novos soltos na raiz)
- `search_files`: `parentId = '<id da 90_Entrada>' and createdTime > '<since>'`.
- Lote grande (dezenas de arquivos): primeiro um Doc "Inventário 90_Entrada —
  AAAA-MM-DD" em `80_Atualizacoes` (arquivo · tipo · data · de quem · o que
  traz · destino) e os achados decisivos no resumo e na resposta; só então mova.
- Áudio → `download_file_content` para uma pasta nova no scratchpad →
  `python3 -m pip install -q faster-whisper` (se faltar) →
  `python3 agent/transcribe.py <audio> <saida.txt>` → Doc "Transcrição —
  AAAA-MM-DD — <título>" na pasta do tema (resumo de 5 linhas, citações com
  minuto, texto todo).
- Foto, PDF, carta → leia; registre o que é, de quem, datas, valores, prazos.
- Resposta de outra IA (na Entrada ou nova em `70_Analises_juntas_e_outras_IAs`,
  exceto "Checagem —…") → `fact-checker` → Doc "Checagem — <título>" na `70_`.
- Processado → mova (`update_file` com `parentId`) para a pasta do tema,
  conforme o `04_MAPA_DA_PASTA`. Nunca apague nada.

## 5. Documentos centrais
Fato que mudou (resultado, diagnóstico, remédio, alta ou transferência,
decisão do seguro, consulta, prazo) → grave como na skill `mae`, seção 3.

## 6. Resumo e fechamento
- Com novidade: Doc "Atualização AAAA-MM-DD (manhã|noite)" em
  `80_Atualizacoes`, até 1 página: 🔴 Atenção agora · 🟢 Novidades (com
  fonte) · ❓ Perguntar à equipe (inglês simples) · ✅ Fazer (dono, horário) ·
  📎 Links.
- `update_file` na pasta `80_Atualizacoes`: descrição `last_sync=<now>`.
- Notificação push só para: resultado alterado, alta ou transferência,
  decisão do seguro, carta com prazo, mensagem nova da equipe.
- Resposta: 3–6 linhas + link do Doc; falhas (login, MFA, rede, credencial)
  em uma linha. Nada novo → "Sem novidades (Gmail, MyChart, Entrada)."
