---
name: consulta
description: Prepara o Bruce para uma consulta dele e fecha depois. Antes — lê a agenda e o MyChart, chama a junta-bruce focada na especialidade e grava no Drive um roteiro PT+EN (pedidos principais, história em 5 frases, sintomas de 0 a 10, perguntas, página "For my provider"). Depois — lê o After Visit Summary, a gravação ou as fotos da 09_INBOX e atualiza a ficha, a agenda e as pendências. Use com "prepara minha consulta", "tenho médico hoje", "/consulta" ou "/consulta depois".
---

# consulta — antes e depois de cada consulta do Bruce

Português para explicar; inglês simples, uma ideia por frase, para o que ele
vai dizer. Dados de saúde só no Drive (`06_SAUDE 🩺 (privado)`).

## Antes (padrão)

1. **Qual consulta:** próximo evento médico do Bruce no Google Calendar e/ou
   e-mail "Check In For Your Upcoming Visit(s)" do MyChart (diz a hora de
   chegada). Anote especialidade, profissional, local e hora.
2. **Contexto:** `00_FICHA_SAUDE_BRUCE`, últimas notas dessa especialidade e
   pedidos em aberto. Se o MyChart do Bruce estiver acessível
   (`MYCHART_BRUCE_*`), leia antes: resultados recentes, lista de remédios,
   nota da última consulta (passos da skill `saude-bruce`).
3. **Como ele está hoje:** se não souber, uma pergunta curta (sintomas desde
   a última consulta). A resposta muda a prioridade.
4. **Junta:** siga a skill `junta-bruce` com foco na especialidade da
   consulta, mais o check-up que estiver faltando.
5. **Roteiro no Drive** (`01_CONSULTAS_E_DECISOES`, Google Doc a partir de
   HTML, título `🩺 AAAA-MM-DD — CONSULTA HHhMM — <especialidade> — Roteiro`):
   - ⏱️ em 30 segundos: 3–4 pedidos principais com a frase em inglês;
   - 🗣️ a história em 5 frases (EN + PT);
   - 📋 sintomas de 0 a 10 (tabela PT/EN);
   - 🔴 pedidos por prioridade · 🩸 exames numa coleta · prevenção e vacinas;
   - 💊 remédios a conferir · 💼 afastamento (o que documentar) · 💰 custo;
   - 🚨 sinais de alerta e 988 · ✅ checklist (check-in online, documento,
     cartão do seguro, frascos dos remédios, pedir para gravar, pedir o After
     Visit Summary);
   - 📄 "FOR MY PROVIDER" — 1 página em inglês para mostrar ao médico.
6. Resposta curta com o link. Se a consulta for hoje e houver visão dupla ou
   tontura, lembre de não dirigir.

## Depois (`/consulta depois`)

1. Fontes: After Visit Summary e nota no MyChart, gravação ou fotos na
   `09_INBOX` (áudio: `python3 agent/transcribe.py`).
2. Doc "Resumo — AAAA-MM-DD — <especialidade>" em `01_CONSULTAS_E_DECISOES`:
   o que o médico concluiu · exames pedidos (com data marcada?) ·
   encaminhamentos · mudanças de remédio · quando voltar · sinais de alerta
   ditos · citações-chave com minuto.
3. Atualize a `00_FICHA_SAUDE_BRUCE` (com fonte) e a agenda (exames e
   retornos; mesma lógica da `check-medico`, etiqueta `[Eu]`).
4. Pedido combinado que não apareceu no MyChart em 2 dias úteis → lembrete
   e frase pronta para mandar pelo MyChart (nada é enviado sem "pode enviar").
