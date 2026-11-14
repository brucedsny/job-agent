#!/usr/bin/env bash
# UserPromptSubmit hook — a cada mensagem, um lembrete curto das regras do caso
# da mãe. Não contém dados de paciente.
set -euo pipefail

prompt="$(jq -r '.prompt // ""' 2>/dev/null || true)"

# Chamada explícita de skill (/mae, /junta, /atualiza...): as regras já estão nela.
case "$prompt" in
  /*) exit 0 ;;
esac

read -r -d '' ctx <<'TXT' || true
[Só se for sobre a mãe] Recomendação concreta (comida, remédio, exame, atividade, documento) → /junta modo rápido antes.
Texto que sai → fact-checker; enviar só com "pode enviar". "atualiza"/"atualize" sozinho = /atualiza.
Estilo: responda só o que foi perguntado, sem lição de moral; falta fato → pergunte; seguro/dinheiro/família → 01_FATOS.
TXT

jq -n --arg c "$ctx" '{hookSpecificOutput: {hookEventName: "UserPromptSubmit", additionalContext: $c}}'
