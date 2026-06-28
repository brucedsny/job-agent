# CLAUDE.md

Guia de contexto para o Claude Code neste repositório.

## Sobre o projeto

`job-agent` — repositório em estágio inicial. O código do projeto ainda não foi
criado; por enquanto o repositório contém apenas a infraestrutura de automação do
Claude Code (skills, hooks, permissões e workflows do GitHub Actions).

Quando o projeto for definido, atualize esta seção com: linguagem/stack, como
rodar, como testar e como fazer lint.

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

> Preencher quando o projeto tiver código.

```
# Instalar deps:  <TODO>
# Rodar:          <TODO>
# Testar:         <TODO>
# Lint:           <TODO>
```
