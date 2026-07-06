---
name: check-medico
description: Checa as consultas médicas no MyChart da UIHC (duas contas — usuário e mãe), sincroniza tudo no calendário "Saúde" do Google Calendar com cores por pessoa, e cria lembretes para especialidades sem consulta futura marcada. Use quando o usuário pedir para checar/sincronizar consultas médicas ou quando o trigger semanal disparar.
---

# check-medico — rotina de sincronização de consultas médicas

Você vai: (1) raspar as consultas do MyChart das duas contas, (2) sincronizá-las
no calendário **"Saúde"** do Google Calendar, (3) detectar especialidades com
consulta passada mas nenhuma futura e criar lembretes de "marcar consulta".
Responda ao usuário em português.

## Contexto fixo

- Config: `agent/config.json` (contas, labels, cores, timezone `America/Chicago`).
- `[Eu]` → colorId **9** (Blueberry). `[Mãe]` → colorId **11** (Tomato).
  Lembretes de "marcar" → colorId **5** (Banana).
- Calendário alvo: o calendário secundário cujo `summary` é **"Saúde"**
  (obtenha o `id` via `list_calendars`). **Nunca** crie eventos no calendário
  primário.

## Passo 0 — Preflight (aborte cedo com relatório claro se algo faltar)

1. Env vars: `MYCHART_EU_USER`, `MYCHART_EU_PASS`, `MYCHART_MAE_USER`,
   `MYCHART_MAE_PASS` devem estar definidas (`printenv | grep -c MYCHART` etc.,
   sem imprimir valores).
2. Rede: `curl -sS -o /dev/null -w "%{http_code}" --max-time 15 https://mychart.uihealthcare.org/MyChart/` —
   se falhar com erro de túnel/403 do proxy, a política de rede do ambiente
   está bloqueando o MyChart; instrua o usuário a liberar
   `mychart.uihealthcare.org` nas configurações do ambiente.
3. Calendário: `list_calendars` deve conter um calendário "Saúde". Se não
   existir, peça ao usuário para criá-lo (Google Calendar → Outros calendários
   → “+” → Criar novo calendário → nome `Saúde`).
4. Dependências: `python3 -c "import playwright"`; se faltar,
   `pip install -r agent/requirements.txt` (o Chromium já está em
   `PLAYWRIGHT_BROWSERS_PATH`, não rode `playwright install`).

Se este for um disparo automático do trigger e o preflight falhar, avise o
usuário **uma única vez** listando o que falta e encerre sem tentar o resto.

## Passo 1 — Raspar o MyChart (uma conta por vez)

Para cada conta (`eu`, depois `mae`):

1. Crie um diretório de saída no scratchpad e rode em background:
   `python3 agent/mychart.py --account <id> --out <outdir>`
2. Monitore `<outdir>/status.json`:
   - `waiting_mfa`: o MyChart mandou um código de verificação por e-mail.
     Busque no Gmail (`search_threads`, query tipo
     `from:(mychart OR uihc OR uihealthcare) code newer_than:1h`), extraia o
     código numérico da mensagem mais recente e escreva-o em
     `<outdir>/mfa_code.txt`. O scraper continua sozinho.
   - `error`: leia o `detail` e os artefatos (`login_failed.txt/png`) para
     diagnosticar. Não tente mais de 2 vezes por conta.
   - `done`: siga adiante.
3. Extraia as consultas você mesmo lendo `<outdir>/visits_upcoming.txt` e
   `<outdir>/visits_past.txt` (e screenshots, se o texto for ambíguo). Para
   cada consulta capture: data, hora, especialidade/departamento, médico,
   local/endereço. Consultas futuras E passadas (passadas: últimos ~24 meses,
   o que a página mostrar).

## Passo 2 — Sincronizar consultas futuras no calendário

1. `list_events` no calendário "Saúde" de hoje até +12 meses.
2. Para cada consulta futura raspada, procure evento existente no mesmo dia
   com o mesmo label e especialidade:
   - Não existe → `create_event`: título `<label> <Especialidade> — <Médico>`,
     `calendarId` do Saúde, `colorId` da conta, `location`, `description` com
     os detalhes brutos raspados, `timeZone: America/Chicago`, e
     `overrideReminders` popup de 1440 e 120 minutos.
   - Existe mas data/hora mudou → `update_event`.
3. Consulta cancelada no MyChart (evento futuro nosso sem consulta
   correspondente na raspagem): pergunte ao usuário antes de deletar, a menos
   que a página confirme explicitamente o cancelamento.

## Passo 3 — Especialidades perdidas (sem consulta futura)

Para cada conta: especialidades presentes nas consultas **passadas** que não
têm nenhuma consulta **futura** agendada.

Para cada uma, verifique se já existe evento `📞 <label> Marcar: <Especialidade>`
no calendário Saúde entre −30 e +30 dias (para não recriar algo que o usuário
viu ou apagou há pouco). Se não existir, crie evento de dia inteiro na próxima
segunda-feira, colorId 5, com descrição explicando: última consulta dessa
especialidade e telefone/instrução de agendamento se aparecer nos dumps.

## Passo 4 — Relatório

Resuma em português: novas consultas adicionadas, alteradas, lembretes de
"marcar" criados, e qualquer falha (login, MFA, rede). Se nada mudou, diga
apenas isso em uma linha.
