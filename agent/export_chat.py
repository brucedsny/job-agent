#!/usr/bin/env python3
"""Export chat history to clean Markdown and a SQLite database.

Sources it understands:
  * Claude Code session transcripts (~/.claude/projects/*/*.jsonl)
  * claude.ai data export (conversations.json, projects.json from
    Settings > Privacy > Export data)

Usage:
  python3 agent/export_chat.py --out DIR [--cap 6000] [SOURCE ...]

With no SOURCE it exports every Claude Code transcript on this machine.
For each conversation it writes two files in DIR/conversas:
  <name>_COMPLETA.md   dialogue + tool calls + tool results (each result capped)
  <name>_DIALOGO.md    only what the user and the assistant wrote
and appends every message to DIR/base.sqlite (table `mensagens`).
Thinking blocks and system reminders are dropped. Output can hold patient
data: keep it out of the repository.
"""
import argparse
import glob
import json
import os
import re
import sqlite3

REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)


def clean(text):
    return REMINDER.sub("", text or "").strip()


def flatten(content):
    if isinstance(content, str):
        return content
    parts = []
    for block in content or []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            parts.append(block.get("text", ""))
        elif block.get("type") == "tool_result":
            parts.append(flatten(block.get("content")))
    return "\n".join(parts)


def claude_code_rows(path):
    """Yield (timestamp, role, kind, text) from a Claude Code JSONL transcript."""
    seen = set()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("type") not in ("user", "assistant") or event.get("uuid") in seen:
                continue
            seen.add(event.get("uuid"))
            ts = (event.get("timestamp") or "")[:16].replace("T", " ")
            content = event.get("message", {}).get("content")
            if event["type"] == "user":
                is_result = isinstance(content, list) and any(
                    isinstance(b, dict) and b.get("type") == "tool_result" for b in content)
                text = clean(flatten(content))
                if not text or text.startswith("This session is being continued"):
                    continue
                yield ts, "user", "tool_result" if is_result else "text", text
            elif isinstance(content, list):
                for block in content:
                    if block.get("type") == "text" and block.get("text", "").strip():
                        yield ts, "assistant", "text", block["text"].strip()
                    elif block.get("type") == "tool_use":
                        args = json.dumps(block.get("input", {}), ensure_ascii=False)
                        yield ts, "assistant", "tool_use", f"{block.get('name')} {args}"


def claude_ai_conversations(path):
    """Yield (name, rows) for each conversation in a claude.ai export."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    for conv in data:
        rows = []
        for msg in conv.get("chat_messages", []):
            text = msg.get("text") or flatten(msg.get("content"))
            role = "user" if msg.get("sender") == "human" else "assistant"
            ts = (msg.get("created_at") or "")[:16].replace("T", " ")
            if text and text.strip():
                rows.append((ts, role, "text", text.strip()))
        name = conv.get("name") or conv.get("uuid", "conversa")
        yield name, rows


def claude_ai_projects(path):
    """Yield (name, rows) with each project's instructions and knowledge docs."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    for proj in data:
        rows = []
        if proj.get("prompt_template"):
            rows.append(("", "project", "instructions", proj["prompt_template"]))
        for doc in proj.get("docs", []):
            rows.append(((doc.get("created_at") or "")[:16], "project",
                         "doc:" + doc.get("filename", ""), doc.get("content", "")))
        yield "PROJETO_" + proj.get("name", proj.get("uuid", "")), rows


def slug(name):
    return re.sub(r"[^\w.-]+", "_", name, flags=re.U).strip("_")[:80] or "conversa"


def write(out, name, rows, cap, db):
    os.makedirs(os.path.join(out, "conversas"), exist_ok=True)
    full, dialog = [f"# {name}\n"], [f"# {name}\n"]
    for ts, role, kind, text in rows:
        db.execute("INSERT INTO mensagens VALUES (?,?,?,?,?)", (name, ts, role, kind, text))
        who = {"user": "🧑 USUÁRIO", "assistant": "🤖 IA", "project": "📁 PROJETO"}[role]
        if kind in ("text", "instructions") or kind.startswith("doc:"):
            label = f" ({kind})" if kind != "text" else ""
            block = f"\n---\n### {who}{label} — {ts}\n\n{text}\n"
            full.append(block)
            dialog.append(block)
        elif kind == "tool_use":
            full.append(f"`ferramenta: {text[:400]}`\n")
        else:
            shown = text if len(text) <= cap else text[:cap] + f"\n…[cortado: {len(text)} caracteres]"
            full.append(f"<details><summary>resultado</summary>\n\n```\n{shown}\n```\n</details>\n")
    base = os.path.join(out, "conversas", slug(name))
    with open(base + "_COMPLETA.md", "w", encoding="utf-8") as fh:
        fh.write("\n".join(full))
    with open(base + "_DIALOGO.md", "w", encoding="utf-8") as fh:
        fh.write("\n".join(dialog))
    return base


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cap", type=int, default=6000, help="max characters kept per tool result")
    ap.add_argument("sources", nargs="*")
    args = ap.parse_args()
    sources = args.sources or glob.glob(os.path.expanduser("~/.claude/projects/*/*.jsonl"))
    os.makedirs(args.out, exist_ok=True)
    db = sqlite3.connect(os.path.join(args.out, "base.sqlite"))
    db.execute("CREATE TABLE IF NOT EXISTS mensagens (conversa TEXT, quando TEXT, papel TEXT, tipo TEXT, texto TEXT)")
    for src in sources:
        name_hint = os.path.splitext(os.path.basename(src))[0]
        if src.endswith(".jsonl"):
            print(write(args.out, "claude_code_" + name_hint, list(claude_code_rows(src)), args.cap, db))
        elif os.path.basename(src) == "projects.json":
            for name, rows in claude_ai_projects(src):
                print(write(args.out, name, rows, args.cap, db))
        else:
            for name, rows in claude_ai_conversations(src):
                print(write(args.out, name, rows, args.cap, db))
    db.commit()
    db.close()


if __name__ == "__main__":
    main()
