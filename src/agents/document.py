"""Agent 5 — Document: ATS-safe PDF (WeasyPrint, Typst fallback) + ATS validator.

Deliberately plain layout: one column, standard fonts, no tables/images,
recognizable headings, fully selectable text. No LLM.
"""

from __future__ import annotations

import html as html_lib
import shutil
import subprocess
from pathlib import Path

from jinja2 import Template
from pydantic import BaseModel

from ..models import TailoredResume

EXPECTED_HEADINGS = ("RESUMO", "EXPERIÊNCIA", "EXPERIENCE", "SKILLS",
                     "COMPETÊNCIAS", "EDUCATION", "FORMAÇÃO")


class DocumentError(RuntimeError):
    pass


class AtsReport(BaseModel):
    passed: bool
    char_count: int
    has_images: bool
    found_headings: list[str]
    issues: list[str]


_HTML = Template(
    """<!DOCTYPE html><html lang="pt-br"><head><meta charset="utf-8">
<style>
  @page { size: A4; margin: 1.6cm; }
  body { font-family: Arial, Helvetica, sans-serif; font-size: 10.5pt; color: #111; line-height: 1.35; }
  h1 { font-size: 18pt; margin: 0 0 2px 0; }
  h2 { font-size: 12pt; margin: 14px 0 4px 0; border-bottom: 1px solid #444; text-transform: uppercase; }
  .contact { font-size: 9.5pt; color: #333; }
  .headline { font-weight: bold; margin: 2px 0 6px 0; }
  .role { font-weight: bold; }
  ul { margin: 4px 0 8px 18px; padding: 0; }
</style></head><body>
  <h1>{{ name }}</h1>
  <div class="contact">{{ contact_line }}</div>
  {% if headline %}<div class="headline">{{ headline }}</div>{% endif %}
  {% if summary %}<h2>Resumo</h2><div>{{ summary }}</div>{% endif %}
  <h2>Experiência</h2>
  {% for exp in experiences %}
    <div><span class="role">{{ exp.title }} — {{ exp.company }}</span> ({{ exp.dates }})</div>
    <ul>{% for b in exp.bullets %}<li>{{ b.text }}</li>{% endfor %}</ul>
  {% endfor %}
  {% if skills %}<h2>Competências</h2><div>{{ skills | join(', ') }}</div>{% endif %}
  {% if education_lines %}<h2>Formação</h2>
  <ul>{% for ed in education_lines %}<li>{{ ed }}</li>{% endfor %}</ul>{% endif %}
</body></html>""",
    autoescape=True,
)


def render_html(resume: TailoredResume) -> str:
    return _HTML.render(
        name=resume.name, contact_line=resume.contact_line, headline=resume.headline,
        summary=resume.summary, experiences=resume.experiences, skills=resume.skills,
        education_lines=resume.education_lines,
    )


def render_pdf(resume: TailoredResume, out_path: str | Path) -> str:
    """Render the PDF; returns the engine used ('weasyprint' | 'typst')."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from weasyprint import HTML  # heavy system deps; lazy import

        HTML(string=render_html(resume)).write_pdf(str(out_path))
        return "weasyprint"
    except Exception:  # noqa: BLE001 — intentional fallback
        _render_typst(resume, out_path)
        return "typst"


def _typ_escape(text: str) -> str:
    for ch in ("\\", "#", "$", "*", "_", "@", "<", ">", "[", "]"):
        text = text.replace(ch, "\\" + ch)
    return text


def _render_typst(resume: TailoredResume, out_path: Path) -> None:
    if shutil.which("typst") is None:
        raise DocumentError("Neither WeasyPrint nor Typst is available "
                            "(install the [pdf] extra or the `typst` binary).")
    e = _typ_escape
    lines = ['#set page(paper: "a4", margin: 1.6cm)', '#set text(size: 10.5pt)',
             f"= {e(resume.name)}", e(resume.contact_line)]
    if resume.headline:
        lines.append(f"*{e(resume.headline)}*")
    if resume.summary:
        lines += ["== Resumo", e(resume.summary)]
    lines.append("== Experiência")
    for exp in resume.experiences:
        lines.append(f"*{e(exp.title)} — {e(exp.company)}* ({e(exp.dates)})")
        lines += [f"- {e(b.text)}" for b in exp.bullets]
    if resume.skills:
        lines += ["== Competências", e(", ".join(resume.skills))]
    if resume.education_lines:
        lines += ["== Formação"] + [f"- {e(ed)}" for ed in resume.education_lines]
    typ_path = out_path.with_suffix(".typ")
    typ_path.write_text("\n".join(lines), encoding="utf-8")
    proc = subprocess.run(["typst", "compile", str(typ_path), str(out_path)],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise DocumentError(f"Typst failed: {proc.stderr}")


def validate_ats(pdf_path: str | Path) -> AtsReport:
    from pypdf import PdfReader  # lazy

    reader = PdfReader(str(pdf_path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    upper = html_lib.unescape(text).upper()
    found = [h for h in EXPECTED_HEADINGS if h in upper]
    has_images = False
    for page in reader.pages:
        try:
            xobjs = page.get("/Resources", {}).get("/XObject")
            if xobjs and any(o.get_object().get("/Subtype") == "/Image"
                             for o in xobjs.get_object().values()):
                has_images = True
        except Exception:  # noqa: BLE001
            continue

    issues = []
    if len(text.strip()) < 200:
        issues.append("Too little extractable text — ATS may not read the PDF.")
    if not found:
        issues.append("No recognizable section headings.")
    if has_images:
        issues.append("Contains images — ATS may ignore embedded content.")
    return AtsReport(passed=not issues, char_count=len(text.strip()), has_images=has_images,
                     found_headings=found, issues=issues)
