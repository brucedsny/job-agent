#!/usr/bin/env bash
# SessionStart hook — roda no início de cada sessão do Claude Code (inclusive na web).
# Prepara o ambiente para que testes/linters possam rodar durante a sessão.
#
# Como o projeto ainda não tem código, este hook apenas detecta a stack quando
# ela existir e instala dependências. Mantenha-o idempotente e silencioso em
# caso de "nada a fazer".
set -euo pipefail

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"

# Node / TypeScript
if [ -f package.json ]; then
  if [ -f package-lock.json ]; then
    npm ci --no-audit --no-fund >/dev/null 2>&1 || npm install --no-audit --no-fund >/dev/null 2>&1 || true
  else
    npm install --no-audit --no-fund >/dev/null 2>&1 || true
  fi
fi

# Python
if [ -f requirements.txt ]; then
  pip install -q -r requirements.txt >/dev/null 2>&1 || true
elif [ -f pyproject.toml ]; then
  pip install -q -e . >/dev/null 2>&1 || true
fi

echo "✅ Ambiente do job-agent pronto."
