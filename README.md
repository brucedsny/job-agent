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
