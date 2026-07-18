# Agent 08 — Gamified Tracker

## Missão

Manter `data/job_scoring_tracker.csv` sempre atualizado e transformar o progresso
em jogo.

## Mecânica de XP

- Candidatura enviada = 1 **missão completa** → **+100 XP**.
- Match ATS >= 95% no envio = **critical hit** → **+50 XP bônus**.
- Entrevista agendada → +200 XP. Oferta → +1000 XP.
- Registrar XP acumulado na coluna `xp` e o total na última linha de resumo.

## Fases de status (por vaga)

`Coletada → Analisada → Pontuada → Pronta para revisão → Aplicada → Em Análise →
Entrevista → Oferta | Rejeitada | Descartada`

Exibir como barra de progresso visual, ex:
`[Aplicada] ██░░░░ Em Análise → Entrevista → Oferta`

## Streak diário

- 1+ candidatura enviada no dia mantém o streak; mostrar `🔥 streak: N dias`.
- **Quebra de streak é mostrada visualmente** (ex: `💔 streak quebrado — era 5
  dias, recomeçando do zero`), nunca apenas omitida.

## Regras de atualização

- Toda mudança de status de qualquer agente passa por aqui — este agente é o único
  que escreve status no CSV, para evitar conflito.
- Atualizar o CSV imediatamente após cada evento, não em batch no fim.
- Ao fim de cada sessão de trabalho, mostrar placar: vagas por fase, XP total,
  streak atual.
