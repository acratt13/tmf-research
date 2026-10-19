import copy
import json
from pathlib import Path
import tempfile
import unittest
from tmf_research.cli import validate, report_lines, html_report, markdown, rea_record, main


def fixture():
    return {"schema_version": 1, "title": "Test report", "question": "What is known?", "summary": "Bounded evidence.",
            "sources": [{"id": "s1", "title": "Fixture", "state": "partial", "retrieved_at": "2026-10-19T00:00:00Z",
                         "scope": "Selected fields only", "limitations": "No execution"}],
            "findings": [{"text": "A field exists", "label": "observed", "sources": ["s1"], "caveat": "Static metadata only"}],
            "requirements": [{"id": "REQ-1", "text": "Preserve evidence", "acceptance": "Read back the saved source"}],
            "unknowns": ["Runtime behavior"]}


class Reports(unittest.TestCase):
    def test_rejects_missing_source(self):
        data = fixture(); data["findings"][0]["sources"] = ["invented"]
        with self.assertRaises(ValueError): validate(data)

    def test_partial_source_requires_visible_caveat(self):
        data = fixture(); del data["findings"][0]["caveat"]
        with self.assertRaises(ValueError): validate(data)

    def test_unavailable_source_cannot_support_observed_claim(self):
        data = fixture(); data["sources"][0]["state"] = "unavailable"
        with self.assertRaises(ValueError): validate(data)

    def test_rejects_uncited_observation(self):
        data = fixture(); data["findings"][0]["sources"] = []
        with self.assertRaises(ValueError): validate(data)

    def test_rejects_duplicate_source(self):
        data = fixture(); data["sources"].append(copy.deepcopy(data["sources"][0]))
        with self.assertRaises(ValueError): validate(data)

    def test_untrusted_html_is_escaped(self):
        data = fixture(); data["summary"] = '<script>alert("x")</script><img src="https://evil.example/tracker">'
        result = html_report(report_lines(data))
        self.assertNotIn("<script>", result)
        self.assertNotIn("<img", result)
        self.assertIn("&lt;script&gt;", result)

    def test_markdown_cannot_embed_remote_image(self):
        data = fixture(); data["summary"] = "![tracker](https://evil.example/x)"
        result = markdown(report_lines(data))
        self.assertNotIn("![tracker]", result)

    def test_executive_view_keeps_limits_and_evidence(self):
        data = fixture(); lines = report_lines(data, "executive")
        text = "\n".join(text for _, text in lines)
        self.assertIn("Static metadata only", text)
        self.assertIn("No execution", text)
        self.assertNotIn("REQ-1", text)

    def test_render_does_not_overwrite_existing_deliverable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / "input.json"; output = root / "report.md"
            source.write_text(json.dumps(fixture())); output.write_text("Client approved original")
            self.assertEqual(main(["render", str(source), "--output", str(output)]), 1)
            self.assertEqual(output.read_text(), "Client approved original")

    def test_import_does_not_upgrade_coverage_or_invent_findings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rea.json"
            raw = {"evidence_id": "ev_fixture", "normalized_result": {"coverage": {"state": "incomplete"}}, "limitations": ["Skipped source"]}
            path.write_text(json.dumps(raw)); record = rea_record(path, "Fixture")
            self.assertEqual(record["sources"][0]["state"], "partial")
            self.assertEqual(record["findings"], [])
            self.assertIn("incomplete", record["sources"][0]["scope"])
            validate(record)

    def test_rejects_report_without_unknowns_field(self):
        data = fixture(); del data["unknowns"]
        with self.assertRaises(ValueError): validate(data)

    def test_rejects_active_url_scheme(self):
        data = fixture(); data["sources"][0]["url"] = "javascript:alert(1)"
        with self.assertRaises(ValueError): validate(data)


if __name__ == "__main__": unittest.main()
