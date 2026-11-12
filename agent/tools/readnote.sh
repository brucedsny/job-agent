#!/usr/bin/env bash
# Open one clinical note in the running MyChart explorer by the exact text of
# its "Signed ..." line, save the note text to OUT and go back to the list.
#
# Usage:  agent/tools/readnote.sh "Signed Jan 2, 2026, 9:15 AM" OUT.txt
# Needs agent/mychart_explorer.py running and logged in (PORT, default 8765),
# showing a visit's notes list (visits/past-details?csn=...&pageMode=notesfirst).
# OUT holds patient data: keep it in the scratchpad, never in the repository.
set -euo pipefail
[ $# -eq 2 ] || { echo "usage: $0 'Signed <date>' OUT.txt" >&2; exit 2; }
SIG="$1"; OUT="$2"; API="localhost:${PORT:-8765}"

SIG_JSON="$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$SIG")"
JS="(()=>{const s=${SIG_JSON};const els=[...document.querySelectorAll('*')].filter(e=>e.children.length===0&&(e.textContent||'').trim()===s);if(!els.length)return 'nf';let t=els[0];for(let i=0;i<6&&t;i++){if(t.tagName==='A'||t.tagName==='BUTTON'||(t.getAttribute&&t.getAttribute('role')==='button'))break;t=t.parentElement;}(t||els[0]).click();return 'ok '+(t?t.tagName:'')})()"
Q="$(python3 -c 'import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1]))' "$JS")"

reply="$(curl -s "$API/eval?js=$Q")"
case "$reply" in
  *'"value": "ok'*) ;;
  *) echo "note not opened: $reply" >&2; exit 1 ;;
esac
curl -s "$API/wait?ms=3500" >/dev/null
curl -s "$API/note_text" | python3 -c '
import json, sys
d = json.load(sys.stdin)
t = d.get("text") or json.dumps(d)
open(sys.argv[1], "w", encoding="utf-8").write(t)
print(len(t), "chars")' "$OUT"
curl -s "$API/back" >/dev/null
curl -s "$API/wait?ms=2500" >/dev/null
