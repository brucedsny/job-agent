# CLAUDE.md

Guia de contexto para o Claude Code neste repositório.

## Sobre o projeto

`job-agent` — além da infraestrutura de automação do Claude Code (skills, hooks,
permissões e workflows do GitHub Actions), o repositório contém o **`site_copier`**:
um agente em Python (apenas stdlib) que copia todo o conteúdo de um site para
navegação offline. Documentação em `site_copier/README.md`.

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
# Instalar deps:  (nenhuma — usa só a stdlib do Python 3.8+)
# Rodar:          python -m site_copier <url> -o <dir>
# Testar:         python -m unittest discover -s tests
# Lint:           <TODO>
```
