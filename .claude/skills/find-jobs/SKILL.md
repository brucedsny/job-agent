---
name: find-jobs
description: Roda o início do pipeline de busca de vagas (Job Aggregator → JD Analyzer → Qualitative Scoring) e apresenta o ranking do batch. Use quando o usuário pedir para buscar vagas, coletar vagas novas ou rodar o pipeline (ex: "/find-jobs" ou "busque vagas novas").
---

# Find Jobs — etapas 1-3 do pipeline

Execute em ordem fixa, seguindo as definições em `agents/`:

## 1. Coleta (Job Aggregator)

Lance o subagente `job-aggregator` (ou siga `agents/01_job_aggregator.md`
diretamente) para buscar, filtrar, deduplicar e gravar o batch do dia em
`data/raw_jobs/` + tracker.

## 2. Análise (JD Analyzer)

Para cada vaga coletada, siga `agents/02_jd_analyzer.md`: escolher resume-base
ativo, extrair keywords obrigatórias/desejáveis, calcular Match % e registrar as
keywords faltantes.

> Se os resumes em `data/` ainda forem `PLACEHOLDER`, pare aqui, mostre o
> resultado da coleta e peça ao usuário os resumes reais — não estime Match %
> sem ground truth.

## 3. Scoring (Qualitative Scoring)

Para vagas com Match >= 70%, siga `agents/03_qualitative_scoring.md`: notas de
Benefícios, Qualidade de Vida, Pressão e Cultura; Score Geral ponderado; Chance
de Contratação estimada.

## Saída para o usuário

- Ranking do batch por Score Geral (tabela: empresa, cargo, modalidade, Match %,
  Score Geral, Chance %).
- Vagas com Match 70-94% marcadas como elegíveis para `/gap` (Agent 09).
- Pergunta final: quais vagas avançar para o Resume Tailor (etapa 4)? Nenhuma
  candidatura avança sem escolha explícita do usuário.

Atualize `data/job_scoring_tracker.csv` a cada etapa (via regras do Agent 08).
