"""Export the customer-service study through local Craft CLIs.

Operator-assisted presentation step, not a research engine. No installation,
network access, or execution of commands contained in research input.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tmf_research.cli import validate


def export(args):
    record_path = Path(args.report).resolve()
    record = json.loads(record_path.read_text())
    validate(record)
    blueprint = Path(args.blueprint).resolve()
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    serial = 0

    def run(app, *params):
        nonlocal serial
        serial += 1
        result = subprocess.run([str(Path(getattr(args, app)).resolve()), *map(str, params)],
                                capture_output=True, text=True, timeout=120)
        (out / f"{serial:02}-{app}.log").write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(f"{app} failed; see step {serial} log")
        return result.stdout

    def command(name, params):
        return ["--cmd", name + "=" + json.dumps(params)]

    run("wordcraft", "convert", blueprint, out / "blueprint.docx")
    saved = run("wordcraft", "text", out / "blueprint.docx")
    assert "outcome_unknown" in saved and "Economics worksheet" in saved
    run("wordcraft", "convert", out / "blueprint.docx", out / "blueprint.pdf")
    run("wordcraft", "render", out / "blueprint.docx", out / "blueprint-preview.png", "--page", "1")

    requirements = record["requirements"]
    rows = [["ID", "Domain", "Priority", "Requirement", "Acceptance", "Basis", "Status"]]
    rows += [[r["id"], r.get("domain", ""), r.get("priority", ""), r["text"],
              r["acceptance"], r.get("basis", "Design"), r.get("status", "Proposed")]
             for r in requirements]
    commands = []
    for row_number, row in enumerate(rows, 1):
        for column, value in enumerate(row):
            commands.append({"command": "cell.set", "params": {
                "cell": f"{chr(65 + column)}{row_number}", "input": value}})
    last = len(rows)
    commands += [
        {"command": "sheet.rename", "params": {"name": "Requirements"}},
        {"command": "insert.table", "params": {"range": f"A1:G{last}", "header": True,
                                                 "name": "Requirements", "style": "TableStyleMedium2"}},
        {"command": "home.wrapText", "params": {"range": f"A1:G{last}", "on": True}},
        {"command": "home.columnWidth", "params": {"cols": "A:A,C:C", "width": 65}},
        {"command": "home.columnWidth", "params": {"cols": "B:B,F:F,G:G", "width": 145}},
        {"command": "home.columnWidth", "params": {"cols": "D:D,E:E", "width": 370}},
        {"command": "home.rowHeight", "params": {"rows": f"2:{last}", "height": 80}},
        {"command": "view.freezeTopRow", "params": {}},
        {"command": "cell.set", "params": {"cell": "I1", "input": "Proposed requirements"}},
        {"command": "cell.set", "params": {"cell": "J1", "input": f"=COUNTA(A2:A{last})"}},
    ]
    script = out / "grid-commands.jsonl"
    script.write_text("\n".join(json.dumps(x) for x in commands))
    run("gridcraft", "run", "--script", script, "--out", out / "requirements.xlsx", "--quiet")
    assert run("gridcraft", "eval", "=J1", "--in", out / "requirements.xlsx").strip() == str(len(requirements))
    run("gridcraft", "convert", out / "requirements.xlsx", out / "requirements.csv")
    with (out / "requirements.csv").open(newline="") as stream:
        csv_rows = list(csv.reader(stream))
    assert [row[:7] for row in csv_rows[:last]] == rows

    # Briefing draws from the same reviewed record; it is not a second finding source.
    slides = [("The pilot", record["summary"])]
    slides += [("Research finding", f["text"] + ("\nLimit: " + f["caveat"] if f.get("caveat") else "") +
                "\nEvidence: " + ", ".join(f["sources"])) for f in record["findings"][:9]]
    slides += [("Build and verify", f"{len(requirements)} proposed requirements\nIdentity and private-note controls\nDurable cases and confirmed human takeover\nIdempotent effects and visible recovery\nSupervised pilot and measured outcomes"),
               ("Limits and next decision", "Operator-assisted research; no autonomous investigation.\nNo customer-service system implemented or tested.\nChoose client, channel, intents and authoritative systems.\nValidate demand, access, costs and acceptance scope.")]
    cmd = ["run", *command("file.new", {"blank": True, "theme": "Nocturne"})]
    for index, (title, body) in enumerate(slides):
        cmd += command("slide.new", {"layout": "blank"})
        cmd += command("design.background", {"color": "#101A2C"})
        for rect, text, size, color in [
            ([60, 25, 840, 30], f"TMF / CUSTOMER SERVICE                         {index + 1:02} / {len(slides):02}", 13, "#58D6D0"),
            ([60, 85, 840, 65], title, 32, "#FFFFFF"),
            ([60, 180, 840, 285], body, 22, "#D7E3F0"),
            ([60, 495, 840, 22], "RESEARCHED BLUEPRINT / PROPOSED SERVICE / NOT IMPLEMENTED", 10, "#94A8BF"),
        ]:
            cmd += command("insert.textBox", {"rect": rect, "text": text})
            cmd += command("format.fontDialog", {"family": "Inter", "size": size, "color": color})
        cmd += command("slide.notes", {"text": "See evidence-report.md and report.json for full source URLs, scope and limitations."})
    run("deckcraft", *cmd, "--save", out / "briefing.pptx")
    run("deckcraft", "convert", out / "briefing.pptx", out / "briefing.pdf")
    run("deckcraft", "render", out / "briefing.pptx", "--all", out / "slides")
    with zipfile.ZipFile(out / "briefing.pptx") as archive:
        parts = [n for n in archive.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")]
        assert len(parts) == len(slides)
        texts = [" ".join(x.text or "" for x in ET.fromstring(archive.read(n)).iter(
            "{http://schemas.openxmlformats.org/drawingml/2006/main}t")) for n in parts]
        assert any("Operator-assisted research" in text for text in texts)
    receipt = {"status": "passed", "scope": "Local Craft CLI export and saved-content readback; no native GUI or Microsoft interoperability test",
               "input_sha256": {"report": hashlib.sha256(record_path.read_bytes()).hexdigest(),
                                "blueprint": hashlib.sha256(blueprint.read_bytes()).hexdigest()},
               "requirements": len(requirements), "slides": len(slides),
               "checks": ["WordCraft saved text", "GridCraft formula", "independent CSV requirement equality", "independent PPTX XML slide count and limitations"],
               "outputs": {name: hashlib.sha256((out / name).read_bytes()).hexdigest() for name in
                           ["blueprint.docx", "blueprint.pdf", "requirements.xlsx", "requirements.csv", "briefing.pptx", "briefing.pdf"]}}
    (out / "export-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("report", "blueprint", "wordcraft", "gridcraft", "deckcraft", "output"):
        parser.add_argument("--" + name, required=True)
    export(parser.parse_args())
