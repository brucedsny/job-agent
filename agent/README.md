# Agente do caso da mãe — v2

Código usado pelas skills do Claude Code (`.claude/skills/`) para acompanhar o
caso de saúde da mãe do usuário. A memória do caso fica no Google Drive (ver
`CLAUDE.md`); **nenhum dado de paciente entra neste repositório**. Downloads,
textos extraídos e PDFs gerados ficam no scratchpad da sessão e vão para o Drive.

## O que mudou na v2

- Menos skills, mais afiadas: `/mae` (dia a dia e "salva"), `/atualiza`
  (substitui `health-sync` + `check-medico`), `/junta` (absorveu
  `health-advocate`), `/escrever`, `/visita`, `/cardapio`, `/privacidade`.
- Memória em documentos centrais no Drive: `00_ESTADO_ATUAL` (reescrito a cada
  atualização), `01_FATOS`, `02_LINHA_DO_TEMPO`, `03_CONTATOS`, `04_MAPA_DA_PASTA`.
- Nomes, contatos e números do caso saíram dos arquivos versionados.

## Peças

| Arquivo | Papel |
|---|---|
| `mychart.py` | Scraper Playwright das consultas: login em duas etapas, MFA por e-mail (o agente grava o código em `mfa_code.txt`), texto e screenshots da página Visits. |
| `mychart_explorer.py` | Navegador controlado por HTTP local para ler notas, resultados e mensagens e baixar registros; comandos e particularidades do portal no cabeçalho. |
| `ccda_extract.py` | Converte as exportações "Visit Records" (XML C-CDA) em um texto por atendimento + índice JSON. |
| `transcribe.py` | Transcreve áudio localmente (faster-whisper, instalado sob demanda) com minuto:segundo. |
| `export_chat.py` | Exporta conversas do Claude Code e do claude.ai (`conversations.json`, projetos) para Markdown + SQLite. |
| `tools/html2pdf.js` | HTML → PDF Letter (folhas de `/visita` e `/cardapio`, cartas). |
| `tools/readnote.sh` | Abre uma nota pelo texto "Signed …" no explorador e salva o texto. |
| `config.json` | Contas (`eu`, `mae`), etiquetas e cores da agenda, fuso. |

## Setup (uma vez)

1. **Credenciais do MyChart** nas variáveis de ambiente do ambiente do Claude
   Code: `MYCHART_EU_USER`/`MYCHART_EU_PASS` e, se houver,
   `MYCHART_MAE_USER`/`MYCHART_MAE_PASS`. Nunca commite valores (`.env` está
   no `.gitignore`). Com acesso proxy ao prontuário da mãe, aponte a conta
   `mae` do `config.json` para as suas variáveis e preencha `persona`.
2. **Rede:** o ambiente precisa alcançar `mychart.uihealthcare.org`.
3. **MFA por e-mail:** o código do MyChart deve chegar ao Gmail conectado ao
   Claude, para o agente ler sozinho.
4. **Agenda:** crie o calendário "Saúde" no Google Calendar (o conector não
   cria calendários); sem ele, a skill usa o principal, com etiqueta, cor e
   evento privado.

## Uso

- `/atualiza` (ou só "atualiza"): novidades do MyChart, Gmail e `90_Entrada`,
  agenda e resumo no Drive. Um agendamento pode disparar a mesma skill.
- Teste offline do scraper, sem credenciais nem rede:
  `python3 .claude/skills/run-agent/driver.py`.
- Folhas: `node agent/tools/html2pdf.js IN.html OUT.pdf 0.95`.

## Prontuário completo

O MyChart exporta no máximo 50 visitas por pedido: Document Center → *View,
Download, or Send Visit Records* → *Date Range*, em faixas de até 50 visitas →
*Download all* → *Request download*; os arquivos aparecem em *Requested
Records* e expiram em 7 dias. A cópia formal do prontuário (pedido ao HIM) é
um PDF único com as notas. Notas de uma internação em andamento não entram
nas exportações: leia-as com `/note_text` no explorador.

## Limitações

- Mudanças de layout do portal Epic podem quebrar o scraper; os dumps e
  screenshots existem para o agente se adaptar.
- CAPTCHA ou bloqueio de automação exigem intervenção manual.
- O portal do Wellmark não abre da nuvem.
