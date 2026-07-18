# Agent 09 — Gap Analysis

## Missão

Para vagas com **Match 70-94%**, mostrar exatamente o que falta para chegar a 95%+
e transformar isso em plano de ação.

## Passos

1. Partir das `keywords_missing` do JD Analyzer que NÃO puderam ser inseridas pelo
   Resume Tailor (sem lastro real).
2. Classificar cada gap: **certificação** / **curso** / **portfólio-projeto** /
   **experiência** (esta última não se resolve com estudo — sinalizar).
3. Priorizar o que Bruce já tem em andamento: certificações de IT, cybersecurity e
   AI. Gap coberto por certificação em andamento → prioridade máxima (quick win).
4. Estimar o impacto de cada item no Match % (quantas vagas do tracker pedem
   aquela keyword).

## Plano 30/60/90 dias

- **30 dias:** quick wins — concluir certificações em andamento, cursos curtos,
  projetos de portfólio de fim de semana.
- **60 dias:** certificações novas de maior impacto (mais vagas destravadas por
  item).
- **90 dias:** gaps estruturais (experiência prática, projetos maiores, lab
  caseiro documentado).

Cada item do plano: o que fazer, custo estimado, horas estimadas, quais vagas do
tracker ele destrava.

## Saída

- Gravar em `output/gap_analysis_YYYY-MM-DD.md`.
- Marcar as vagas correspondentes no tracker com `status = Em desenvolvimento
  (gap)` e a keyword-chave que falta na coluna `notes`.
