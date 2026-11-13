---
name: junta
description: Junta médica/jurídica do caso da mãe com a "junta da sabedoria". Use para análise, segunda opinião ou estratégia (alta, seguro, direitos, "o que eu digo") e, no modo rápido, antes de QUALQUER recomendação concreta sobre a mãe (comida, remédio, exame, atividade, visita, documento).
---

# junta — análise do caso, sempre a partir do Drive

Prompts, fatos e o portão de segurança vivem no Drive (CLAUDE.md). Nada de
alergias, remédios ou diagnósticos neste repositório.

## 0. Modos

| Chamada | O que faz |
|---|---|
| `/junta` ou `/junta medica` | Junta médica completa + junta médica da sabedoria |
| `/junta juridica` | Junta jurídica e social completa + junta jurídica da sabedoria |
| `/junta ambas` | As duas, com uma seção onde medicina e direito se cruzam |
| `/junta sabedoria <texto ou link>` | Só a crítica de uma resposta, plano, papel ou texto de outra IA |
| `/junta diabo <texto ou link>` | O mesmo que `/junta sabedoria` ("diabo" = nome antigo) |
| modo rápido (automático) | Pergunta pontual: `00_ESTADO_ATUAL` + portão + tema do `01_FATOS`; resposta curta |

## 1. Carregar (antes de responder)

1. `00_ESTADO_ATUAL` — o que vale agora.
2. `01_FATOS` — os temas da pergunta; `02_LINHA_DO_TEMPO` para sequência e datas.
3. O prompt do modo, em `70_Analises_juntas_e_outras_IAs` (ou na raiz):
   `00_PROMPT_JUNTA_MEDICA` (v4 ou mais nova) ou `00_PROMPT_JUNTA_JURIDICA`
   (v2 ou mais nova) — título com "USE ESTE" e a versão mais alta; ignore
   "ANTIGO". Se algo não abrir, diga qual e siga com o resto.
4. Faltou um fato → procure como na skill `mae` (seção 1, passo 5) antes de
   perguntar ao usuário.

## 2. Portão de segurança (obrigatório, inclusive no modo rápido)

Leia a seção "PORTÃO DE SEGURANÇA" do prompt (alergias, intolerâncias,
remédios e riscos médicos; ou riscos jurídicos e financeiros do usuário) e
confira no `01_FATOS` se algo mudou. Teste cada recomendação contra cada item,
inclusive o consentimento ou a concordância da paciente: nada de contenção nem
de sedação só para fazer exame. Portão não abriu → nenhuma recomendação
concreta; diga o que falta.

## 3. Responder

- Siga o prompt (papel, regras, composição, formato). O `01_FATOS` vence o
  retrato do prompt.
- Fato só com fonte (documento + data/hora, ou gravação + minuto); sem fonte →
  "não confirmado". O que o usuário ou outra IA disse só vira fato depois de
  bater com o registro.
- Procure contradições no próprio registro (nota editada depois de conflito,
  recomendações que mudam entre profissionais, plano de alta × recomendação
  médica): costumam ser as alavancas mais fortes.
- Evidência médica: diretrizes e revisões sistemáticas; cada citação conferida
  no PubMed (`mcp__PubMed__*`). Exame com interferentes (remédio, suplemento)
  → bula do exame e do remédio (ex.: DailyMed). Lei: cada uma conferida no
  texto oficial (vale no estado, em vigor neste ano); jurisprudência só se
  conferível. Não conferiu → [VER]. Número do caso nunca de memória.
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
- Tom de pedido, nunca de cobrança nem de ameaça (processo, imprensa): "I want
  to understand the plan." Lei na frente do médico só se o usuário pedir.
- MyChart: o usuário entra com o login da paciente. O que só se lê lá nunca é
  citado à equipe; pergunte primeiro e deixe a equipe contar.
- A voz da paciente primeiro: com capacidade de decisão, a decisão é dela; o
  procurador persuade. Intérprete profissional em conversas e consentimentos.
- Não gravar dentro do hospital. Nada é enviado sem "pode enviar".

## 5. Junta da sabedoria

- Modos completos: chame o subagente `junta-sabedoria` com o rascunho, o modo,
  o prazo do usuário (se houver) e os IDs de `00_ESTADO_ATUAL`, `01_FATOS`,
  `02_LINHA_DO_TEMPO` e do prompt — sem a sua conclusão. Aplique MANTER /
  AJUSTAR / RETIRAR; o usuário recebe só a versão final, com uma linha "O que
  a junta da sabedoria mudou".
- Prazo no mesmo dia (reunião, visita ou envio hoje): peça a resposta em ~10
  min, focada no papel ou na fala que vai sair; o resto fica para depois.
- Modo rápido: você mesmo checa o portão e as regras da seção 4 e faz uma
  autocrítica de 3 linhas (o que pode estar errado; o que mudaria a resposta).

## 6. Sair e fechar

- Texto que vai para fora → `/escrever`; folha para a equipe → `/visita` ou
  `/cardapio`.
- Papel para entregar à equipe: 1 página, inglês simples, sem números do
  prontuário; o português vai em página separada, só para o usuário.
- Documento longo → Doc em `70_Analises_juntas_e_outras_IAs`; no chat, resumo
  e link. Pesquisa longa na web → um prompt pronto para o Perplexity; a
  resposta volta pela `90_Entrada` e passa pelo `fact-checker`.
- Fatos novos → como na skill `mae`, seção 3. Retrato do prompt desatualizado
  em algo importante → avise em uma linha (nova versão; a antiga vira "ANTIGO").
- Resposta curta: cabe numa tela de celular.
