---
name: atualiza
description: Atualização do caso da mãe — só o novo desde o last_sync no MyChart, Gmail e 90_Entrada; agenda de consultas, documentos centrais e resumo em 80_Atualizacoes. Use para "atualiza"/"atualize" ou no agendamento.
---

# atualiza — só o que é novo

Nada novo → só o fechamento do passo 8 (marcador, log e sinal) e resposta de
uma linha, sem documento nem notificação. O scratchpad some quando o contêiner
reinicia: a memória é o Drive. Esta skill não envia nada a ninguém.

## 0. Preparar
- `since` = `last_sync=<RFC3339>` do Doc `_MARCADOR_last_sync` na
  `80_Atualizacoes` (`read_doc`; pode vir como `last\_sync`); sem o Doc, da
  descrição da pasta (`get_file_metadata`); sem marcador, últimas 24 h.
  Anote `now` (UTC).
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

## 6. Painel
- Planilha `05_PAINEL_DA_… (planilha)` na raiz da pasta da mãe, achada pelo
  título (nunca fixe o id): `search_files` com
  `parentId = '<id da raiz>' and title contains '05_PAINEL' and mimeType = 'application/vnd.google-apps.spreadsheet'`.
- Abas: `get_spreadsheet`. Sem a planilha ou sem a aba `LEIAME` → pule o
  passo e anote no resumo. Com ela, siga o contrato escrito no `LEIAME`:
  - linhas novas desta rodada nas abas (exames, sinais, remédios,
    cognição/comportamento, infecções, exames pendentes, perguntas), com
    `append_values` e sem repetir `id_fonte` (leia a coluna antes);
  - aplique a aba `Regras_alerta` e acrescente à aba `Alertas` só os
    alertas novos.

## 7. Junta automática
Só se a rodada trouxe novidade clínica (nota, exame, remédio ou alerta): a
etapa de verificação (`/junta` no modo rápido) só sobre o que mudou. No TOPO
do resumo:
"🩺 Junta (automática): o que mudou · bom ou ruim · risco · 3 perguntas para a equipe"
(perguntas em inglês simples, com tradução). Recomendação concreta só entra
se passar na etapa de verificação. Sem novidade clínica, não rode.

## 8. Resumo e fechamento
- Com novidade: Doc "Atualização AAAA-MM-DD (manhã|noite)" em
  `80_Atualizacoes`, até 1 página: 🩺 Junta (passo 7, no topo) · 🔴 Atenção
  agora · 🟢 Novidades (com fonte) · ❓ Perguntar à equipe (inglês simples) ·
  ✅ Fazer (dono, horário) · 📎 Links.
- Travou em algo que só o usuário resolve (código, aprovação, credencial,
  liberar rede; o SMS do Wellmark não conta) → no resumo,
  "bloqueado: precisa do <nome do usuário>: <o quê>".
- Notificação push só para: resultado alterado, alta ou transferência,
  decisão do seguro, carta com prazo, mensagem nova da equipe.
- Depois de salvar o resumo (nada novo: direto), nesta ordem:
  1. **Marcador** — `update_doc` no `_MARCADOR_last_sync` com `replaceAllText`
     do valor anterior exato (o RFC3339, sem `last_sync=`) por `<now>`;
     releia com `read_doc`. Nunca com `update_file` (pede aprovação e trava a
     rodada sem ninguém). Não voltou `last_sync=<now>` (ou não há o Doc) →
     "❌ marcador não gravado" no resumo (nada novo: na resposta).
  2. **Log** — aba `Log_robo` existe → `append_values` de uma linha:
     `inicio_utc | fim_utc | fontes_ok | linhas_novas | alertas | erros | observacao`.
  3. **Sinal**, por último — Doc `_SINAL_ROBO_MAE` (pasta `00_CEREBRO_…` do
     usuário; ache pelo título com `search_files`). Troque a PRIMEIRA linha por
     "🟢 Robô da mãe: rodou DD/MM às HHhMM (CT), resumo salvo às HHhMM. Fontes: …"
     (CT = America/Chicago; cada fonte ok, falhou ou pulada; nada novo →
     "sem novidades" no lugar do resumo) com `update_doc` e `replaceAllText`
     da primeira linha exata de agora (sem as `\` de escape); releia. Sem o
     Doc ou não voltou → diga na resposta.
     - 🟡 se o resumo tem "bloqueado: precisa do <nome do usuário>", se uma
       fonte falhou (Wellmark pulado por SMS não conta) ou se entrou alerta
       novo na aba `Alertas` — sobre ele, só
       "alerta de saúde novo — veja o resumo".
     - 🔴 se houver qualquer "❌" (vence o 🟡).
     - Nessa linha, nunca detalhe de saúde, nome de remédio ou do caso.
- Resposta: 3–6 linhas + link do Doc; falhas (login, MFA, rede, credencial)
  em uma linha. Nada novo → "Sem novidades (Gmail, MyChart, Entrada)."
