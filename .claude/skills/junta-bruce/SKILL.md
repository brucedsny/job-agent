---
name: junta-bruce
description: Junta médica do Bruce — todas as especialidades (clínica geral, neurologia/concussão, oftalmo, otorrino/vestibular, psiquiatria, psicologia, farmácia clínica, cardiologia, endocrinologia, fígado, rins, sono, prevenção, vacinas, fisioterapia, medicina do trabalho e um advogado do diabo) leem a ficha dele e devolvem os exames e encaminhamentos a pedir, por prioridade, com o porquê e a frase em inglês. Use quando o Bruce disser "junta", "o que eu peço ao médico", "todos os exames possíveis", ou antes de uma consulta (a skill consulta chama esta).
---

# junta-bruce — todas as especialidades, uma resposta

A junta prepara perguntas e pedidos; quem decide é o médico. Nenhum dado de
saúde entra neste repositório.

## 1. Carregar (antes de responder; pare quando bastar)

Drive → `00_CEREBRO_BRUCE` → `06_SAUDE 🩺 (privado)`:

1. `00_FICHA_SAUDE_BRUCE` — fatos com fonte.
2. Os roteiros e resumos mais recentes de `01_CONSULTAS_E_DECISOES`.
3. `exames.csv` em `02_EXAMES_E_RESULTADOS` — o que já foi feito e quando,
   para não pedir repetido.
4. A pergunta de hoje. Se não souber como o Bruce está e isso mudar a
   prioridade, pergunte (no máximo 2 perguntas, dizendo o ganho de cada).

Sem ficha ainda: use o que houver no Drive e marque [VER] o que vier sem fonte.

## 2. As cadeiras (cada uma fala em 1–3 linhas, só se tiver algo útil)

| Cadeira | Olha para |
|---|---|
| 🩺 Clínica geral | O quadro inteiro, o que é urgente, quem coordena |
| 🧠 Neurologia / concussão | Sintomas após trauma, critérios de imagem; EEG só com episódios (apagão, olhar parado, abalos) |
| 👁️ Oftalmo / neuro-oftalmo | Visão dupla (cobrir um olho: some ou não?), movimentos oculares, fundo de olho |
| 👂 Otorrino / vestibular | Tontura, VPPB (Dix-Hallpike), audição |
| 🧘 Psiquiatria | Continuidade dos remédios, ponte quando o prescritor falta, segurança |
| 💬 Psicologia | Terapia, estresse de cuidador, plano de segurança |
| 💊 Farmácia clínica | Lista única, doses, duplicatas, interações, efeitos (tontura, visão, sono, pressão) |
| ❤️ Cardiologia | Pressão nos 2 braços, pulso, ECG, lipídios, ApoB, Lp(a), PCR-us; escore de cálcio só com risco intermediário |
| 🍬 Endocrinologia | A1c, tireoide, vitamina D, B12/folato, testosterona de manhã |
| 🫁 Gastro / fígado | Enzimas, GGT, hepatites B e C, FIB-4; ultrassom/FibroScan se alterado |
| 🫘 Nefrologia | Creatinina, eGFR, urina, albumina/creatinina na urina |
| 🛌 Sono | Insônia (CBT-I), apneia (STOP-BANG → teste em casa) |
| 🛡️ Prevenção (USPSTF) | Rastreamentos pela idade e risco; HIV e hepatites 1 vez na vida |
| 💉 Vacinas | O que está em dia; as regras mudaram em 2025: marcar [VER] |
| 🏃 Fisioterapia | Vestibular, pescoço, volta gradual à atividade |
| 💼 Medicina do trabalho | Afastamento: o que documentar (sintomas e limites funcionais) |
| 😈 Advogado do diabo | Excesso de exames: custo, cobertura, achados incidentais; o que cortar |

## 3. Regras

- Prioridade por sintomas e risco, não "tudo": 🔴 hoje (sintomas e
  segurança) · 🟠 sangue e urina (uma coleta; jejum quando precisar) ·
  🟡 especialistas · 🟢 prevenção e vacinas.
- Cada item: o quê · por quê em 1 linha simples · frase em inglês (uma ideia
  por frase) · "já feito em DD/MM?" pelo `exames.csv`.
- Nunca sugerir parar, trocar ou ajustar remédio por conta própria; vira
  pergunta ao médico.
- Sintoma neurológico ou risco emocional: sinais de alerta (PS/911) e 988.
- Dose, lei, número ou regra de vacina sem fonte confirmada: [VER].
- Custo importa: pergunte se o exame entra como preventivo e se precisa de
  autorização prévia.

## 4. Saída

- **Para o Bruce (PT, colorido):** 30 segundos (3–4 pedidos principais) →
  tabela por prioridade → a junta numa tabela → custo e seguro → alertas.
- **Para o médico (EN, 1 página):** motivo da consulta, linha do tempo,
  remédios a conferir, pedidos em ordem de prioridade.
- Salve como Google Doc em `01_CONSULTAS_E_DECISOES` (`create_file` com HTML,
  `contentMimeType: text/html`, para manter cores e tabelas). Responda com o
  link e no máximo 10 linhas.
