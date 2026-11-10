#!/usr/bin/env bash
# SessionStart hook — checagem rápida de privacidade. Não imprime dados pessoais:
# só avisa se o repositório está público ou se há padrões sensíveis nos arquivos.
set -uo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"

warn=()

# 1) Visibilidade do repositório no GitHub (API pública: privado responde 404).
url="$(git remote get-url origin 2>/dev/null || true)"
slug="$(printf '%s' "$url" | sed -E 's#(\.git)?$##; s#.*github\.com[:/]+##; s#.*/git/##' )"
if [ -n "$slug" ]; then
  vis="$(curl -s -m 8 "https://api.github.com/repos/${slug}" 2>/dev/null | jq -r '.visibility // empty' 2>/dev/null || true)"
  if [ "$vis" = "public" ]; then
    warn+=("O repositório ${slug} está PÚBLICO no GitHub. Peça ao usuário para torná-lo privado (Settings → General → Danger Zone → Change visibility).")
  fi
fi

# 2) Padrões sensíveis nos arquivos versionados (SSN, CPF, data de nascimento antiga).
hits="$(git ls-files -z 2>/dev/null | xargs -0 grep -IlE '\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b|\b[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2}\b|\b[01][0-9]/[0-3][0-9]/19[0-9]{2}\b' 2>/dev/null | head -5 | tr '\n' ' ')"
if [ -n "$hits" ]; then
  warn+=("Possível dado pessoal (SSN, CPF ou data de nascimento) nestes arquivos: ${hits}— revisar antes de qualquer commit.")
fi

if [ ${#warn[@]} -gt 0 ]; then
  echo "⚠️ PRIVACIDADE — avise o usuário na PRIMEIRA linha da próxima resposta:"
  for w in "${warn[@]}"; do echo "- $w"; done
else
  echo "🔒 Privacidade: repositório privado e nenhum padrão sensível encontrado."
fi
exit 0
