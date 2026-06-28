---
name: commit-pr
description: Cria um commit limpo com as mudanças atuais e abre um pull request seguindo as convenções do repositório. Use quando o usuário pedir para commitar e/ou abrir um PR.
---

# Commit & PR

Empacote o trabalho atual em um commit bem descrito e (se solicitado) abra um PR.

## Passos

1. **Inspecione** o estado: `git status` e `git diff` para entender o que mudou.
2. **Branch:** se estiver na branch padrão, crie uma branch de feature antes de
   commitar (`git checkout -b feat/<descrição-curta>`). Nunca commite direto na
   branch padrão sem permissão.
3. **Stage & commit:** agrupe mudanças relacionadas. Mensagem no imperativo,
   curta e descritiva (ex: `add job scraper for linkedin`). Não inclua
   identificadores de modelo na mensagem.
4. **Push:** `git push -u origin <branch>`. Em falha de rede, tente novamente com
   backoff (2s, 4s, 8s, 16s).
5. **PR (só se pedido):** use a ferramenta GitHub MCP `create_pull_request`.
   - Se houver template em `.github/pull_request_template.md`, preencha as seções
     dele a partir do diff.
   - Título conciso; corpo explica o "porquê" e resume as mudanças.

## Regras

- **Não** abra PR a menos que explicitamente solicitado.
- **Não** force push em branches compartilhadas.
- Confirme com o usuário antes de qualquer operação destrutiva.
