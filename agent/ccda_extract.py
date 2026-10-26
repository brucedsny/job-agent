#!/usr/bin/env python3
"""Turn Epic C-CDA visit documents (IHE_XDM/*/DOC*.XML) into readable text.

Usage: python3 -I agent/ccda_extract.py OUT_DIR EXPORT_DIR [EXPORT_DIR ...]
EXPORT_DIR is an unzipped MyChart "Visit Records" download (has IHE_XDM/).
Writes OUT_DIR/visits/<date>_<type>_<docid>.md per document and
OUT_DIR/visits_index.json with one row per document.
"""

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {"h": "urn:hl7-org:v3"}
BLOCK = {"paragraph", "tr", "item", "br", "caption", "list", "table", "thead", "tbody"}


def local(tag: str) -> str:
    return tag.split("}", 1)[-1]


def narrative(el) -> str:
    """Flatten CDA narrative XHTML-ish markup into text with rows and cells."""
    out: list[str] = []

    def walk(node):
        name = local(node.tag)
        if name in ("td", "th"):
            out.append(" ".join("".join(node.itertext()).split()) + " | ")
            if node.tail and node.tail.strip():
                out.append(node.tail.strip())
            return
        if node.text and node.text.strip():
            out.append(node.text.strip() + " ")
        for child in node:
            walk(child)
        if name in BLOCK:
            out.append("\n")
        if node.tail and node.tail.strip():
            out.append(node.tail.strip() + " ")

    walk(el)
    text = "".join(out)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def ts(value: str | None) -> str:
    if not value or len(value) < 8:
        return ""
    v = value[:12]
    date = f"{v[0:4]}-{v[4:6]}-{v[6:8]}"
    return date + (f" {v[8:10]}:{v[10:12]}" if len(v) >= 12 else "")


def name_of(el) -> str:
    if el is None:
        return ""
    parts = [" ".join(p.itertext()).strip() for p in el.findall(".//h:name/*", NS)]
    if not parts:
        parts = ["".join(el.find(".//h:name", NS).itertext()).strip()] if el.find(".//h:name", NS) is not None else []
    return " ".join(p for p in parts if p)


def parse(path: Path) -> dict:
    root = ET.parse(path).getroot()
    title = "".join((root.find("h:title", NS) or ET.Element("x")).itertext()).strip()
    enc = root.find(".//h:componentOf/h:encompassingEncounter", NS)
    low = high = etype = location = provider = ""
    if enc is not None:
        eff = enc.find("h:effectiveTime", NS)
        if eff is not None:
            low = ts((eff.find("h:low", NS) if eff.find("h:low", NS) is not None else eff).get("value"))
            hi = eff.find("h:high", NS)
            high = ts(hi.get("value")) if hi is not None else ""
        code = enc.find("h:code", NS)
        if code is not None:
            etype = code.get("displayName") or ""
            if not etype:
                ot = code.find("h:originalText", NS)
                etype = "".join(ot.itertext()).strip() if ot is not None else ""
        fac = enc.find(".//h:healthCareFacility", NS)
        if fac is not None:
            nm = fac.find(".//h:location/h:name", NS)
            if nm is None:
                nm = fac.find(".//h:serviceProviderOrganization/h:name", NS)
            location = "".join(nm.itertext()).strip() if nm is not None else ""
        prov = enc.find(".//h:encounterParticipant//h:assignedPerson", NS)
        if prov is None:
            prov = enc.find(".//h:responsibleParty//h:assignedPerson", NS)
        provider = name_of(prov)
    doc_time = ts((root.find("h:effectiveTime", NS) or ET.Element("x")).get("value"))
    sections = []
    for sec in root.iter("{urn:hl7-org:v3}section"):
        st = sec.find("h:title", NS)
        body = sec.find("h:text", NS)
        if st is None or body is None:
            continue
        txt = narrative(body)
        if txt:
            sections.append({"title": "".join(st.itertext()).strip(), "text": txt})
    return {
        "title": title, "doc_time": doc_time, "start": low, "end": high,
        "type": etype, "location": location, "provider": provider, "sections": sections,
    }


def main():
    out = Path(sys.argv[1])
    (out / "visits").mkdir(parents=True, exist_ok=True)
    rows = []
    for export in sys.argv[2:]:
        for xml in sorted(Path(export).glob("IHE_XDM/*/DOC*.XML")):
            try:
                d = parse(xml)
            except ET.ParseError as e:
                print("parse error", xml, e)
                continue
            date = (d["start"] or d["doc_time"] or "0000-00-00")[:10]
            kind = re.sub(r"[^A-Za-z0-9]+", "_", d["type"] or d["title"])[:40].strip("_")
            name = f"{date}_{kind}_{Path(export).name[-24:]}_{xml.stem}.md"
            secs = "\n\n".join(f"## {s['title']}\n\n{s['text']}" for s in d["sections"])
            header = (
                f"# {d['title']} — {d['type']}\n\n"
                f"- Período: {d['start']} → {d['end'] or '(sem fim)'}\n"
                f"- Local: {d['location']}\n- Profissional: {d['provider']}\n"
                f"- Origem: {Path(export).name}/{xml.name}\n\n"
            )
            (out / "visits" / name).write_text(header + secs)
            diag = next((s["text"] for s in d["sections"] if re.search(r"diagnos", s["title"], re.I)), "")
            reason = next((s["text"] for s in d["sections"] if re.search(r"reason for visit", s["title"], re.I)), "")
            rows.append({
                "date": date, "start": d["start"], "end": d["end"], "type": d["type"], "title": d["title"],
                "location": d["location"], "provider": d["provider"], "reason": reason[:300],
                "diagnoses": diag[:400], "sections": [s["title"] for s in d["sections"]],
                "chars": len(secs), "file": f"visits/{name}", "source": f"{Path(export).name}/{xml.name}",
            })
    rows.sort(key=lambda r: r["start"] or r["date"])
    (out / "visits_index.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    print(len(rows), "documents")


if __name__ == "__main__":
    main()
