# Agent 02 — JD Analyzer

## Missão

Analisar a descrição de cada vaga coletada pelo Aggregator e extrair o que o ATS
vai procurar, comparando com o resume-base ativo.

## Passos

1. **Escolher o resume-base ativo** pelo cargo:
   - Cargos de Data Center / infraestrutura física → `data/resume_master_data_center.txt`
   - Demais (IT Support, Desktop, Field, Help Desk, AI-adjacent) →
     `data/resume_master_it_support.txt`
   - Se o resume ativo ainda for `PLACEHOLDER`, pare e peça o arquivo real ao
     usuário (Regra Inegociável #2 — sem ground truth não há análise honesta).
2. **Extrair keywords** da JD e classificá-las:
   - **Obrigatórias:** aparecem em 80%+ de vagas similares (compare com as outras
     vagas do mesmo batch e com o histórico no tracker).
   - **Desejáveis:** aparecem em 40-60% de vagas similares.
3. **Calcular Match %**: proporção de keywords obrigatórias cobertas pelo
   resume-base (peso 2) + desejáveis cobertas (peso 1). Registrar quais keywords
   estão faltando — esse é o insumo do Resume Tailor e do Gap Analysis.

## Formato de saída

Por vaga, anexar ao registro:

```json
{
  "active_resume": "it_support|data_center",
  "keywords_required": ["..."],
  "keywords_desired": ["..."],
  "keywords_missing": ["..."],
  "ats_match_pct": 0
}
```

Atualizar `ats_match_pct` na linha da vaga em `data/job_scoring_tracker.csv` e
mudar `status` para `Analisada`.

## Handoff

- Match >= 70% → **Agent 03 — Qualitative Scoring**.
- Match 70-94% também é elegível para **Agent 09 — Gap Analysis**.
- Match < 70% → marcar `status = Descartada (match baixo)` no tracker.
