"""Local evidence/report CLI and bounded TMF Council research runner."""
from __future__ import annotations
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import urlsplit

LABELS = {"documented", "observed", "inferred", "proposed", "unknown"}
SOURCE_STATES = {"available", "partial", "unavailable"}
REA_OPERATIONS = {"inspect-managed-artifact", "inspect-managed-members", "analyze-javascript-application"}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_new(path, text):
    """Never silently replace a report or its evidence."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as stream:
        stream.write(text)


def dump(value):
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def validate(record):
    if not isinstance(record, dict) or record.get("schema_version") != 1:
        raise ValueError("Expected report object with schema_version=1")
    for field in ("title", "question", "summary"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise ValueError(f"Missing nonempty {field}")
    for field in ("sources", "findings", "requirements", "unknowns"):
        if not isinstance(record.get(field), list):
            raise ValueError(f"{field} must be an array")
    sources = {}
    for source in record["sources"]:
        if not isinstance(source, dict):
            raise ValueError("Every source must be an object")
        sid = source.get("id", "")
        if not isinstance(sid, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", sid) or sid in sources:
            raise ValueError("Source IDs must be unique stable identifiers")
        if source.get("state") not in SOURCE_STATES:
            raise ValueError(f"Source {sid}: invalid state")
        for field in ("title", "retrieved_at", "scope", "limitations"):
            if not isinstance(source.get(field), str) or not source[field].strip():
                raise ValueError(f"Source {sid}: missing {field}")
        try:
            datetime.fromisoformat(source["retrieved_at"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"Source {sid}: invalid timestamp") from exc
        if "url" in source:
            url = urlsplit(source["url"])
            if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password:
                raise ValueError(f"Source {sid}: expected public-style HTTP(S) URL without credentials")
        if "artifact_sha256" in source and not re.fullmatch(r"[a-f0-9]{64}", source["artifact_sha256"]):
            raise ValueError(f"Source {sid}: invalid SHA256")
        sources[sid] = source
    for finding in record["findings"]:
        if not isinstance(finding, dict) or not isinstance(finding.get("text"), str) or not finding["text"].strip():
            raise ValueError("Every finding needs text")
        if finding.get("label") not in LABELS:
            raise ValueError("Every finding needs an explicit evidence label")
        if "caveat" in finding and not isinstance(finding["caveat"], str):
            raise ValueError("Finding caveat must be text")
        refs = finding.get("sources", [])
        if not isinstance(refs, list) or any(not isinstance(x, str) or x not in sources for x in refs):
            raise ValueError("Finding cites an unknown source ID")
        if finding["label"] in {"documented", "observed"}:
            if not refs or any(sources[x]["state"] == "unavailable" for x in refs):
                raise ValueError("Documented/observed findings need available or partial evidence")
        if any(sources[x]["state"] == "partial" for x in refs) and not finding.get("caveat"):
            raise ValueError("Findings citing partial evidence need a caveat")
    for requirement in record["requirements"]:
        if not isinstance(requirement, dict):
            raise ValueError("Every requirement must be an object")
        for key in ("id", "text", "acceptance"):
            if not isinstance(requirement.get(key), str) or not requirement[key].strip():
                raise ValueError(f"Requirement missing {key}")
    ids = [x["id"] for x in record["requirements"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Requirement IDs must be unique")
    if any(not isinstance(x, str) or not x.strip() for x in record["unknowns"]):
        raise ValueError("Unknowns must be nonempty strings")
    return record


def report_lines(record, audience="technical"):
    """One semantic view feeds Markdown, HTML and PDF alike."""
    validate(record)
    lines = [("title", record["title"]), ("body", record["question"]),
             ("heading", "Summary"), ("body", record["summary"]),
             ("body", "Evidence labels describe the input. Validation checks structure and references; it does not verify the truth of a claim.")]
    lines.append(("heading", "Findings"))
    for finding in record["findings"]:
        refs = ", ".join(finding.get("sources", [])) or "no external evidence"
        lines.append(("body", f"[{finding['label'].upper()}] {finding['text']} ({refs})"))
        if finding.get("caveat"):
            lines.append(("body", "Limit: " + finding["caveat"]))
    if audience == "technical":
        lines.append(("heading", "Proposed requirements and acceptance"))
        for item in record["requirements"]:
            lines.extend([("body", item["id"] + ": " + item["text"]), ("body", "Acceptance: " + item["acceptance"])])
    lines.append(("heading", "Unknowns and remaining work"))
    lines.extend(("body", x) for x in record["unknowns"])
    lines.append(("heading", "Evidence register"))
    for source in record["sources"]:
        lines.append(("body", f"{source['id']} — {source['title']} [{source['state']}]; retrieved {source['retrieved_at']}"))
        for key in ("url", "artifact_sha256", "evidence_id", "scope", "limitations"):
            if source.get(key):
                lines.append(("body", key + ": " + str(source[key])))
    return lines


def markdown(lines):
    # Deliberately plain prose: untrusted input cannot add active HTML or remote image loads.
    def escape(value):
        value = value.replace("\\", "\\\\")
        for char in "`*_{}[]<>!#|":
            value = value.replace(char, "\\" + char)
        return value.replace("\n", " ").replace("\r", " ")
    return "\n\n".join(("# " if kind == "title" else "## " if kind == "heading" else "") + escape(text)
                         for kind, text in lines) + "\n"


def html_report(lines):
    body = "\n".join(f"<{tag}>{html.escape(text)}</{tag}>" for kind, text in lines
                     for tag in [{"title": "h1", "heading": "h2", "body": "p"}[kind]])
    return ('<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
            '<title>TMF Research report</title><style>'
            'body{font:17px/1.65 system-ui,sans-serif;max-width:860px;margin:48px auto;padding:0 24px;color:#17212b;background:#fafafa}'
            'h1{line-height:1.15;font-size:40px}h2{margin-top:36px}p{overflow-wrap:anywhere}'
            '@media print{body{font-size:11pt;margin:0;max-width:none}h2{break-after:avoid}p{orphans:3;widows:3}}'
            '</style><body>' + body + '</body></html>')


def pdf_report(path, lines):
    try:
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    except ImportError as exc:
        raise ValueError("PDF requires the optional dependency: pip install '.[pdf]'") from exc
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    story = []
    for kind, text in lines:
        style = styles[{"title": "Title", "heading": "Heading2", "body": "BodyText"}[kind]]
        story.extend([Paragraph(html.escape(text), style), Spacer(1, 8)])
    # Exclusive open prevents replacing an existing client deliverable.
    with target.open("xb") as output:
        SimpleDocTemplate(output, title=lines[0][1], author="TMF Research").build(story)


def rea_record(path, title):
    """Import the original REA envelope; do not reinterpret missing coverage as complete."""
    raw = Path(path).read_bytes()
    if len(raw) > 16 * 1024 * 1024:
        raise ValueError("REA evidence exceeds the 16 MiB import limit")
    envelope = json.loads(raw)
    if not isinstance(envelope, dict) or not isinstance(envelope.get("evidence_id"), str):
        raise ValueError("Expected a REA evidence envelope with evidence_id")
    normalized = envelope.get("normalized_result")
    if not isinstance(normalized, dict):
        raise ValueError("REA envelope has no structured normalized_result")
    coverage = normalized.get("coverage", normalized.get("completeness", {}))
    limitations = envelope.get("limitations", [])
    if not isinstance(limitations, list):
        raise ValueError("REA limitations must be an array")
    source = {"id": "rea1", "title": title, "state": "partial",
              "retrieved_at": datetime.now(timezone.utc).isoformat(),
              "evidence_id": envelope["evidence_id"], "artifact_sha256": hashlib.sha256(raw).hexdigest(),
              "scope": "Imported REA JSON envelope. Coverage: " + json.dumps(coverage),
              "limitations": " | ".join(str(x) for x in limitations) or "Coverage and claim support require manual review."}
    return {"schema_version": 1, "title": title, "question": "What does this REA inspection establish?",
            "summary": "REA evidence imported. No domain findings have been asserted automatically.",
            "sources": [source], "findings": [], "requirements": [],
            "unknowns": ["Review the original normalized_result and its coverage before writing findings.",
                         "The recorded SHA256 identifies the imported evidence file, not the inspected target artifact.",
                         "An imported envelope is not proof of successful or complete inspection."]}


def main(argv=None):
    parser = argparse.ArgumentParser(description="TMF Council local research workbench")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="Open the local TMF Council research workbench")
    serve.add_argument("--runs", default="runs/council")
    serve.add_argument("--config", help="Local operator configuration JSON; never model supplied")
    serve.add_argument("--port", type=int, default=8765)
    run = sub.add_parser("run", help="Run a research brief through TMF Council")
    run.add_argument("brief")
    run.add_argument("--runs", default="runs/council")
    run.add_argument("--config", help="Local operator configuration JSON")
    check = sub.add_parser("validate", help="Check report structure and source references, not claim truth")
    check.add_argument("record")
    render = sub.add_parser("render", help="Render one structured record as Markdown, HTML or PDF")
    render.add_argument("record")
    render.add_argument("--format", choices=["md", "html", "pdf"], default="md")
    render.add_argument("--audience", choices=["technical", "executive"], default="technical")
    render.add_argument("--output", required=True)
    imp = sub.add_parser("import-rea", help="Import a REA JSON envelope without inventing findings")
    imp.add_argument("evidence")
    imp.add_argument("--title", required=True)
    imp.add_argument("--output", required=True)
    inspect = sub.add_parser("inspect", help="Run a selected local REA inspection; target code is not intentionally launched")
    inspect.add_argument("target")
    inspect.add_argument("--operation", choices=sorted(REA_OPERATIONS), required=True)
    inspect.add_argument("--rea-command", default='["rea"]', help="JSON array command prefix; never interpreted by a shell")
    inspect.add_argument("--timeout", type=int, default=60)
    inspect.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "serve":
            from .server import serve as serve_workbench
            if not 1024 <= args.port <= 65535:
                raise ValueError("Use an unprivileged local port")
            serve_workbench(args.runs, read_json(args.config) if args.config else {}, args.port)
        elif args.command == "run":
            from .engine import ResearchEngine, RunStore
            store = RunStore(args.runs)
            run_id = store.create(read_json(args.brief))
            print(dump({"run_id": run_id, "status": "queued"}), end="", flush=True)
            ResearchEngine(store, read_json(args.config) if args.config else {}).execute(run_id)
            state = store.read(run_id)
            print(dump(state), end="")
            return 0 if state["status"] == "completed" else 2
        elif args.command == "validate":
            record = validate(read_json(args.record))
            print(dump({"valid": True, "findings": len(record["findings"]), "claim_truth": "not_checked"}), end="")
        elif args.command == "render":
            lines = report_lines(read_json(args.record), args.audience)
            if args.format == "pdf":
                pdf_report(args.output, lines)
            else:
                write_new(args.output, markdown(lines) if args.format == "md" else html_report(lines))
            print(f"Saved {args.format} report")
        elif args.command == "import-rea":
            write_new(args.output, dump(rea_record(args.evidence, args.title)))
            print("Imported evidence; findings remain unreviewed")
        elif args.command == "inspect":
            prefix = json.loads(args.rea_command)
            if not isinstance(prefix, list) or not prefix or any(not isinstance(x, str) or not x for x in prefix):
                raise ValueError("--rea-command must be a nonempty JSON array of command strings")
            if not 1 <= args.timeout <= 300:
                raise ValueError("Timeout must be between 1 and 300 seconds")
            if not Path(args.target).exists():
                raise ValueError("Inspection target does not exist")
            if Path(args.output).exists():
                raise ValueError("Output already exists")
            # REA runs only after an explicit inspect command. No model selects executable commands.
            from .processes import bounded_run
            result = bounded_run(prefix + [args.operation, str(Path(args.target).resolve()), "--json"],
                                 timeout=args.timeout, max_output=16 * 1024 * 1024, text=False)
            if len(result.stdout) > 16 * 1024 * 1024:
                raise ValueError("REA output exceeds the 16 MiB retained-output limit")
            envelope = json.loads(result.stdout)
            if not isinstance(envelope, dict) or not envelope.get("evidence_id"):
                raise ValueError("REA did not return an evidence envelope")
            write_new(args.output, dump(envelope))
            print(dump({"saved": True, "rea_exit_code": result.returncode,
                        "evidence_id": envelope["evidence_id"],
                        "inspection_success": "review_raw_evidence_and_coverage"}), end="")
            if result.returncode:
                return 1
        return 0
    except (ValueError, TypeError, OSError, subprocess.SubprocessError) as exc:
        # Do not echo provider output, commands, environment values, or arbitrary exception strings.
        print(f"Operation failed ({type(exc).__name__}). Check inputs, dependencies and output ownership.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
