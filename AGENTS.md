# AGENTS.md — for Codex and other non-Claude agents

This repository's operating rules live in `CLAUDE.md`. Read it first and follow it as if it were written for you.

- Skills in `.claude/skills/*/SKILL.md` are step-by-step procedures. Treat them as instructions, not code to run blindly.
- Review agents are in `.claude/agents/` (`fact-checker`, `junta-diabo`). Apply the same checks when you review.
- This repository is PUBLIC. Never commit personal data: names, dates of birth, record numbers, diagnoses, medications, addresses or IDs. Case data lives only in the owner's Google Drive.
- Never print or store passwords, verification codes or tokens. Secrets come only from `MYCHART_*` environment variables.
- Do not push to `main`, run the scrapers, or change scheduled jobs unless the owner explicitly asks.
- Nothing is sent to anyone (email, portal message, form) unless the owner writes "pode enviar".
