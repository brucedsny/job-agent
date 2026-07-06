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
- `/pr-review` — revisão do diff atual (bugs + melhorias).
- `/security-review` — revisão de segurança das mudanças do branch.
- `/commit-pr` — commit limpo + abertura de PR.
- `/triage-issue` — investigação e triagem de uma issue.

## Comandos do projeto

```
# Instalar deps:  pip install -r agent/requirements.txt
# Rodar scraper:  python3 agent/mychart.py --account eu --out <dir>
# Rotina toda:    /check-medico
# Checar sintaxe: python3 -m py_compile agent/mychart.py
```
