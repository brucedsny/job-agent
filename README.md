# job-agent — Job Search Automation Agent

Sistema multi-agente em **Claude Code** para busca, qualificação, personalização
e candidatura a vagas de TI/AI (Bruce Dornelles, Cedar Rapids, IA).

O cérebro do sistema é o [`CLAUDE.md`](CLAUDE.md) — regras inegociáveis, arquivos
de verdade e o pipeline de 9 agentes. As definições detalhadas de cada agente
estão em [`agents/`](agents/).

## Estrutura

```
job-agent/
├── CLAUDE.md                          <- cérebro do sistema, lido em toda sessão
├── agents/                            <- definição de cada sub-agente (pipeline 1-9)
│   ├── 01_job_aggregator.md
│   ├── 02_jd_analyzer.md
│   ├── 03_qualitative_scoring.md
│   ├── 04_resume_tailor.md
│   ├── 05_cover_letter_generator.md
│   ├── 06_match_humanity_score.md
│   ├── 07_human_checkpoint.md
│   ├── 08_gamified_tracker.md
│   └── 09_gap_analysis.md
├── data/
│   ├── job_scoring_tracker.csv        <- planilha viva, os agentes atualizam
│   ├── raw_jobs/                      <- batches brutos de vagas coletadas
│   ├── resume_master_it_support.txt   <- ⚠️ PLACEHOLDER: substituir pelo real
│   └── resume_master_data_center.txt  <- ⚠️ PLACEHOLDER: substituir pelo real
├── templates/
│   └── cover_letter_template.txt      <- esqueleto da carta (Agent 05)
├── output/                            <- resumes/cartas gerados (fora do git)
└── .claude/
    ├── agents/job-aggregator.md       <- subagente invocável do Agent 01
    └── skills/                        <- /find-jobs, /pr-review, etc.
```

## Como usar

1. **Substitua os placeholders** em `data/resume_master_*.txt` pelo conteúdo dos
   seus resumes reais (e, se quiser, `templates/cover_letter_template.txt` pelo
   seu template). Sem isso, só a coleta de vagas (etapas 1-3 parciais) funciona —
   o sistema nunca inventa experiência.
2. No Claude Code, rode **`/find-jobs`** — coleta (Job Aggregator), análise de JD
   e scoring qualitativo, terminando num ranking do batch.
3. Escolha as vagas para avançar: Resume Tailor → Cover Letter → gate de
   qualidade (Match >= 95% e detecção de IA <= 10%) → **checkpoint humano**.
   Nada é enviado sem seu "aprovado" explícito.
4. Vagas com Match 70-94% ganham um plano de 30/60/90 dias via Gap Analysis.

## Regras que o sistema sempre segue

- Nunca envia candidatura sem aprovação explícita do usuário.
- Nunca inventa experiência ou certificação fora dos arquivos de verdade.
- Descarta vagas com mais de 14 dias de postagem.
- Só libera envio com Match ATS >= 95% e detecção de IA <= 10%.
- Atualiza `data/job_scoring_tracker.csv` automaticamente.

## Limitações importantes

- Busca de vagas reais exige acesso à internet autorizado na sessão.
- Envio automático em portais fechados (LinkedIn Easy Apply, Workday) exige
  automação de navegador (Playwright) configurada à parte — o Claude Code guia a
  configuração quando necessário.
- Vagas federais (USAJOBS) usam resume em formato federal (OPM), gerado pelo
  Resume Tailor quando aplicável.

## Infraestrutura Claude Code do repositório

- **GitHub Actions:** `@claude` em issues/PRs (`.github/workflows/claude.yml`) e
  review automático de PRs (`claude-code-review.yml`). Requer o secret
  `ANTHROPIC_API_KEY`.
- **Skills:** `/find-jobs`, `/pr-review`, `/security-review`, `/commit-pr`,
  `/triage-issue` (em `.claude/skills/`).
- **Configuração:** `.claude/settings.json` (permissões + hook de SessionStart).
