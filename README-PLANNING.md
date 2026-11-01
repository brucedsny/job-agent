# Job Search Agent — Plano de Arquitetura

Sistema modular de busca de emprego em Python, operado pelo Claude Code, com
**humano no comando** das decisões irreversíveis. Princípios não-negociáveis:

1. **Nunca mentir.** O currículo é adaptado, nunca inventado. Toda afirmação é
   rastreável a um fato no perfil-mestre (`data/profile/master.yaml`).
2. **API antes de browser.** Automação de navegador só sem API e com
   consentimento explícito por vaga (Gate C).
3. **Tudo auditável.** Cada ação é registrada no CRM local com custo.
4. **Aprovação humana antes de qualquer envio (Gate B).** Sempre. Nunca auto-apply.

## 1. Os 8 agentes

Módulos independentes com contratos Pydantic (`src/models.py`), comunicando-se por
artefatos persistidos no CRM — o pipeline é reentrante e testável. O
`Orchestrator` (`src/orchestrator.py`) é a cola, não um dos 8.

```
① Discovery → ② Extraction → ③ Fit Ranking → ④ Resume Tailor → ⑤ Document → ⑥ Assembly
                                                                              │ Gate B (humano)
                                                                              ▼
                       ⑧ CRM (escreve em todas as etapas)           ⑦ Submission (API › e-mail › browser)
```

| # | Agente | Responsabilidade | Modelo |
|---|--------|------------------|--------|
| ① | Discovery | URL manual, Greenhouse, Lever, Ashby; dedup por URL canônica + hash | — |
| ② | Extraction | Estrutura a JD (must vs nice, senioridade, salário) e detecta o modo de candidatura | Haiku → Sonnet se denso |
| ③ | Fit Ranking | Probabilidade **real** de entrevista + gaps + justificativa | Sonnet |
| ④ | Resume Tailor | Reordena/reformula fatos verídicos; guard determinístico + fact-check LLM | Opus |
| ⑤ | Document | PDF ATS-safe (1 coluna, sem tabela/imagem) + validador | — |
| ⑥ | Assembly | Pacote: PDF, screening, cover letter, checklist, bloqueios | Sonnet / Opus |
| ⑦ | Submission | Só após aprovação: API ATS › e-mail › browser (Gate C) › manual | — |
| ⑧ | CRM | SQLite: funil, artefatos, custos, auditoria, outcomes | — |

## 2. Fluxo ponta a ponta

```
[0] Perfil-mestre com fatos verificáveis
[1] Discovery → discovered
[2] Extraction → extracted
[3] Fit Ranking (+ ajuste do funil) → ranked | icebox
    Gate A (opcional): humano seleciona
[4] Tailor + guard → tailored        Gate D: revisar diff e claims sinalizados
[5] Document + validador ATS → document_ready
[6] Assembly → pending_approval
    ══ Gate B (obrigatório): humano aprova / edita / rejeita ══
[7] Submission → submitted | needs_manual | failed
[8] Feedback de resultados reais → aprendizado do funil
```

## 3. Human-in-the-loop

| Gate | Quando | Obrigatório? |
|------|--------|--------------|
| A — Seleção de vagas | após ranking | configurável |
| **B — Aprovação de candidatura** | antes de submeter | **sempre** |
| **C — Consentimento de browser** | antes de automação de navegador | **sempre** |
| D — Revisão do diff do CV | após tailoring | configurável |

Aprovar uma vaga não aprova outra. Drafts com pendências bloqueantes não podem
ser aprovados. `approve-all --yes` é uma ação humana em lote e só aprova drafts
limpos.

## 4. Segurança e consentimento

- Perfil, CRM e PDFs ficam locais e fora do git; segredos só via `.env`.
- Ao LLM vai só o necessário (perfil + JD da vaga).
- Browser: último recurso, respeita ToS, sem burlar captcha, não clica "enviar"
  por padrão (`browser_auto_submit=False`).
- Guard anti-mentira: números/métricas sem lastro e claims apontados pelo
  fact-checker bloqueiam o pacote.
- Kill-switch (`job-agent stop` ou `data/STOP`), teto de gasto por execução,
  caps de candidaturas por dia e por empresa.

## 5. Roadmap (implementado)

- **Fase 1 — MVP:** CRM, contratos, CLI, extraction/ranking/tailor/document/
  assembly, Gate B, submissão por e-mail.
- **Fase 2 — Automação forte:** Lever + Ashby, processamento em lote com teto de
  gasto, submissão via API do Greenhouse, browser atrás do Gate C, aprovação em
  lote, `report`.
- **Fase 3 — Elite:** motor de regras + `autopilot`, kill-switch, aprendizado do
  funil (ajusta só a priorização, nunca os fatos do CV), cover letters com guard,
  fallback de modelo, mapeamento de formulário por LLM.

**Sobre o "auto-apply" da Fase 3:** a regra "Gate B sempre obrigatório"
prevalece. O `autopilot` descobre, avalia pela política e **prepara**
candidaturas de alto fit, mas sempre para em `pending_approval`; o envio exige
aprovação humana explícita.
