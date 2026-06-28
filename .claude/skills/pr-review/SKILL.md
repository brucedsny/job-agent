---
name: pr-review
description: Revisa o diff atual (ou um PR informado) buscando bugs de correção e melhorias de simplificação/reuso/eficiência. Use ao revisar mudanças locais antes do push ou ao analisar um PR. Aceita --comment para postar achados como comentários inline no PR.
---

# PR Review

Revise as mudanças de código com foco em **bugs reais primeiro**, depois em
melhorias claras de qualidade.

## Passos

1. **Determine o alvo da revisão:**
   - Sem argumento: revise o diff do working tree (`git diff` + `git diff --staged`)
     ou o diff do branch contra a base (`git diff main...HEAD`).
   - Com número de PR (ex: `/pr-review 42`): use as ferramentas do GitHub MCP
     (`pull_request_read`) para obter o diff e o contexto.

2. **Procure, nesta ordem de prioridade:**
   - **Correção:** lógica errada, off-by-one, null/undefined, condições de corrida,
     casos de borda não tratados, erros silenciosamente engolidos.
   - **Segurança:** input não validado, injeção, secrets hard-coded, authz ausente.
   - **Qualidade:** duplicação que pode ser reusada, simplificações óbvias,
     ineficiências claras (N+1, trabalho redundante).

3. **Relate** cada achado com `arquivo:linha`, a severidade e uma correção
   concreta. Não invente problemas — se estiver bom, diga isso brevemente.

## Flags

- `--comment` — em vez de só relatar no chat, poste os achados como comentários
  inline no PR usando as ferramentas do GitHub MCP. Agrupe nitpicks e omita os
  de baixíssimo valor.

## Princípios

- Sinal sobre ruído: poucos achados de alta confiança valem mais que muitos
  incertos.
- Não reescreva o estilo do autor; aponte só o que importa.
