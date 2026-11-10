# CLAUDE.md

Guia de contexto para o Claude Code neste repositório.

## Sobre o projeto

`job-agent` — agentes pessoais de automação rodando sobre o Claude Code.

**Agente atual: consultas médicas (MyChart UIHC → Google Calendar).**
Stack: Python 3.11 + Playwright (Chromium pré-instalado em
`PLAYWRIGHT_BROWSERS_PATH`; não rode `playwright install`). Documentação e
setup em `agent/README.md`; orquestração em `.claude/skills/check-medico/`.
Sincroniza as consultas de duas contas do MyChart no calendário "Saúde" do
Google Calendar (via MCP) e cria lembretes de especialidades sem consulta
futura. Credenciais só por variáveis de ambiente (`MYCHART_*`) — nunca
commitar segredos nem imprimir seus valores.

Também acompanha a saúde da mãe 2x/dia (skills `health-*`): ficha de fatos
verificados, atualizações e transcrições ficam no Google Drive do usuário.
Dados de paciente nunca entram no repositório.

## Convenções

- **Idioma:** as respostas ao usuário podem ser em português; código, nomes e
  mensagens de commit em inglês, salvo indicação contrária.
- **Branches:** desenvolva em branches de feature; nunca faça push direto para a
  branch padrão sem permissão explícita.
- **Commits:** mensagens curtas e descritivas no imperativo (ex: "add login
  handler"). Não inclua identificadores de modelo nas mensagens.
- **PRs:** só abra um PR quando solicitado. Mantenha-os pequenos e focados.

## Skills disponíveis

Invoque com `/<nome>`:

- `/check-medico` — sincroniza consultas do MyChart (UIHC) no calendário
  "Saúde" do Google Calendar e cria lembretes de especialidades pendentes.
- `/health-sync` — rotina 2x/dia (MyChart + Gmail + Inbox do Drive) que
  atualiza a ficha de fatos e escreve a atualização no Drive.
- `/health-advocate` — respostas de advocacia em saúde com fonte (Vitórias /
  Brechas / A real / O que dizer / Checklist).
- `/junta` — análise do caso inteiro por uma junta médica (padrão),
  jurídica/social (`/junta juridica`) ou as duas (`/junta ambas`), com a
  "junta do diabo" atacando o rascunho; `/junta diabo <texto>` só critica.
  Carrega prompts e ficha do Drive.
- `/pr-review` — revisão do diff atual (bugs + melhorias).
- `/security-review` — revisão de segurança das mudanças do branch.
- `/commit-pr` — commit limpo + abertura de PR.
- `/triage-issue` — investigação e triagem de uma issue.

Subagentes (`.claude/agents/`):
- `fact-checker` — checa afirmações de outras IAs ou rascunhos contra o
  prontuário e devolve só o veredito com fonte.
- `junta-diabo` — equipe vermelha que ataca rascunhos da junta (fatos,
  evidência, lei, segurança, vieses) e devolve MANTER / AJUSTAR / RETIRAR.

**Regra de segurança:** qualquer recomendação concreta sobre a mãe (comida,
remédio, suplemento, exame, atividade, documento ou contrato) passa antes pelo
"portão de segurança" do prompt da junta no Drive (alergias, intolerâncias,
remédios e riscos), mesmo em perguntas rápidas. Use `/junta` no modo rápido.
O hook `UserPromptSubmit` (`.claude/hooks/junta-reminder.sh`) lembra disso a
cada mensagem; a junta completa com `junta-diabo` fica para decisões grandes.

## Comandos do projeto

```
# Instalar deps:  pip install -r agent/requirements.txt
# Rodar scraper:  python3 agent/mychart.py --account eu --out <dir>
# Rotina toda:    /check-medico
# Checar sintaxe: python3 -m py_compile agent/mychart.py
# Transcrever:    python3 agent/transcribe.py <audio> <saida.txt>  (pip install faster-whisper)
```

## MyChart da Clea a partir da nuvem (funciona — não peça senha ao usuário)

O MyChart da UIHC abre pela nuvem. O login vem das variáveis de ambiente
`MYCHART_EU_USER`/`MYCHART_EU_PASS` (hoje com o login da Clea; use
`MYCHART_MAE_*` se existirem). Nunca peça usuário/senha nem imprima valores.

1. `setsid -f nohup python3 agent/mychart_explorer.py --out <scratchpad>/mychart_live --port 8765 >/dev/null 2>&1`
2. Siga a sequência de login do cabeçalho de `agent/mychart_explorer.py`
   (`fill_secret` para usuário e senha; `#emailCode` para o código).
3. Código MFA: o e-mail "Verification Code" mais recente no Gmail
   (`newer_than:1h`). Se não chegar em 3 min, peça ao usuário só o código.
4. Leia com `/text`, `/links`, `/note_text`; feche com `/quit`.

Memória do caso: Google Drive, pasta Clea_Prontuario_IA — leia primeiro
`00_PAINEL` e `00_FATOS_VERIFICADOS`. O portal do Wellmark não abre da nuvem.
