---
name: junta-medica
description: Atalho para a junta MÉDICA do caso da mãe (diagnóstico diferencial, exames, remédios, perguntas à equipe) com a junta do diabo. Igual a "/junta medica".
---

# junta-medica — atalho

Rode a skill `junta` no modo **médico** (`/junta medica`): carregue
`00_ESTADO_ATUAL`, os temas do `01_FATOS` e o prompt `00_PROMPT_JUNTA_MEDICA`
(versão "USE ESTE" mais alta) em `70_Analises_juntas_e_outras_IAs`; passe
pelo portão de segurança; rascunho → subagente `junta-diabo` → resposta.

Se o prompt do Drive não abrir, use este roteiro mínimo e diga que o prompt
não carregou:
1. Linha do tempo: função antes do declínio, internações, exames-chave,
   remédios iniciados e suspensos (com datas).
2. Piora nova logo depois de remédio novo = pergunta obrigatória à equipe.
3. Diagnóstico diferencial: a favor, contra e o exame que decide cada hipótese.
4. Remédios: Beers, interações, pressão, quedas, deglutição, sódio, rins;
   sensibilidade a antipsicóticos se Lewy for hipótese. Cite bula ou diretriz.
5. Até 6 perguntas para a equipe, em inglês curto com tradução.
6. FATO, INFERÊNCIA e OPINIÃO separados; nunca afirmar diagnóstico.
