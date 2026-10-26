---
name: check-medico
description: Checa as consultas médicas no MyChart da UIHC (contas do usuário e da mãe, Clea), sincroniza tudo no Google Calendar com cores por pessoa, e cria lembretes para especialidades sem consulta futura marcada. Use quando o usuário pedir para checar/sincronizar consultas médicas ou quando o trigger semanal disparar.
---

# check-medico — rotina de sincronização de consultas médicas

Você vai: (1) raspar as consultas do MyChart de cada conta com credenciais,
(2) sincronizá-las no Google Calendar, (3) detectar especialidades com
consulta passada mas nenhuma futura e criar lembretes de "marcar consulta".
Responda ao usuário em português.

## Contexto fixo

- Config: `agent/config.json` (contas, labels, cores, timezone `America/Chicago`).
- `[Eu]` (Bruce) → colorId **9** (Blueberry). `[Mãe]` (Clea) → colorId **11**
  (Tomato). Lembretes de "marcar" → colorId **5** (Banana). Todos os eventos
  com `visibility: private`.
- Calendário alvo: o calendário cujo `summary` é **"Saúde"** (obtenha o `id`
  via `list_calendars`). Enquanto ele não existir, use o calendário principal
  (o usuário aceitou isso em 26/10/2026) e lembre uma vez, no relatório, que
  criar o "Saúde" separa os eventos médicos.
- **A etiqueta vem do paciente detectado, não da variável de ambiente.** O
  scraper grava em `result.json` o campo `patient_name` (o "Welcome, X!" da
  tela inicial). Mapeie pelo `patient_first_name` de cada conta no config
  (Bruce → `[Eu]`, Clea → `[Mãe]`). Em 26/10/2026 as variáveis `MYCHART_EU_*`
  continham o login da Clea; se o nome detectado não bater com a conta usada,
  confie no nome detectado e mencione isso uma vez no relatório.

## Passo 0 — Preflight

1. Credenciais: para cada conta do config, veja se `user_env` e `pass_env`
   estão definidas (`[ -n "${!v}" ]`, **sem imprimir valores**). Rode só as
   contas completas; liste as que faltam no relatório. Só aborte se nenhuma
   conta tiver credenciais.
2. Rede: `curl -sS -o /dev/null -w "%{http_code}" --max-time 15 https://mychart.uihealthcare.org/mychart/Authentication/Login`.
   Se falhar com erro de túnel/403 do proxy, a política de rede do ambiente
   está bloqueando o MyChart: instrua o usuário a liberar
   `mychart.uihealthcare.org` nas configurações do ambiente e aborte.
3. Calendário: `list_calendars`; anote o `id` do "Saúde" ou use o principal.
4. Dependências: `python3 -c "import playwright"`; se faltar,
   `python3 -m pip install -r agent/requirements.txt`. Use `python3 -m pip`:
   neste contêiner o `pip` solto instala para outro Python. O Chromium já está
   em `PLAYWRIGHT_BROWSERS_PATH`; não rode `playwright install` (o scraper cai
   para o binário pré-instalado se a versão não bater).

Se este for um disparo automático do trigger e o preflight abortar, avise o
usuário **uma única vez** listando o que falta e encerre sem tentar o resto.

## Passo 1 — Raspar o MyChart (uma conta por vez)

Para cada conta com credenciais:

1. Anote a hora (UTC), crie um diretório de saída no scratchpad e rode em
   background: `python3 agent/mychart.py --account <id> --out <outdir>`.
   O login real é em duas etapas (usuário → Continue → senha), seguido de
   "Verify your identity"; o scraper escolhe **Send to my email**.
2. Monitore `<outdir>/status.json`:
   - `waiting_mfa`: o código chega em segundos no Gmail do usuário
     (brucedsny@gmail.com), inclusive o da Clea. Busque com `search_threads`
     e a query `from:donotreply-mychart@uihealthcare.org subject:"Verification Code" newer_than:1h`.
     Pegue a mensagem mais recente **posterior à hora anotada** (a saudação diz
     "Hello <nome>"), extraia o número de 6 dígitos do snippet e escreva-o em
     `<outdir>/mfa_code.txt`. O código expira em ~30 min. O scraper continua
     sozinho.
   - `error`: leia o `detail` e os artefatos (`login_failed.*`,
     `login_password_step_missing.*`, `login_page_unrecognized.*`) para
     diagnosticar. Não tente mais de 2 vezes por conta.
   - `done`: siga adiante.
3. Leia `<outdir>/result.json` (`patient_name`) e extraia as consultas você
   mesmo de `<outdir>/visits_upcoming.txt` (a página traz "Upcoming Visits",
   "Future visits" e "Past visits" juntas) e `visits_past.txt`; use os
   screenshots se o texto for ambíguo. Para cada consulta capture: data, hora
   de chegada e de início, departamento/especialidade, profissional,
   local/endereço e telefone.
4. Se as visitas passadas mostrarem uma internação/PS em andamento (sem data de
   fim), as consultas ambulatoriais desses dias provavelmente não vão
   acontecer: sinalize no relatório e na descrição do evento.

## Passo 2 — Sincronizar consultas futuras no calendário

1. `list_events` no calendário alvo de hoje até +12 meses.
2. Para cada consulta futura raspada, procure evento existente no mesmo dia
   com a mesma etiqueta e especialidade. Séries recorrentes (por exemplo, a
   reabilitação cardíaca da Clea, seg/qua/sex às 9h15) contam como existentes
   pelas suas instâncias.
   - Não existe → `create_event`: título `<label> <Especialidade> — <Profissional>`,
     início na hora de chegada, `colorId` da pessoa, `location`, `description`
     com chegada/início/telefone e "Fonte: MyChart", `timeZone: America/Chicago`,
     `visibility: private` e `overrideReminders` popup de 1440 e 120 minutos.
   - Existe mas a data/hora mudou → `update_event`.
3. Consulta cancelada no MyChart (evento futuro nosso sem consulta
   correspondente na raspagem): pergunte ao usuário antes de deletar, a menos
   que a página confirme explicitamente o cancelamento.

## Passo 3 — Especialidades perdidas (sem consulta futura)

Para cada pessoa: especialidades presentes nas consultas **passadas** que não
têm nenhuma consulta **futura** agendada. Ignore PS, internações, telefonemas e
mensagens; considere só especialidades de acompanhamento.

Para cada uma, verifique se já existe evento `📞 <label> Marcar: <Especialidade>`
no calendário alvo entre −30 e +30 dias (para não recriar algo que o usuário
viu ou apagou há pouco). Se não existir, crie um evento de dia inteiro na
próxima segunda-feira, colorId 5, com descrição explicando a última consulta
dessa especialidade e o telefone/instrução de agendamento, se aparecer nos dumps.

## Passo 4 — Relatório

Resuma em português: novas consultas adicionadas, alteradas, lembretes de
"marcar" criados, contas puladas por falta de credenciais e qualquer falha
(login, MFA, rede). Se nada mudou, diga apenas isso em uma linha.
