---
name: cruzamento
description: Cruzamento entre camadas do painel da mãe (remédios × comportamento × sinais × infecção × exames) numa janela de dias — padrões, gatilhos, o que acalma, exames vencidos e furos do registro, com perguntas em inglês. Use para "cruzamento", "cruza os dados", "padrões", antes de reunião com a equipe e na auditoria semanal.
---

# cruzamento — o que só aparece juntando as camadas

As regras de alerta do painel olham UMA linha de UMA aba. Esta skill olha as
abas juntas, numa janela de tempo: o que mudou junto, o que veio antes, o que
acalma, o que falta medir. Só lê o painel (o escritor único é o `/atualiza`).
Nenhum dado dela entra neste repositório.

## 1. Carregar (só leitura)

- `00_ESTADO_ATUAL` e a planilha `05_PAINEL_DA_…` (busca como no `/atualiza`,
  passo 6). Janela padrão: 14 dias; exames: a série inteira. Só linhas
  ativas (`status_registro` ≠ "superado").
- Abas: `Sinais`, `Remedios`, `Cognicao_Comportamento`, `Infeccoes`,
  `Graficos` (séries prontas dos exames), `Alertas`, `Perguntas` (abertas),
  `Hipoteses`, `Regras_alerta`.
- Diário da família (`60_Cuidados_diarios`, planilha `DIARIO_…`), se existir:
  eventos e sinais. Gravações [GRAV] são uso interno: nunca viram pergunta.

## 2. Linha do tempo única

Uma tabela: data_hora · camada · o quê · fonte (DOC / FAM / FAM-equipe). Hora
aproximada leva "~". Todos os padrões saem dela.

## 3. Padrões — teste cada um; "sem padrão" também é resultado

| # | Padrão | Dispara quando |
|---|---|---|
| P1 | Delirium sobreposto | em 72 h, 3+ de: flutuação no mesmo dia (bem ↔ agitada ou alucinando); sinal de infecção (sintoma, exame alterado, cultura sem resultado válido); temperatura que cumpre a regra de febre do painel; recusa de comida, líquido, remédio ou exame; pulso ≥ 100; remédio que age no cérebro iniciado, parado ou com dose mudada; exame vencido (P4) |
| P2 | Remédio → mudança | evento em `Remedios` (iniciado, parado, dose↑/↓, se precisar dado, injeção) seguido em até 72 h de mudança no comportamento ou nos sinais, para pior ou melhor. Remédio parado conta |
| P3 | Gatilhos e o que acalma | o que veio nas 2 h antes de cada episódio (celular ou visita retirados, coleta, procedimento, insistência, conflito) e antes de cada melhora (família, música, atividade, refeição em grupo). 2+ repetições = padrão |
| P4 | Exame vencido com risco | exame com valor alterado no histórico, sem resultado há mais de 5 dias de internação (30 em casa) e com sintoma novo que ele ajudaria a explicar |
| P5 | Hora do dia | 5+ episódios com hora: % na manhã (até 12h), tarde (12–18h), noite (após 18h); ≥ 60% numa faixa = padrão |
| P6 | Sono × dia seguinte | 5+ noites com `sono_h`: episódios depois de noites < 6 h × ≥ 6 h |
| P7 | Comida, líquido e peso | recusas, calorias, peso na mesma balança, pulso e pressão: falta de fome, desidratação ou protesto? |
| P8 | Furo do registro | fato em outra fonte (ESTADO, diário, nota) que não chegou ao painel, ou linha que cumpre uma regra de `Regras_alerta` sem alerta |

Os limiares de P4–P6 são desta skill, sem fonte clínica: ajuste se o caso
pedir. Para cada padrão: fatos com fonte → explicação possível [INF] →
confundidores (infecção, dor, sono, audição, ambiente) → evidência contra, e
se ela é mais velha que o padrão → força (forte: 3+ ocorrências sem
confundidor maior · fraco · sem padrão). Correlação não é causa: escreva
"aconteceram juntos", nunca "causou".

## 4. Etapa de verificação

- Pergunta não é recomendação. Sugestão concreta (horário de telefone, momento
  da coleta, como visitar) passa pelo modo rápido da `/junta` — 6 checagens +
  autocrítica de 3 linhas — escrito no próprio relatório.
- Citação clínica nova só conferida no PubMed, com DOI. Pergunta estratégica
  (alta, capacidade, tribunal) → "passar pela /junta ambas antes de usar".

## 5. Saída

Doc "Cruzamento AAAA-MM-DD — <janela>" em `70_Analises_juntas_e_outras_IAs`,
até 2 páginas, abrindo com 🔬 ou 🔎 e a linha de fontes:
1. 🔴 Padrões fortes (máx. 3): fatos · por que importa (fonte) · contra.
2. 🗣️ Perguntas para a equipe (máx. 6): inglês simples + tradução + para quem
   + prioridade; se já existe na aba `Perguntas`, complete a linha em vez de
   duplicar.
3. 🤝 Para a família: o que acalma × o que piora, em frases práticas.
4. ⚪ O que os dados NÃO mostram · ❓ dados que faltam.
5. 🛠️ Furos do registro (P8).
6. 🔎 Etapa de verificação · 📎 fontes.

## 6. Fechar

- RECADO na `90_Entrada` ("RECADO AAAA-MM-DD — Cruzamento") para o robô:
  linhas que faltam no painel (P8), perguntas novas e complementos, e
  hipóteses marcadas [INF]. O robô confere na fonte e grava.
- Chat: até 6 linhas + link do Doc.
- Quando rodar: antes de reunião com a equipe, de alta ou de troca de remédio,
  e uma vez por semana (auditoria de domingo).
