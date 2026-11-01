# job-agent

Repositório configurado para uso intensivo com **Claude Code** (CLI, web e GitHub Actions).

> O código do projeto ainda não foi criado. Este repositório já vem com a
> infraestrutura de automação do Claude (skills, hooks, permissões e workflows)
> pronta para quando o desenvolvimento começar.

## O que já está instalado

### 🤖 GitHub Actions (Claude na nuvem)
- **`.github/workflows/claude.yml`** — responde a `@claude` em issues, comentários
  de PR e reviews. Mencione `@claude` em qualquer issue/PR para acionar.
- **`.github/workflows/claude-code-review.yml`** — revisa automaticamente todo PR
  aberto/atualizado, postando comentários inline.

> **Requisito:** adicione o secret `ANTHROPIC_API_KEY` no repositório
> (Settings → Secrets and variables → Actions). Veja [Configuração](#configuração).

### 🧩 Skills (em `.claude/skills/`)
Comandos especializados invocáveis com `/<nome>` no Claude Code:

| Skill | O que faz |
|-------|-----------|
| `/pr-review` | Revisa o diff atual buscando bugs e melhorias, opcionalmente postando comentários no PR. |
| `/security-review` | Revisão de segurança das mudanças pendentes do branch. |
| `/commit-pr` | Cria um commit limpo e abre um PR seguindo as convenções do repo. |
| `/triage-issue` | Investiga uma issue do GitHub, classifica e propõe um plano de ação. |

### ⚙️ Configuração do Claude Code (em `.claude/`)
- **`settings.json`** — permissões pré-aprovadas (reduz prompts) e hook de
  `SessionStart`.
- **`hooks/session-start.sh`** — roda no início de cada sessão (incl. na web)
  para preparar o ambiente.

### 📋 `CLAUDE.md`
Guia de contexto carregado automaticamente pelo Claude em toda sessão.

## Configuração

1. **Secret da API** (para os GitHub Actions):
   ```
   Settings → Secrets and variables → Actions → New repository secret
   Nome: ANTHROPIC_API_KEY
   Valor: <sua chave da Anthropic>
   ```
2. **App do Claude no GitHub** (recomendado para os workflows interativos):
   instale via https://github.com/apps/claude para permitir que o Claude
   responda e abra PRs.

## Uso rápido

- Em uma issue: comente `@claude implemente X` → o workflow abre um PR.
- Em um PR: comente `@claude corrija o teste que falhou`.
- No Claude Code local/web: digite `/pr-review`, `/security-review`, etc.

---

## Job Search Agent (o código)

Sistema modular de 8 agentes para busca de emprego, com **humano no comando**:
o currículo é adaptado **só com fatos reais** do perfil-mestre, e **toda
candidatura exige aprovação humana (Gate B) — nunca há auto-apply**.
Arquitetura e políticas: [`README-PLANNING.md`](README-PLANNING.md).

### Instalação

```bash
pip install -e ".[dev]"            # + ".[pdf]" (WeasyPrint) e ".[browser]" (Playwright) se quiser
cp .env.example .env               # ANTHROPIC_API_KEY e fontes de vagas
job-agent init-profile             # edite data/profile/master.yaml com dados REAIS
```

### Uso

```bash
job-agent discover --greenhouse stripe --query python   # ou --url / --lever / --ashby / --all
job-agent run <job_id>              # extrai → rankeia → adapta CV → PDF → pacote; PARA no Gate B
job-agent autopilot --max 10        # prepara as de alto fit pela política (não envia)
job-agent review <job_id>           # preview do que será enviado
job-agent approve <job_id>          # aprovação humana (ou approve-all --yes)
job-agent submit <job_id>           # API ATS / e-mail; browser só com --consent (Gate C)
job-agent feedback <job_id> callback && job-agent rates   # aprendizado do funil
job-agent report                    # funil, custo por etapa, pendências
job-agent stop / resume             # kill-switch
```

| # | Agente | Modelo |
|---|--------|--------|
| 1 | Discovery (URL, Greenhouse, Lever, Ashby) | — |
| 2 | Extraction | Haiku → Sonnet |
| 3 | Fit Ranking (probabilidade real de entrevista) | Sonnet |
| 4 | Resume Tailor + guard anti-mentira | Opus |
| 5 | Document (PDF ATS-safe: WeasyPrint → Typst) | — |
| 6 | Assembly (pacote, cover letter, bloqueios) | Sonnet / Opus |
| 7 | Submission (API › e-mail › browser c/ Gate C) | — |
| 8 | CRM (SQLite: funil, custo, auditoria, outcomes) | — |

Testes: `pytest -q` (offline — sem rede nem API key).
