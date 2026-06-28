---
name: security-review
description: Faz uma revisão de segurança das mudanças pendentes no branch atual. Use antes de abrir/mergear um PR ou quando o usuário pedir uma análise de segurança. Procura vulnerabilidades exploráveis, não estilo.
---

# Security Review

Avalie as mudanças pendentes do branch (`git diff main...HEAD`) sob a ótica de
um revisor de segurança.

## Categorias a verificar

- **Injeção:** SQL/NoSQL, comando de shell, template, LDAP — qualquer input
  concatenado em uma query/comando sem parametrização.
- **AuthN/AuthZ:** rotas/handlers sem checagem de autenticação ou autorização;
  escalonamento de privilégio; IDOR (acesso a recursos por ID sem checar dono).
- **Segredos:** chaves de API, tokens, senhas hard-coded ou logados.
- **Validação de input:** dados externos usados sem sanitização (path traversal,
  SSRF, XSS, deserialização insegura).
- **Cripto:** algoritmos fracos, IV/nonce reutilizado, randômico não seguro.
- **Dependências:** novas deps com vulnerabilidades conhecidas.

## Saída

Para cada achado, informe:
- **Severidade** (crítica / alta / média / baixa)
- **Local** (`arquivo:linha`)
- **Vetor de exploração** (como seria abusado)
- **Correção recomendada**

Se não houver problemas de segurança, diga isso de forma direta. Não relate
melhorias de estilo aqui — isso é trabalho do `/pr-review`.
