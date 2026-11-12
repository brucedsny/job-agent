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


def claude_ai_message_rows(msg):
    """Rows for one claude.ai message: text, tool calls/results, attachments."""
    role = "user" if msg.get("sender") == "human" else "assistant"
    ts = (msg.get("created_at") or "")[:16].replace("T", " ")
    rows = []
    for att in msg.get("attachments") or []:
        body = att.get("extracted_content") or ""
        if body.strip():
            rows.append((ts, role, "anexo", f"[{att.get('file_name', 'anexo')}]\n{body.strip()}"))
    blocks = msg.get("content") or []
    for block in blocks:
        kind = block.get("type")
        if kind == "text" and (block.get("text") or "").strip():
            rows.append((ts, role, "text", block["text"].strip()))
        elif kind == "tool_use":
            args = json.dumps(block.get("input", {}), ensure_ascii=False)
            rows.append((ts, role, "tool_use", f"{block.get('name')} {args}"))
        elif kind == "tool_result":
            text = flatten(block.get("content"))
            if text.strip():
                rows.append((ts, role, "tool_result", text.strip()))
    if not any(r[2] == "text" for r in rows) and (msg.get("text") or "").strip():
        rows.append((ts, role, "text", msg["text"].strip()))
    return rows


def claude_ai_conversations(path, only=None):
    """Yield (name, rows) for each conversation in a claude.ai export."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    for conv in data:
        if only and not any(conv.get("uuid", "").startswith(p) for p in only):
            continue
        rows = []
        for msg in conv.get("chat_messages", []):
            rows.extend(claude_ai_message_rows(msg))
        name = (conv.get("created_at") or "")[:10] + "_" + (conv.get("name") or conv.get("uuid", "conversa"))
        yield name, rows


TEXT_DOC = (".md", ".txt", ".csv", ".json", ".py")


def claude_ai_projects(path, only=None, dump=None):
    """Yield (name, rows) with each project's instructions and text knowledge docs.

    `path` is projects.json (a list) or a folder of one-project JSON files.
    Non-text docs (XML, HTML, CSS) are listed by name; with `dump` every doc
    is also written as-is under dump/<project>/<filename>.
    """
    files = sorted(glob.glob(os.path.join(path, "*.json"))) if os.path.isdir(path) else [path]
    projects = []
    for file in files:
        with open(file, encoding="utf-8") as fh:
            data = json.load(fh)
        projects.extend(data if isinstance(data, list) else [data])
    for proj in projects:
        name = (proj.get("name") or "").strip() or proj.get("uuid", "")[:8]
        if only and name not in only and not any(proj.get("uuid", "").startswith(p) for p in only):
            continue
        rows = []
        if proj.get("prompt_template"):
            rows.append(("", "project", "instructions", proj["prompt_template"]))
        skipped = []
        for doc in proj.get("docs", []):
            fname = doc.get("filename", "")
            if dump:
                target = os.path.join(dump, slug(name), *[slug(p) for p in fname.split("/")])
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, "w", encoding="utf-8") as fh:
                    fh.write(doc.get("content") or "")
            if fname.lower().endswith(TEXT_DOC):
                rows.append(((doc.get("created_at") or "")[:16], "project", "doc:" + fname, doc.get("content", "")))
            else:
                skipped.append(fname)
        if skipped:
            rows.append(("", "project", "doc:arquivos_nao_texto",
                         "Guardados só no arquivo bruto (XML/HTML/CSS):\n" + "\n".join(skipped)))
        yield "PROJETO_" + name, rows


def slug(name):
    return re.sub(r"[^\w.-]+", "_", name, flags=re.U).strip("_")[:80] or "conversa"


def write(out, name, rows, cap, db, md=True):
    for ts, role, kind, text in rows:
        db.execute("INSERT INTO mensagens VALUES (?,?,?,?,?)", (name, ts, role, kind, text))
    if not md:
        return name
    os.makedirs(os.path.join(out, "conversas"), exist_ok=True)
    full, dialog = [f"# {name}\n"], [f"# {name}\n"]
    for ts, role, kind, text in rows:
        who = {"user": "🧑 USUÁRIO", "assistant": "🤖 IA", "project": "📁 PROJETO"}[role]
        if kind in ("text", "instructions", "anexo") or kind.startswith("doc:"):
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
    ap.add_argument("--only", nargs="*", help="claude.ai: conversation uuid prefixes or project names to keep")
    ap.add_argument("--dump-docs", help="claude.ai projects: also write every project file as-is here")
    ap.add_argument("--no-md", action="store_true", help="only fill base.sqlite, no Markdown files")
    ap.add_argument("sources", nargs="*", help="Claude Code .jsonl, conversations.json, projects.json or a projects/ folder")
    args = ap.parse_args()
    sources = args.sources or glob.glob(os.path.expanduser("~/.claude/projects/*/*.jsonl"))
    os.makedirs(args.out, exist_ok=True)
    db = sqlite3.connect(os.path.join(args.out, "base.sqlite"))
    db.execute("CREATE TABLE IF NOT EXISTS mensagens (conversa TEXT, quando TEXT, papel TEXT, tipo TEXT, texto TEXT)")
    md = not args.no_md
    for src in sources:
        name_hint = os.path.splitext(os.path.basename(src))[0]
        if src.endswith(".jsonl"):
            print(write(args.out, "claude_code_" + name_hint, list(claude_code_rows(src)), args.cap, db, md))
        elif os.path.isdir(src) or os.path.basename(src) == "projects.json":
            for name, rows in claude_ai_projects(src, args.only, args.dump_docs):
                print(write(args.out, name, rows, args.cap, db, md))
        else:
            for name, rows in claude_ai_conversations(src, args.only):
                print(write(args.out, name, rows, args.cap, db, md))
    db.commit()
    db.close()


if __name__ == "__main__":
    main()
