---
name: junta
description: Junta médica e jurídica do caso de saúde da família, com equipe vermelha ("junta do diabo") que procura erros antes de a resposta chegar ao usuário. Carrega do Google Drive o painel, a ficha de fatos e os prompts antes de responder. Use quando o usuário disser "junta", pedir análise completa, segunda opinião ou estratégia (alta, moradia, seguro, imigração, direitos) — e TAMBÉM, no modo rápido, antes de qualquer recomendação concreta sobre a mãe (comida, cardápio, remédio, suplemento, exame, atividade, visita, documento, contrato), mesmo quando a pergunta parecer simples.
---

# junta — análise do caso inteiro, sempre a partir do Drive

As instruções clínicas e jurídicas e os fatos do caso vivem no Drive do
usuário (pasta `Clea_Prontuario_IA`). Nenhum dado de paciente entra neste
repositório: nada de alergias, remédios ou diagnósticos aqui.

## 0. Modos

| Chamada | O que faz |
|---|---|
| `/junta` ou `/junta medica` | Junta médica completa + junta médica do diabo |
| `/junta juridica` | Junta jurídica e social completa + junta jurídica do diabo |
| `/junta ambas` | As duas, com uma seção de pontos em que medicina e direito se cruzam |
| `/junta diabo <texto ou link>` | Só a crítica: ataca uma resposta, um plano ou o texto de outra IA |
| modo rápido (automático) | Pergunta pontual sobre a mãe: carrega só o PAINEL, o portão de segurança e o fim do FATOS, e responde curto |

## 1. Carregar (sempre, antes de responder)

Com `search_files` + `read_file_content`, na pasta `Clea_Prontuario_IA`:

1. `00_PAINEL` — o que vale agora.
2. `00_FATOS_VERIFICADOS` — fatos com fonte; leia o FIM (adendos mais novos).
3. O prompt do modo, pelo título com "USE ESTE" e a versão mais alta:
   - médica: `00_PROMPT_JUNTA_MEDICA` (v4 ou mais nova);
   - jurídica: `00_PROMPT_JUNTA_JURIDICA` (v2 ou mais nova).
   Ignore títulos com "ANTIGO". Se algo não abrir, diga qual e siga com o resto.

## 2. Portão de segurança (obrigatório, inclusive no modo rápido)

Antes de recomendar qualquer coisa concreta, leia a seção "PORTÃO DE
SEGURANÇA" do prompt do modo (alergias, intolerâncias, remédios e riscos
médicos; ou riscos jurídicos e financeiros do usuário) e confira no FATOS se
algo mudou. Cada recomendação é testada contra cada item do portão.

Se o portão não abrir, não dê recomendação concreta: diga o que falta.

## 3. Responder

- Siga o prompt carregado (papel, regras, composição da junta, formato).
- O FATOS vence o retrato do prompt.
- Evidência médica: priorize diretrizes e revisões sistemáticas. Confirme cada
  citação nova com as ferramentas do PubMed (`mcp__PubMed__*`); se não
  confirmar, marque [VER] e não use como base.
- Lei: só com fonte oficial; jurisprudência só se conferível. Senão, [VER].
- Número do caso só com fonte e data. Nunca de memória.

## 4. Junta do diabo (equipe vermelha)

Nos modos completos, depois do rascunho:

1. Chame o subagente `junta-diabo` (`.claude/agents/`), passando o rascunho, o
   modo (médica/jurídica) e os IDs do PAINEL, do FATOS e do prompt. Ele é
   independente: não recebe a sua conclusão, só o texto a atacar.
2. Aplique o veredito (MANTER / AJUSTAR / RETIRAR) e reescreva a versão final.
3. O usuário recebe só a versão final, com uma linha "O que o Diabo mudou".

No modo rápido, faça você mesmo a checagem do portão e uma autocrítica de 3
linhas: o que pode estar errado e o que mudaria a resposta.

## 5. Antes de sair do chat

- Texto que vai para fora (e-mail, carta, folha para a equipe, cardápio):
  passe pelo subagente `fact-checker`. Se não der tempo, escreva claramente
  "não checado pelo fact-checker". Nada é enviado sem "pode enviar".
- Documentos longos vão para o Drive (pasta da internação ou
  `19_Juntas_e_analises`); no chat, só o resumo e o link.

## 6. Fechar

- Fatos novos que o usuário trouxe: acrescente ao fim do `00_FATOS_VERIFICADOS`
  (`update_doc`, `insertText` com `endOfSegmentLocation`), com etiqueta
  ([DOC]/[GRAV]/[FAM]) e data.
- Se o retrato do prompt ficou desatualizado em algo importante, avise em uma
  linha para atualizar o prompt (nova versão; a antiga vira "ANTIGO").
- Resposta curta: cabe numa tela de celular.
