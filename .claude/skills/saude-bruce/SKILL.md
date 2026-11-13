---
name: saude-bruce
description: Agente de saúde do Bruce (separado do da mãe) — entra no MyChart DELE (UIHC), baixa o que é novo (resultados, notas, remédios, consultas, mensagens, documentos) para a pasta 06_SAUDE do Cérebro no Google Drive, atualiza a ficha de fatos e avisa só o que importa. Use quando o Bruce pedir "baixa meu MyChart", "atualiza minha saúde", "/saude-bruce tudo" (download completo) ou quando o trigger agendado disparar.
---

# saude-bruce — o MyChart do Bruce no Drive

Responda em português, em tópicos com emoji e números; o que o Bruce vai dizer
ou escrever vai em inglês simples, com tradução. Nenhum dado de saúde entra
neste repositório: o lugar é o Drive. Nunca misture com a Clea: nada do Bruce
vai para a pasta dela, e esta skill não troca de pessoa no MyChart.

## Onde fica cada coisa

Drive → `00_CEREBRO_BRUCE` → `06_SAUDE 🩺 (privado)`. Ache pelo título
(`search_files`); se faltar algo, crie.

| Pasta / doc | O quê |
|---|---|
| `00_FICHA_SAUDE_BRUCE` (Doc) | Fatos verificados, com fonte e data. Fonte única de verdade. |
| `01_CONSULTAS_E_DECISOES` | Roteiros (`/consulta`), resumos de consulta, decisões. |
| `02_EXAMES_E_RESULTADOS` | Resultados em texto + planilha `exames.csv`. |
| `04_MYCHART_DOWNLOADS (bruto)` | Exportações do MyChart como vieram (PDF, XML C-CDA). |
| `09_INBOX` | O Bruce joga fotos, PDFs e áudios aqui. |

## Passo 0 — Login no MyChart do Bruce

- Credenciais: `MYCHART_BRUCE_USER` / `MYCHART_BRUCE_PASS`. Confira só os
  nomes (`[ -n "${MYCHART_BRUCE_USER:-}" ]`); nunca imprima valores nem peça
  senha no chat. Se faltarem: explique em 3 linhas como criá-las (menu do
  ambiente → Edit → Environment variables; uma sessão nova as enxerga) e siga
  com Gmail e Drive.
- `MYCHART_EU_*` guarda hoje o login da Clea: não use para o Bruce.
- Dependências: `python3 -m pip install -q -r agent/requirements.txt` se
  `import playwright` falhar (não rode `playwright install`).
- Explorador em background:
  `setsid -f nohup python3 agent/mychart_explorer.py --out <scratchpad>/mychart_bruce --port 8765 >/dev/null 2>&1`
  e o login do cabeçalho de `agent/mychart_explorer.py`, com
  `var=MYCHART_BRUCE_USER` / `var=MYCHART_BRUCE_PASS`.
- Código MFA: anote a hora antes de pedir o código; use o e-mail
  "Verification Code" do Gmail posterior a ela e com "Hello Bruce" (os da Clea
  chegam na mesma caixa). Não chegou em 3 min: peça ao Bruce só o código.
- Antes de baixar, confirme "Welcome, Bruce!" na tela inicial. Outro nome:
  pare e avise.

## Passo 1 — O que baixar

Marcador: `last_sync=<RFC3339>` na descrição da pasta `06_SAUDE`. Sem marcador
ou com o argumento `tudo`: baixe tudo; senão, só o posterior ao marcador.

1. **Resumo de saúde** (Health Summary): problemas, remédios (nome, dose,
   quem receitou, data), alergias, vacinas, histórico.
2. **Test Results**: cada resultado com valor, unidade, referência,
   alterado?, data da coleta e quem pediu → linhas em `exames.csv`
   (`data,exame,valor,unidade,referencia,alterado,fonte`). Laudos de imagem:
   texto integral.
3. **Visits**: passadas com notas (`/note_text` na página da visita) e
   futuras (data, chegada, especialidade, profissional, local, telefone).
4. **Messages**: conversas com a equipe, só leitura.
5. **Document Center**: cartas e After Visit Summaries; exportação de
   registros por faixa de datas (até 50 visitas por pedido; ver cabeçalho do
   explorador) → `04_MYCHART_DOWNLOADS`; depois
   `python3 agent/ccda_extract.py` para um texto por atendimento.
6. **Billing**: saldo e contas novas (só o resumo).

Baixe primeiro para uma pasta nova no scratchpad e leia arquivos baixados com
`python3 -I`. Suba ao Drive com `create_file` (PDF com
`disableConversionToGoogleType`; texto longo vira Google Doc). `/quit` no fim.

## Passo 2 — Ficha (`00_FICHA_SAUDE_BRUCE`)

Crie se não existir. Blocos: identificação mínima (sem números de documento)
· problemas ativos · remédios atuais (lista ÚNICA; duplicata no MyChart →
"⚠️ conferir com o médico") · alergias · exames-chave com tendência ·
consultas futuras · pendências (pedidos de exame e encaminhamentos em aberto)
· NÃO CONFIRMADO (o que alguém disse e o registro não mostra). Toda linha com
fonte e data. Edite com `mcp__Google_Docs__update_doc`; não apague histórico,
marque "(substituído em DD/MM)".

## Passo 3 — Alertas (só o que importa)

- 🔴 resultado novo fora da referência, mensagem da equipe, consulta
  cancelada ou remarcada, pedido de exame aberto sem data marcada.
- Remédios: duplicata, interação ou efeito colateral vira **pergunta para o
  médico**, nunca conselho para parar ou mudar dose (benzodiazepínico parado
  de repente pode dar convulsão).
- Se o registro ou o Bruce mencionar risco de se machucar: inclua sempre o
  988 (ligação ou texto, 24 h) e o GuideLink Center (Iowa City, 24 h).

## Passo 4 — Agenda

Consultas novas ou alteradas: mesma lógica da `check-medico` (etiqueta
`[Eu]`, colorId 9, privado, lembretes de 1440 e 120 min, sem duplicar).

## Passo 5 — Fechar

- `update_file` na pasta `06_SAUDE`: descrição com `last_sync=<agora>`.
- Resposta em até 8 linhas: 🔴 atenção · 🟢 novidades (com fonte) · ❓
  perguntar ao médico (inglês simples) · ✅ fazer · 📎 links.
- Ofereça o "RESUMO PARA O CÉREBRO" (modelo no `00_LEIA_PRIMEIRO`) para a
  `00_CAIXA_DAS_IAs`.
