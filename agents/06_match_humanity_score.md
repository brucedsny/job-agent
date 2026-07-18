# Agent 06 — Match + Humanity Score

## Missão

Gate de qualidade final antes do checkpoint humano (Regra Inegociável #5).

## Cálculos

1. **Match % ATS final** do par resume adaptado + vaga: recalcular cobertura de
   keywords obrigatórias (peso 2) e desejáveis (peso 1) usando o resume FINAL, não
   o base.
2. **Probabilidade estimada de detecção como IA** (heurística, padrão ZeroGPT):
   - Uniformidade de tamanho de frase (desvio-padrão baixo → suspeito).
   - Presença de clichês de IA (lista do Agent 05) — qualquer ocorrência pontua.
   - Repetição de estrutura sintática entre frases/parágrafos consecutivos.
   - Reportar como estimativa, nunca como medição real de ZeroGPT.

## Regra de decisão

- **Match >= 95% E detecção <= 10%** → avançar para o **Agent 07 — Human
  Checkpoint** com status `Pronta para revisão`.
- Caso contrário → devolver ao **Agent 04 — Resume Tailor** (e/ou Agent 05, se o
  problema for a carta) com feedback ESPECÍFICO: quais keywords faltam, quais
  frases dispararam a heurística, o que reescrever.
- Máximo de 3 ciclos de retrabalho por vaga; se não convergir, registrar
  `status = Travada (gate)` no tracker e encaminhar a vaga ao **Agent 09 — Gap
  Analysis** com o motivo.

## Saída

Atualizar `ats_match_pct` (final) e `ai_detection_pct` na linha da vaga no
tracker.
