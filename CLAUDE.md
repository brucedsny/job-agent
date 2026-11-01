# CLAUDE.md

Guia de contexto para o Claude Code neste repositório.

## Sobre o projeto

`job-agent` — Job Search Agent em Python 3.11 (8 agentes: discovery, extraction,
ranking, tailor, document, assembly, submission, CRM). Pacote em `src/`, CLI Typer
(`src/cli.py`), CRM em SQLite (`data/crm.sqlite`), LLM via Anthropic SDK
(`src/llm.py`). Arquitetura: `README-PLANNING.md`.

Regras invioláveis: o CV adaptado só usa fatos de `data/profile/master.yaml`
(guard anti-mentira em `src/agents/tailor.py`); **nunca** submeter sem aprovação
humana (Gate B, `GATE_B_ALWAYS_REQUIRED`); browser só com consentimento (Gate C).
Dados pessoais (`master.yaml`, `crm.sqlite`, PDFs) nunca vão para o git.

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

- `/pr-review` — revisão do diff atual (bugs + melhorias).
- `/security-review` — revisão de segurança das mudanças do branch.
- `/commit-pr` — commit limpo + abertura de PR.
- `/triage-issue` — investigação e triagem de uma issue.

## Comandos do projeto

```
# Instalar deps:  pip install -e ".[dev]"   (extras: pdf, browser)
# Rodar:          job-agent --help   (ou python -m src.cli)
# Testar:         pytest -q
# Lint:           (não configurado)
```
