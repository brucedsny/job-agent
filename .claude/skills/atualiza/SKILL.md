---
name: atualiza
description: Atualização do caso da mãe — só o novo desde o último sucesso de cada fonte no MyChart, Gmail e 90_Entrada; agenda de consultas, documentos centrais e resumo em 80_Atualizacoes. Use para "atualiza"/"atualize" ou no agendamento.
---

# atualiza — só o que é novo

Nada novo e lote completo → só o fechamento do passo 8 (marcadores, log e
sinal) e a resposta curta do fim, sem documento nem notificação. O scratchpad
some quando o contêiner reinicia: a memória é o Drive. Esta skill não envia
nada a ninguém. Toda gravação (Doc, evento, arquivo, linha) é relida:
✅ voltou, ❌ não voltou. Releia com `read_doc` (Doc) ou `get_values`
(planilha). O `read_file_content` corta os ~5 últimos caracteres do Doc:
com ele, confira um trecho do meio do texto gravado, nunca o fim, para não
gerar ❌ falso.

## 0. Preparar
- `run_id` = `now` = início da rodada (UTC, RFC3339).
- `versao` = `git rev-parse --short HEAD` depois do `git pull` (a versão das
  skills que esta rodada carregou); `junta_prompt` = a linha `prompt: …` que a
  junta anotou no passo 7 (registro `00_REGISTRO_DE_PROMPTS`; no modo rápido,
  a linha `MODO_RAPIDO`), copiada como veio; sem junta, "não rodou". Os dois vão no `Log_robo` e na
  última linha do resumo.
- Marcadores: `read_doc` no Doc `_MARCADOR_last_sync` da `80_Atualizacoes`
  (pode vir com `\_`). Linha `last_sync=<UTC>` e, em qualquer lugar do Doc
  (as que faltam entram no fim), uma linha por fonte: `fonte:mychart=`,
  `fonte:gmail=`, `fonte:agenda=`, `fonte:entrada=`, `fonte:wellmark=` e
  `fonte:painel=`, cada uma com `<UTC>` (RFC3339). Só o passo 8.2 grava
  neste Doc, com a regra de lá; se o prompt do agendamento mandar gravar o
  `last_sync` de outro jeito, vale esta skill.
- `since` de cada fonte = a linha dela; sem a linha, `last_sync`; sem o Doc,
  a descrição da pasta (`get_file_metadata`); sem marcador, últimas 24 h.
  Cada fonte lê só o novo desde o SEU `since`. Agenda ou painel mais atrás
  que as outras → completem com o registrado desde o `since` deles (resumos
  da `80_Atualizacoes`, `01_FATOS`); a checagem da agenda e o `id_fonte`
  evitam repetir.
- Leia `00_ESTADO_ATUAL` (onde ela está, o que está pendente).
- Preflight sem imprimir valores: credenciais `MYCHART_*` e `WELLMARK_*` (`[ -n "${VAR:-}" ]`);
  rede: `curl -sS -o /dev/null -w "%{http_code}" --max-time 15 https://mychart.uihealthcare.org/mychart/Authentication/Login`
  (erro de túnel ou 403 do proxy → peça para liberar `mychart.uihealthcare.org`
  no ambiente e siga sem MyChart); `python3 -c "import playwright"`, senão
  `python3 -m pip install -r agent/requirements.txt` (nunca `playwright install`).
- Disparo automático sem nada para rodar: avise uma vez o que falta e encerre.

## 1. Gmail (sempre)
- `search_threads` com `after:<since do Gmail em epoch>`:
  `from:(uihealthcare.org OR uiowa.edu OR wellmark.com OR clinixhealthcare.com OR iowacourts.gov OR iid.iowa.gov) -subject:"Verification Code"`,
  e outra pelo primeiro nome da mãe e pelos domínios extras do `03_CONTATOS`
  (casa de cuidado, advogado etc.).
- Leia só threads novos. Classifique: hospital/portal · HIM (prontuário) ·
  seguro · CLINIX (revisão externa) · tribunal · casa de cuidado · contas.
- Aviso do portal → passo 2. Prazo (recurso, audiência, pagamento) → passo 3.

## 2. MyChart
Entre se o usuário pediu, se houve aviso do portal desde o `since` dele, se
ela está internada ou em transição (até 7 dias após alta ou transferência),
às segundas ou se esse `since` passa de 7 dias.
- Explorador e login como no CLAUDE.md. Anote a hora antes de pedir o código;
  use o e-mail `from:donotreply-mychart@uihealthcare.org subject:"Verification Code" newer_than:1h`
  mais recente depois dela (a saudação "Hello <nome>" diz de qual conta é;
  expira em ~30 min). Falhou ou o código não chegou em 3 min → registre e
  siga; no máximo 2 tentativas por conta.
- Só o posterior ao `since` do MyChart: Test Results (valor, referência,
  alterado?), notas da internação ou visita (`/note_text` em
  `visits/past-details?csn=…&pageMode=notesfirst`; uma por vez com
  `agent/tools/readnote.sh`), Messages, Documents/Letters, saldo em Billing e
  a página Visits (`/text`: traz "Upcoming", "Future" e "Past" juntas). `/quit`.
- Se existirem `MYCHART_MAE_*` e `MYCHART_EU_*`, a conta `eu` é a do usuário:
  às segundas, `python3 agent/mychart.py --account eu --out <scratchpad>/eu`
  em background; em `status.json` = `waiting_mfa`, grave o código em
  `<out>/mfa_code.txt`; `error` → leia `detail` e os `login_*`; use
  `visits_upcoming.txt` e `visits_past.txt` (os `.png` se o texto for ambíguo).

## 2b. Wellmark (portal do seguro)
Rode se o usuário pediu, se chegou e-mail do Wellmark desde o `since` dele ou
às segundas (cada login dispara um código de verificação).
- `python3 agent/wellmark.py --out <scratchpad>/wellmark_dl --since <since do Wellmark>`
  em background. `status.json` = `waiting_mfa` com `mfa_channel: email` →
  código do e-mail mais recente do Wellmark (`from:wellmark.com newer_than:1h`)
  em `<out>/mfa_code.txt`.
- Exit 6 (MFA por SMS) → "NÃO verificado (precisa de SMS)"; exit 7 (CAPTCHA,
  bot check ou "Loading" sem fim; veja `blocked.txt`) → "falhou (<o quê>)".
  Siga com e-mails e cartas. Nunca contorne. SMS só com o usuário presente
  (`--allow-sms`; ele passa o código).
- `index.json`: suba para `30_Seguro_Wellmark_e_contas` só os `file` cujo nome
  ainda não existe lá nem em `PLANO DE SAUDE` (pule os `same_text_as`):
  `create_file` com `base64Content` = `sha256:<sha256>:<caminho absoluto>`,
  `application/pdf` e `disableConversionToGoogleType`. Atualize o Doc
  `30_INDICE_WELLMARK` (data, tipo, título, status, arquivo).
- Autorização ou carta nova, ou claim `Denied` novo → `00_ESTADO_ATUAL` e
  `01_FATOS` (seção Seguro); prazo de recurso da carta → passo 3.

## 3. Agenda
- Calendário "Saúde" (`list_calendars`; sem ele, o principal). O aviso de
  que criá-lo separa os eventos sai uma vez só: em ⚙️ só se o marcador não
  tem a linha `aviso:agenda_sem_saude=`, que o passo 8.2 acrescenta. `America/Chicago`, `visibility: private`.
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
- `search_files`: `parentId = '<id da 90_Entrada>' and createdTime > '<since da Entrada>'`.
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
decisão do seguro, consulta, prazo) → grave como na skill `mae`, seção 3:
referência completa, `[INF]` para hipótese e, se contradiz fato anterior,
"Correção DD/MM: antes X (fonte A) → agora Y (fonte B); motivo", com o antigo
marcado "(superado em DD/MM)" — nunca apague nem sobrescreva.

## 6. Painel
- Planilha `05_PAINEL_DA_… (planilha)` na raiz da pasta da mãe, achada pelo
  título (nunca fixe o id): `search_files` com
  `parentId = '<id da raiz>' and title contains '05_PAINEL' and mimeType = 'application/vnd.google-apps.spreadsheet'`.
- Abas: `get_spreadsheet`. Sem a planilha ou sem a aba `LEIAME` → painel
  "NÃO verificado (motivo)" e pule o passo.
- **Trava** (antes da primeira gravação na planilha, `Log_robo` incluído):
  `get_values` em `LEIAME!A:C` e ache a linha com `TRAVA_ROBO` na coluna A
  (B = `travado_por`, C = `ate` UTC). Sem ela → `update_values` de
  `TRAVA_ROBO | livre |` duas linhas abaixo da última preenchida (nunca
  `append_values`: no LEIAME ele cai na primeira linha vazia entre blocos).
  - B diferente de `livre` e C no futuro → outra sessão está gravando:
    painel "NÃO verificado (travado por <B> até <C>)", sem gravar nada na
    planilha nesta rodada (o `Log_robo` vai só para o resumo).
  - Livre ou vencida → `update_values` em B:C com `<run_id> | <now + 45 min>`;
    releia: B ≠ `run_id` → perdeu a vez, igual ao item acima.
  - Libere no passo 8.1 (`livre | <fim UTC>`), também quando a rodada
    abortar; releia. Não liberou → "❌ trava não liberada".
- Com a trava, siga o contrato escrito no `LEIAME` (colunas na ordem do
  cabeçalho de cada aba, lido antes de gravar; nunca pela memória):
  - linhas novas desde o `since` do painel nas abas (exames, sinais, remédios,
    cognição/comportamento, infecções, exames pendentes, perguntas), com
    `append_values` e sem repetir `id_fonte` (leia a coluna antes);
  - aplique a aba `Regras_alerta` e acrescente à aba `Alertas` só os
    alertas novos.

## 7. Junta automática
Só se a rodada trouxe novidade clínica (nota, exame, remédio ou alerta): a
etapa de verificação (`/junta` no modo rápido) só sobre o que mudou. No
resumo, logo abaixo dos três blocos do topo (passo 8):
"🩺 Junta (automática): o que mudou · bom ou ruim · risco · 3 perguntas para a equipe"
(perguntas em inglês simples, com tradução). Recomendação concreta só entra
se passar na etapa de verificação. Sem novidade clínica, não rode.

## 8. Resumo e fechamento
- Com novidade ou lote incompleto: Doc "Atualização AAAA-MM-DD (manhã|noite)"
  em `80_Atualizacoes`, até 1 página. No topo, três blocos separados (bloco
  vazio sai): 🚨 Urgência clínica (só se disparou regra 🔴 da aba
  `Regras_alerta` ou uma nota documenta algo urgente) · 🆕 Novidades
  importantes · ⚙️ Falhas operacionais. Sem urgência, nunca um título
  vermelho "ATENÇÃO AGORA". Depois: 🩺 Junta (passo 7) · ❓ Perguntar à
  equipe (inglês simples) · ✅ Fazer (dono, horário) · 📡 Fontes · 📎 Links.
  Última linha: "Lote: completo" ou "Lote: incompleto (o que faltou)",
  seguida de "· versão <versao> · junta: <junta_prompt>".
- Em todo o resumo (Junta incluída): cada fato com referência recuperável
  `[fonte · tipo do documento · título ou ID da nota/arquivo · data e hora ·
  seção]`, com link ou ID do Drive quando houver ("[MyChart]" sozinho não
  basta); causa ou interpretação ("o principal gatilho é…", "piorou
  porque…") → `[INF]` (hipótese), salvo se o original a documenta — então
  cite entre aspas.
- 📡 Fontes (com o `run_id`): uma linha por fonte — Gmail, MyChart,
  Wellmark, Agenda, Entrada, Painel — com só um destes status (hora em CT):
  "novidade" · "sem novidade (verificado às HH:MM)" · "NÃO verificado
  (motivo)" (ex.: Wellmark pedindo SMS, MyChart fora da vez) · "falhou
  (erro)". Fonte pulada nunca é "sem novidade": e-mail ausente não prova que
  o portal está sem novidade.
- Travou em algo que só o usuário resolve (código, aprovação, credencial,
  liberar rede; o SMS do Wellmark não conta) → em ⚙️,
  "bloqueado: precisa do <nome do usuário>: <o quê>".
- Notificação push só para: urgência clínica, resultado alterado, alta ou
  transferência, decisão do seguro, carta com prazo, mensagem nova da equipe.
- `lote_completo` = sim só se toda fonte da vez (a que os passos 1–6 mandam
  rodar agora) foi verificada e nenhuma gravação da rodada deu ❌ (Doc,
  evento, arquivo, linha do painel, `Log_robo`, trava, marcador). Fonte fora
  da vez ou Wellmark parado só no SMS: "NÃO verificado", sem deixar o lote
  incompleto; painel travado por outra sessão deixa.
- **Regra dos marcadores:** QUALQUER ❌ na rodada → NENHUM marcador avança,
  nem o `last_sync`, e a rodada seguinte relê tudo desde os marcadores
  antigos (o `id_fonte` e a checagem da agenda evitam repetir). Sem ❌:
  avança a linha `fonte:` de cada fonte verificada; `last_sync` só com
  `lote_completo` = sim. O sinal (item 3) fica fora: vem depois e não
  guarda dado.
- Depois de salvar e reler o resumo (sem Doc: direto), nesta ordem:
  1. **Log** — com a trava do passo 6, `append_values` de uma linha no
     `Log_robo`, nas colunas do cabeçalho:
     `inicio_utc | fim_utc | fontes_ok | linhas_novas | alertas | erros | observacao | docs | marcadores | sinal | lote_completo | versao | junta_prompt`
     — inicio_utc: o `run_id`; fontes_ok: o status de cada fonte;
     linhas_novas: as acrescentadas, por aba; docs: cada Doc gravado, ✅ ou
     ❌; marcadores: os que vão avançar ou "nenhum (❌ na rodada)"; sinal:
     "a gravar"; lote_completo: sim ou não. Cabeçalho: nunca reescreva a
     linha 1 quando houver dados; faltando colunas desta lista, escreva só os
     nomes que faltam nas células vazias logo depois da última preenchida;
     coluna que não existe nem pode ser criada → o valor vai em observacao.
     Releia a linha (`get_values`) e libere a trava; releia.
  2. **Marcadores** — pela regra acima. Um único `update_doc` no
     `_MARCADOR_last_sync` (as trocas entram juntas ou nenhuma), com
     `replaceAllText` da linha inteira exata de agora (sem as `\` de escape;
     nunca só o valor, que pode se repetir em outra linha):
     `fonte:<nome>=<anterior>` → `fonte:<nome>=<hora UTC em que a
     verificação dela começou>`; `last_sync=<anterior>` → `last_sync=<now>`;
     linha que falta (e `aviso:agenda_sem_saude=<now>`, se avisou) →
     `insertText` no fim do Doc. Nunca com `update_file` (pede aprovação e
     trava a rodada sem ninguém). Releia com `read_doc`; o que não voltou (ou
     sem o Doc) → "❌ marcador <linha> não gravado" no resumo, `lote_completo`
     = não e, na linha do log, marcadores = "❌ não gravado".
  3. **Sinal**, por último — Doc `_SINAL_ROBO_MAE` (pasta `00_CEREBRO_…` do
     usuário; ache pelo título com `search_files`). Troque a PRIMEIRA linha por
     "🟢 Robô da mãe: rodou DD/MM às HHhMM (CT), resumo salvo às HHhMM. Fontes: …"
     (CT = America/Chicago; cada fonte com o status do 📡 Fontes; sem Doc →
     "sem novidade nas fontes verificadas" no lugar do resumo) com
     `update_doc` e `replaceAllText` da primeira linha exata de agora (sem as
     `\` de escape); releia. Sem o Doc ou não voltou → diga na resposta e
     ponha ❌ no `sinal` da linha do log. Por fim, troque o "a gravar" do
     `sinal` na linha do log por ✅ ou ❌ (`update_values` só nessa célula).
     - 🟢 só com `lote_completo` = sim e sem alerta novo.
     - 🟡 lote incompleto → "rodada incompleta — ver resumo"; alerta novo na
       aba `Alertas` → sobre ele, só "alerta de saúde novo — veja o resumo".
     - 🔴 se houver qualquer "❌" (vence o 🟡).
     - Nessa linha, nunca detalhe de saúde, nome de remédio ou do caso.
- Resposta: 3–6 linhas na ordem do resumo + link do Doc; falhas (login, MFA,
  rede, credencial) em uma linha; por último a linha "Lote: …". Sem Doc →
  uma linha com o status de cada fonte e a linha "Lote: …".
