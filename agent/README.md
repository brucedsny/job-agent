# Agente de consultas médicas (MyChart UIHC → Google Calendar)

Rotina que checa as consultas no MyChart da UIHC de **duas pessoas** (você e
sua mãe), adiciona tudo num calendário dedicado **"Saúde"** do Google Calendar
(mesmo calendário, cores diferentes) e cria lembretes para especialidades com
consulta passada mas nenhuma futura marcada.

## Como funciona

| Peça | Papel |
|------|-------|
| `agent/mychart.py` | Script Playwright que loga no MyChart, resolve o desafio de MFA (código lido do Gmail pelo agente) e salva o texto/screenshots das páginas de consultas. |
| `.claude/skills/check-medico/` | Skill que orquestra: roda o scraper para as duas contas, extrai as consultas dos dumps, sincroniza o calendário via Google Calendar (MCP) e gera o relatório. |
| Trigger semanal | Dispara a skill automaticamente toda semana na sessão do Claude Code. |

Cores no calendário: `[Eu]` azul (Blueberry), `[Mãe]` vermelho (Tomato),
lembretes de "marcar consulta" amarelo (Banana).

## Setup (uma vez)

1. **Crie o calendário "Saúde"** no Google Calendar:
   Outros calendários → `+` → Criar novo calendário → nome `Saúde`.
   (O conector do Calendar cria eventos, mas não calendários.)

2. **Credenciais do MyChart** — nas configurações do *environment* do Claude
   Code (claude.ai/code → seu ambiente → variáveis de ambiente), defina:
   ```
   MYCHART_EU_USER / MYCHART_EU_PASS    (sua conta)
   MYCHART_MAE_USER / MYCHART_MAE_PASS  (conta da sua mãe)
   ```
   Nunca commite esses valores (`.env` está no `.gitignore`).

   *Alternativa:* se você tem **acesso proxy** ao prontuário da sua mãe pela
   sua própria conta, edite `agent/config.json`: na conta `mae`, aponte
   `user_env`/`pass_env` para as suas credenciais e preencha `persona` com o
   nome dela como aparece no seletor de pessoa do MyChart.

3. **Política de rede** — o ambiente precisa alcançar
   `mychart.uihealthcare.org`. Nas configurações do ambiente, adicione esse
   domínio à lista de permissões de rede (ou use "todos os domínios").

4. **MFA por e-mail** — deixe a verificação em duas etapas do MyChart
   configurada para enviar o código ao Gmail conectado ao Claude
   (brucedsny@gmail.com), para o agente conseguir ler o código sozinho.

## Uso

- Manual: digite `/check-medico` numa sessão do Claude Code neste repo.
- Automático: o trigger semanal roda a mesma skill e só avisa se houver
  novidade ou problema.

## Limitações conhecidas

- Scraping de portal Epic pode quebrar se a UIHC mudar o layout; o script
  salva screenshots/dumps justamente para o agente se adaptar, mas ajustes em
  `mychart.py` podem ser necessários.
- Se o MyChart exigir CAPTCHA ou bloquear automação, será preciso intervenção
  manual (a skill reporta isso).
