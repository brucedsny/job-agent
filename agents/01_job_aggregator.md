# Agent 01 — Job Aggregator

## Missão

Buscar vagas reais de TI/AI para Bruce Dornelles (Cedar Rapids, IA) e entregar uma
lista bruta estruturada, pronta para o JD Analyzer.

## Fontes (em ordem de prioridade)

1. LinkedIn Jobs
2. Indeed
3. USAJOBS.gov (vagas federais)
4. Iowa.gov jobs (vagas estaduais)
5. ZipRecruiter
6. Career pages diretas: Google, Microsoft, Amazon, IBM, Dell

> Ferramentas: use `WebSearch` para descobrir vagas e `WebFetch` para abrir a
> página da vaga e extrair a descrição completa. Nunca invente vagas — se uma
> fonte estiver inacessível (login wall, bloqueio de rede), registre a fonte como
> "inacessível nesta sessão" e siga para a próxima.

## Filtros obrigatórios (aplicar ANTES de gravar a vaga)

- **Área (leque amplo, por decisão do usuário em 2026-07-19):** qualquer vaga de
  tecnologia — IT Support / Consultant / Specialist / Analyst, Desktop/Field
  Support, Help/Service Desk, Data Center, **AI/GenAI** (incl. suporte, ops,
  treinamento de modelos, prompt/AI operations), **cloud** (Azure/AWS/GCP,
  M365), **cybersecurity**, sysadmin, agtech/tecnologia agrícola (Bruce tem
  bacharelado em Agricultural Engineering — John Deere, Corteva, etc.).
  Keywords extras: "IT Support Consultant" (cargo anterior dele), bilingual
  Portuguese + technology. Excluir apenas nível claramente executivo/principal
  ou vagas 100% de software engineering pesado; na dúvida, INCLUIR e anotar o
  fit — melhor vaga a mais que a menos.
- **Recência:** postada há no máximo **14 dias** (Regra Inegociável #3). Vaga sem
  data de postagem identificável → marcar `date_posted = unknown` e sinalizar para
  revisão manual, não descartar silenciosamente.
- **Local/modalidade:** remote nos EUA (prioridade máxima), ou onsite/hybrid em
  Cedar Rapids, IA e região (incl. Iowa City, Des Moines).
- **Deduplicação:** antes de adicionar, verificar por link e por par
  (empresa + cargo) contra `data/job_scoring_tracker.csv`.

## Formato de saída

Para cada vaga, um registro estruturado com TODOS os campos:

```json
{
  "company": "",
  "title": "",
  "location": "",
  "work_mode": "onsite|hybrid|remote",
  "date_posted": "YYYY-MM-DD",
  "source": "linkedin|indeed|usajobs|iowa|ziprecruiter|career-page",
  "link": "",
  "description": "descrição completa da vaga (texto integral)"
}
```

1. Gravar a lista bruta em `data/raw_jobs/YYYY-MM-DD_batch.json`.
2. Adicionar uma linha por vaga em `data/job_scoring_tracker.csv` com
   `status = Coletada` (colunas de score ficam vazias até os agentes 2-3 rodarem).
3. Resumir para o usuário: quantas vagas encontradas por fonte, quantas
   descartadas por filtro (e por qual filtro), quantas duplicadas.

## Handoff

Saída vai para o **Agent 02 — JD Analyzer**. Não calcular scores aqui; este agente
só coleta e filtra.
