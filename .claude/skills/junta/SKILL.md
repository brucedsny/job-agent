---
name: junta
description: Análise profunda do caso de saúde da família por uma "junta" — médica (todas as especialidades) ou jurídica/social (direitos no hospital, alta segura, seguro, imigração, moradia, procurações, Brasil). Carrega do Google Drive os prompts e a ficha de fatos antes de responder. Use quando o usuário disser "junta", pedir análise completa, segunda opinião, estratégia de alta/moradia/direitos, ou quando uma resposta exigir o caso inteiro.
---

# junta — análise do caso inteiro, sempre a partir do Drive

As instruções clínicas e jurídicas vivem no Drive do usuário, não neste
repositório. Nenhum dado de paciente entra aqui.

## 1. Carregar (sempre, antes de responder)

Com `search_files` + `read_file_content`, na pasta `Clea_Prontuario_IA`:

1. `00_PAINEL` — o que vale agora.
2. `00_FATOS_VERIFICADOS` — fatos com fonte. Leia o fim (adendos mais novos).
3. O prompt do modo pedido (título com "USE ESTE"):
   - médica (padrão): `00_PROMPT_JUNTA_MEDICA` v3 ou mais nova;
   - `juridica` / direitos / alta / moradia / seguro / imigração:
     `00_PROMPT_DIREITOS_ALTA_E_MORADIA`;
   - se a pergunta misturar os dois, carregue os dois.

Ignore títulos com "ANTIGO". Se algo não abrir, diga qual e siga com o resto.

## 2. Responder

- Siga o prompt carregado como instrução de formato e de regras.
- Se a ficha e o retrato do prompt divergirem, a ficha vence.
- Lei, dose, prazo ou número sem fonte confirmada: marque [VER], não afirme.
- Rascunho que vai sair (e-mail, carta, mensagem): passe pelo subagente
  `fact-checker` antes de mostrar como pronto. Nada é enviado sem
  "pode enviar".

## 3. Fechar

- Fatos novos que o usuário trouxe: acrescente ao fim do `00_FATOS_VERIFICADOS`
  (`update_doc`, `insertText` com `endOfSegmentLocation`), com etiqueta
  ([DOC]/[GRAV]/[FAM]) e data.
- Se o retrato do prompt ficou desatualizado em algo importante (internação,
  alta, remédio novo, decisão do seguro), avise em uma linha para atualizar o
  prompt.
- Resposta curta: cabe numa tela de celular; detalhes vão para o Drive.
