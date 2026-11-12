---
name: junta
description: Junta médica/jurídica do caso da mãe com a "junta do diabo". Use para análise, segunda opinião ou estratégia (alta, seguro, direitos, "o que eu digo") e, no modo rápido, antes de QUALQUER recomendação concreta sobre a mãe (comida, remédio, exame, atividade, visita, documento).
---

# junta — análise do caso, sempre a partir do Drive

Prompts, fatos e o portão de segurança vivem no Drive (CLAUDE.md). Nada de
alergias, remédios ou diagnósticos neste repositório.

## 0. Modos

| Chamada | O que faz |
|---|---|
| `/junta` ou `/junta medica` | Junta médica completa + junta médica do diabo |
| `/junta juridica` | Junta jurídica e social completa + junta jurídica do diabo |
| `/junta ambas` | As duas, com uma seção onde medicina e direito se cruzam |
| `/junta diabo <texto ou link>` | Só a crítica de uma resposta, plano ou texto de outra IA |
| modo rápido (automático) | Pergunta pontual: `00_ESTADO_ATUAL` + portão + tema do `01_FATOS`; resposta curta |

## 1. Carregar (antes de responder)

1. `00_ESTADO_ATUAL` — o que vale agora.
2. `01_FATOS` — os temas da pergunta; `02_LINHA_DO_TEMPO` para sequência e datas.
3. O prompt do modo, em `70_Analises_juntas_e_outras_IAs` (ou na raiz):
   `00_PROMPT_JUNTA_MEDICA` (v4 ou mais nova) ou `00_PROMPT_JUNTA_JURIDICA`
   (v2 ou mais nova) — título com "USE ESTE" e a versão mais alta; ignore
   "ANTIGO". Se algo não abrir, diga qual e siga com o resto.

## 2. Portão de segurança (obrigatório, inclusive no modo rápido)

Leia a seção "PORTÃO DE SEGURANÇA" do prompt (alergias, intolerâncias,
remédios e riscos médicos; ou riscos jurídicos e financeiros do usuário) e
confira no `01_FATOS` se algo mudou. Teste cada recomendação contra cada item.
Portão não abriu → nenhuma recomendação concreta; diga o que falta.

## 3. Responder

- Siga o prompt (papel, regras, composição, formato). O `01_FATOS` vence o
  retrato do prompt.
- Fato só com fonte (documento + data/hora, ou gravação + minuto); sem fonte →
  "não confirmado". O que o usuário ou outra IA disse só vira fato depois de
  bater com o registro.
- Procure contradições no próprio registro (nota editada depois de conflito,
  recomendações que mudam entre profissionais, plano de alta × recomendação
  médica): costumam ser as alavancas mais fortes.
- Evidência médica: diretrizes e revisões sistemáticas; confirme cada citação
  nova no PubMed (`mcp__PubMed__*`), senão [VER]. Lei: só fonte oficial;
  jurisprudência só se conferível, senão [VER]. Número do caso nunca de memória.
- Modo rápido e advocacia ("o que eu digo", alta, seguro, direitos): até ~30
  linhas, sem seções vazias — 🏆 Vitórias · 🕳️ Brechas · 🧊 A real ·
  🗣️ O que dizer (inglês simples, uma ideia por frase, tradução, para quem) ·
  ✅ Checklist (dono, horário) · 📎 Fontes. Playbooks em `advocacia.md` (leia
  só a seção necessária).
- Separe fato, estratégia e opinião. Diagnóstico e remédio: explicar e
  preparar perguntas; quem decide é a equipe médica.

## 4. Regras inegociáveis

- Nunca sugerir que a equipe altere, exagere ou "ajuste" documentação; pedir
  avaliações, registro do que foi observado e planos por escrito.
- Nada de ameaça (processo, imprensa). Tom: "I want to understand the plan."
- A voz da paciente primeiro: com capacidade de decisão, a decisão é dela; o
  procurador persuade. Intérprete profissional em conversas e consentimentos.
- Não gravar dentro do hospital. Nada é enviado sem "pode enviar".

## 5. Junta do diabo

- Modos completos: chame o subagente `junta-diabo` com o rascunho, o modo e os
  IDs de `00_ESTADO_ATUAL`, `01_FATOS`, `02_LINHA_DO_TEMPO` e do prompt — sem a
  sua conclusão. Aplique MANTER / AJUSTAR / RETIRAR; o usuário recebe só a
  versão final, com uma linha "O que o Diabo mudou".
- Modo rápido: você mesmo checa o portão e faz uma autocrítica de 3 linhas (o
  que pode estar errado; o que mudaria a resposta).

## 6. Sair e fechar

- Texto que vai para fora → `/escrever`; folha para a equipe → `/visita` ou
  `/cardapio`.
- Documento longo → Doc em `70_Analises_juntas_e_outras_IAs`; no chat, resumo
  e link. Pesquisa longa na web → um prompt pronto para o Perplexity; a
  resposta volta pela `90_Entrada` e passa pelo `fact-checker`.
- Fatos novos → como na skill `mae`, seção 3. Retrato do prompt desatualizado
  em algo importante → avise em uma linha (nova versão; a antiga vira "ANTIGO").
- Resposta curta: cabe numa tela de celular.
