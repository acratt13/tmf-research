"""Reproducible local trial against separately installed Craft v0.8.0 CLIs.

No download, installation, server, API key, or network request is performed here.
The generated pack is an original proposed service-readiness study, not client data.
"""
import argparse
import csv
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
import zipfile

SERVICES = [
    ("S01", "Systems assessment", "Identify worthwhile automation", "Client validates evidence and ranked opportunities", "Read-only application/data inventory"),
    ("S03", "Workflow integration", "Connect approved business actions", "Duplicate, timeout and recovery scenarios pass", "Selected APIs and identity scopes"),
    ("S04", "Customer service", "Route requests with human takeover", "Case context survives escalation and tool failure", "Support CRM, channels and knowledge"),
    ("S05", "Revenue operations", "Connect invoicing and payments", "Partial payments and credits reconcile without duplicates", "Accounting and payment providers"),
    ("S06", "Ecommerce operations", "Connect orders and fulfillment", "Inventory, partial fulfillment and refunds reconcile", "Storefront, stock and shipping systems"),
    ("S08", "Payroll operations", "Move approved inputs through provider workflow", "Responsible owner reconciles run, payment and filing outcomes", "Jurisdiction-specific payroll provider"),
]
SOURCE = "https://github.com/acratt13/tmf-research/blob/47b77af/docs/SERVICE-SPEC.md"
REVIEW = "Pilot artifacts generated; client acceptance pending."


def office_text(path, member, namespace):
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read(member))
    return "\n".join(x.text or "" for x in root.iter(namespace))


def trial(args):
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    result = {"scope": "Local CLI create/reopen/edit/export trial; no native GUI or production integration proof", "apps": {}}
    serial = 0

    def run(app, *command):
        nonlocal serial
        serial += 1
        proc = subprocess.run([str(Path(getattr(args, app)).resolve()), *map(str, command)],
                              capture_output=True, text=True, timeout=90)
        (out / f"{serial:02d}-{app}.stdout.txt").write_text(proc.stdout)
        (out / f"{serial:02d}-{app}.stderr.txt").write_text(proc.stderr)
        if proc.returncode:
            raise RuntimeError(f"{app} step {serial} exited {proc.returncode}; see trial logs")
        return proc.stdout

    def cmd(name, params=None):
        return ["--cmd", name + ("=" + json.dumps(params, ensure_ascii=False) if params is not None else "")]

    headings = ["# TMF Systems | Research to delivery", "A service-readiness briefing", "",
                "## The opportunity", "Build premium business systems from evidence, explicit requirements and verified operating paths.",
                "All six offers below are specified proposals. None is presented as client-accepted or production-ready.", "", "## Priority service families"]
    for sid, title, outcome, acceptance, dependency in SERVICES:
        headings += [f"### {sid} | {title}", outcome + ".", "Acceptance: " + acceptance + ".", "Dependency: " + dependency + ".", ""]
    headings += ["## What every delivery needs", "Scope and business owner; data ownership and permissions; failure and recovery rules; actual acceptance evidence; ongoing support and exit arrangements.",
                 "", "## Remaining decisions", "Client, jurisdiction, provider entitlements, workflow volumes, cost and support commitments remain to be established.",
                 "", "## Source and evidence boundary", SOURCE,
                 "This briefing summarizes our proposed service specification. It is not independent market validation, regulatory assurance or a completed implementation."]
    (out / "briefing.md").write_text("\n\n".join(headings))

    try:
        run("wordcraft", "convert", out / "briefing.md", out / "briefing-draft.docx")
        run("wordcraft", "run", "--file", out / "briefing-draft.docx", *cmd("caret.docEnd"),
            *cmd("text.insert", {"text": "\n\nReview status: " + REVIEW}), "--save", out / "briefing.docx")
        text = run("wordcraft", "text", out / "briefing.docx")
        assert all(s[1] in text for s in SERVICES) and REVIEW in text and SOURCE in text
        run("wordcraft", "convert", out / "briefing.docx", out / "briefing.pdf")
        run("wordcraft", "render", out / "briefing.docx", out / "briefing-page-1.png", "--page", "1", "--scale", "1.5")
        run("wordcraft", "info", out / "briefing.docx")
        # Independent package inspection verifies the edit exists in the saved DOCX.
        xml = office_text(out / "briefing.docx", "word/document.xml", "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
        assert REVIEW in xml and "Payroll operations" in xml
        result["apps"]["wordcraft"] = {"status": "passed", "checks": ["create DOCX", "reopen and edit", "saved text and source readback", "PDF export", "page PNG render", "independent DOCX XML readback"]}
    except Exception as error:
        result["apps"]["wordcraft"] = {"status": "failed", "reason": str(error)}

    try:
        commands = []
        headers = ["ID", "Service", "Client outcome", "Stage", "Acceptance evidence", "Dependencies"]
        rows = [headers] + [[sid, title, outcome, "Specified", acceptance, dependency] for sid, title, outcome, acceptance, dependency in SERVICES]
        for row, values in enumerate(rows, 1):
            for col, value in enumerate(values):
                commands.append({"command": "cell.set", "params": {"cell": f"{chr(65 + col)}{row}", "input": value}})
        commands += [{"command": "sheet.rename", "params": {"name": "Service readiness"}},
                     {"command": "insert.table", "params": {"range": "A1:F7", "header": True, "name": "ServiceReadiness", "style": "TableStyleMedium2"}},
                     {"command": "home.wrapText", "params": {"range": "A1:F12", "on": True}},
                     {"command": "home.columnWidth", "params": {"cols": "A:A", "width": 44}},
                     {"command": "home.columnWidth", "params": {"cols": "B:B", "width": 155}},
                     {"command": "home.columnWidth", "params": {"cols": "C:C,F:F", "width": 210}},
                     {"command": "home.columnWidth", "params": {"cols": "D:D", "width": 85}},
                     {"command": "home.columnWidth", "params": {"cols": "E:E", "width": 290}},
                     {"command": "home.rowHeight", "params": {"rows": "2:7", "height": 52}},
                     {"command": "view.freezeTopRow", "params": {}}]
        for cell, value in {"A9": "Specification source", "B9": SOURCE, "I1": "Summary", "I2": "Offers specified", "J2": "=COUNTA(A2:A7)", "I3": "Specified stage", "J3": '=COUNTIF(D2:D7,"Specified")', "I4": "Client accepted", "J4": '=COUNTIF(D2:D7,"Client accepted")'}.items():
            commands.append({"command": "cell.set", "params": {"cell": cell, "input": value}})
        script = out / "workbook-commands.jsonl"
        script.write_text("\n".join(json.dumps(c) for c in commands))
        run("gridcraft", "run", "--script", script, "--out", out / "service-readiness-draft.xlsx", "--quiet")
        run("gridcraft", "run", "--in", out / "service-readiness-draft.xlsx",
            *cmd("cell.set", {"cell": "A11", "input": REVIEW}), "--out", out / "service-readiness.xlsx", "--quiet")
        text = run("gridcraft", "cat", out / "service-readiness.xlsx", "--range", "A1:J11")
        assert "Payroll operations" in text and REVIEW in text
        for cell, expected in [("J2", "6"), ("J3", "6"), ("J4", "0")]:
            value = run("gridcraft", "eval", f"={cell}", "--in", out / "service-readiness.xlsx").strip()
            assert value == expected, (cell, value, expected)
        run("gridcraft", "convert", out / "service-readiness.xlsx", out / "service-readiness.html")
        run("gridcraft", "convert", out / "service-readiness.xlsx", out / "service-readiness.csv")
        run("gridcraft", "info", out / "service-readiness.xlsx", "--json")
        run("gridcraft", "check", out / "service-readiness.xlsx", "--json")
        with (out / "service-readiness.csv").open(newline="") as stream:
            saved = list(csv.reader(stream))
        assert saved[6][1] == "Payroll operations" and saved[10][0] == REVIEW
        result["apps"]["gridcraft"] = {"status": "passed", "checks": ["create styled XLSX table", "reopen and edit", "formula readback 6/6/0", "HTML and CSV exports", "GridCraft roundtrip check", "independent CSV readback"]}
    except Exception as error:
        result["apps"]["gridcraft"] = {"status": "failed", "reason": str(error)}

    try:
        command = ["run", *cmd("file.new", {"blank": True, "theme": "Nocturne"}), *cmd("file.properties", {"title": "TMF Systems | Research to delivery", "author": "TMF Systems"})]
        slides = [
            ("TMF Systems", "Research to delivery\nPremium business software, workflows and workspaces\nPilot briefing | Proposed service specification"),
            ("Six priority service families", "Systems assessment\nWorkflow integration\nCustomer service\nRevenue operations\nEcommerce operations\nPayroll operations"),
            ("What makes a deliverable professional", "Explicit scope and ownership\nSource-linked requirements\nFailure and recovery paths\nReal acceptance evidence\nSupport and exit arrangements"),
            ("Research before implementation", "Research lead coordinates bounded investigation\nWeb, documents and REA supply evidence\nReview checks support, conflicts and gaps\nOne record feeds report, workbook and briefing"),
            ("Evidence and decisions still needed", "Client, jurisdiction and operating volumes\nProvider access and authoritative records\nCosts, support coverage and specialist review\nNo offer is declared client-accepted here"),
            ("Source and next step", "Source: " + SOURCE + "\nNext: select one client problem and verify its complete workflow\nProposed architecture and scope; not production proof"),
        ]
        for index, (title, body) in enumerate(slides):
            command += cmd("slide.new", {"layout": "blank"})
            command += cmd("design.background", {"color": "#101A2C"})
            command += cmd("insert.textBox", {"rect": [60, 22, 800, 24], "text": f"TMF / RESEARCH                                          {index + 1:02d} / 06"})
            command += cmd("format.fontDialog", {"family": "Inter", "size": 13, "bold": True, "color": "#58D6D0"})
            command += cmd("insert.textBox", {"rect": [60, 70, 840, 66], "text": title})
            command += cmd("format.fontDialog", {"family": "Inter", "size": 34, "bold": True, "color": "#FFFFFF"})
            command += cmd("shape.insert", {"preset": "rect", "rect": [60, 143, 80, 4]})
            command += cmd("shape.fill", {"color": "#58D6D0"})
            command += cmd("shape.line", {"none": True})
            command += cmd("insert.textBox", {"rect": [60, 180, 840, 290], "text": body})
            command += cmd("format.fontDialog", {"family": "Inter", "size": 23, "bold": False, "color": "#D7E3F0"})
            command += cmd("insert.textBox", {"rect": [60, 495, 840, 20], "text": "SERVICE READINESS PILOT  /  PROPOSED SCOPE"})
            command += cmd("format.fontDialog", {"family": "Inter", "size": 10, "bold": False, "color": "#94A8BF"})
        run("deckcraft", *command, "--save", out / "briefing-draft.pptx")
        run("deckcraft", "run", "--in", out / "briefing-draft.pptx", *cmd("slide.go", {"index": 5}),
            *cmd("slide.notes", {"text": REVIEW}), "--save", out / "briefing.pptx")
        info = run("deckcraft", "info", out / "briefing.pptx")
        run("deckcraft", "convert", out / "briefing.pptx", out / "slides.pdf")
        run("deckcraft", "convert", out / "briefing.pptx", out / "slides.md")
        run("deckcraft", "render", out / "briefing.pptx", "--all", str(out / "slides"))
        with zipfile.ZipFile(out / "briefing.pptx") as archive:
            members = archive.namelist()
            slide_parts = [x for x in members if x.startswith("ppt/slides/slide") and x.endswith(".xml") and "/_rels/" not in x]
            assert len(slide_parts) == 6, len(slide_parts)
            text = " ".join(archive.read(x).decode() for x in members if x.endswith(".xml"))
            assert REVIEW in text and "Payroll operations" in text and SOURCE in text
        result["apps"]["deckcraft"] = {"status": "passed", "checks": ["create six-slide PPTX", "reopen and edit notes", "independent PPTX and notes XML readback", "PDF and Markdown export", "slide PNG rendering"]}
    except Exception as error:
        result["apps"]["deckcraft"] = {"status": "failed", "reason": str(error)}
    (out / "result.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return 0 if all(v["status"] == "passed" for v in result["apps"].values()) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for app in ("wordcraft", "gridcraft", "deckcraft"):
        parser.add_argument("--" + app, required=True, help="Path to the upstream CLI executable")
    parser.add_argument("--output", required=True, help="A new directory; existing runs are never overwritten")
    raise SystemExit(trial(parser.parse_args()))
