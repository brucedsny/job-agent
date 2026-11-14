---
name: escrever
description: E-mail, carta ou mensagem do MyChart sobre o caso da mãe — rascunho → fact-checker → envio só após "pode enviar" → registro no 01_FATOS. Use para escrever, responder ou mandar texto para fora.
---

# escrever — rascunho, checagem, "pode enviar", registro

## 1. Contexto
- `00_ESTADO_ATUAL`, o tema do `01_FATOS` e o `03_CONTATOS` (nomes e
  endereços confirmados, assinatura e papel do usuário).
- Resposta a e-mail: leia o thread inteiro (`get_thread`) — quem escreveu, o
  que pediu, prazo.

## 2. Rascunho
- Para equipe, seguro ou tribunal: inglês simples, frases curtas, uma ideia
  por frase; educado e factual; fatos com data; pedido claro, com resposta por
  escrito e prazo. Nada de ameaça; nunca pedir que alguém altere documentação.
- Embaixo, só para o usuário: tradução curta em português.
- Recomendação concreta sobre a mãe no texto → `/junta` no modo rápido antes.
- Só o dado de saúde necessário. Nunca números de documento, senhas ou códigos.

## 3. Checar
Subagente `fact-checker` com o rascunho e os IDs dos documentos centrais;
corrija o que vier ❌ ou 🔶. Sem tempo → escreva no topo "não checado pelo
fact-checker".

## 4. Mostrar e esperar
Mostre: canal, Para/Cc, assunto, texto final e o veredito em uma linha. Envie
só depois de o usuário escrever "pode enviar". Mudou algo → mostre de novo.

## 5. Enviar
- Resposta: `mcp__Gmail__reply` no MESMO thread, aos mesmos destinatários,
  salvo pedido.
- E-mail novo: `mcp__Gmail__send_message` só para endereço confirmado no
  `03_CONTATOS` ou no próprio thread. Nunca adivinhe endereço; na dúvida,
  pergunte.
- MyChart: pelo explorador (Messages → nova mensagem); antes de clicar em Send,
  `/shot` e confira destinatário e texto. Ou entregue o texto para o usuário
  colar.
- Carta: HTML → `node agent/tools/html2pdf.js IN.html OUT.pdf 0.95` → PDF na
  pasta do tema no Drive; o usuário imprime e assina.

## 6. Registrar
- `01_FATOS`, no tema certo: `AAAA-MM-DD HH:MM — enviado a <quem> (<canal>):
  <assunto>; pedido: <o quê>; prazo: <data> [EMAIL enviado <data>]`.
- Evento na `02_LINHA_DO_TEMPO`; contato novo no `03_CONTATOS`.
- Resposta com prazo → lembrete de dia inteiro na agenda (colorId 5, privado).
