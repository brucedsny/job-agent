#!/usr/bin/env bash
# UserPromptSubmit hook — a cada mensagem do usuário, lembra o Claude de usar a
# junta (modo rápido) quando o assunto for a mãe. Não contém dados de paciente.
set -euo pipefail

prompt="$(jq -r '.prompt // ""' 2>/dev/null || true)"

# Mensagem que já chama uma skill explicitamente: não repetir o lembrete.
case "$prompt" in
  /junta*|/health-sync*|/health-advocate*|/check-medico*) exit 0 ;;
esac

read -r -d '' ctx <<'TXT' || true
[Lembrete automático — junta]
Se esta mensagem tratar da mãe do usuário (saúde, consulta, médico, remédio, comida/cardápio, exame, hospital, alta, cuidado, seguro, dinheiro, lei, imigração, moradia, documento ou contrato):
1. Antes de responder, use a skill `junta` no MODO RÁPIDO: 00_PAINEL + fim do 00_FATOS_VERIFICADOS + o portão de segurança do prompt certo (médico, jurídico ou os dois).
2. Antes de entregar, faça a autocrítica da "junta do diabo" em 3 linhas (fato errado? evidência fraca? risco de segurança?).
3. Junta COMPLETA, com o subagente `junta-diabo`, só para decisão grande ou quando o usuário pedir.
4. Texto que vai sair (e-mail, mensagem, carta) passa pelo `fact-checker`. Nada é enviado sem "pode enviar".
5. "Atualize"/"atualiza" sozinho = rodar a skill `health-sync`.
6. Estilo: responda direto ao que o Bruce perguntou; sem lições de moral nem avisos óbvios; se faltar um fato, PERGUNTE antes de supor; confira seguro, família e dinheiro na ficha antes de afirmar.
Se a mensagem não for sobre a mãe, ignore este lembrete.
TXT

jq -n --arg c "$ctx" '{hookSpecificOutput: {hookEventName: "UserPromptSubmit", additionalContext: $c}}'
