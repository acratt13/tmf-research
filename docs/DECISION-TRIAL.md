# Perplexity decision trial

The optional `decision-trial` command evaluates a versioned Perplexity decision
model on operator-labeled cases. It does not change the research engine's
reviewer, select tools, discard sources, approve findings, or modify MC's existing
Jev/Kev integrations. Live accuracy and latency require actual API calls.

The intended jobs include classifying work, selecting research depth, deciding
which investigations a task needs, selecting requested document formats, and
checking source relevance or claim support. Multiple requested outputs are
separate inclusion decisions, not a forced choice of one format.

## Run

Provision `PERPLEXITY_API_KEY` into the process environment through your secret
manager. The command takes only the variable's **name**; never put a key in a
command argument, case file, configuration, receipt, or source control.
No credential values are read from MC's private storage by this tool.

```bash
python3 -m tmf_research decision-trial examples/decision-trial.json \
  --model pplx-decider-flash-v1.2 --output runs/decisions-flash
python3 -m tmf_research decision-trial examples/decision-trial.json \
  --model pplx-decider-v1.2 --output runs/decisions-standard
```

Use `--key-env VARIABLE_NAME` if the secret manager injects a different name.
The example contains synthetic public-safe routing cases. A case has `id`,
`state`, `instructions`, an `options` mapping, and an `expected` option. Optional
`category` groups its purpose. Instructions must describe the decision and its
evidence boundary. Expected labels stay local and are not sent to the provider.

All selected state, instructions, and options are sent to Perplexity. The output
directory retains the selected cases, so use private ignored `runs/` paths for
client material and select only content approved for that provider.

## What to measure

Each case is one request with one choice question. This keeps independent
candidates separate and avoids grouping changes confounding a model comparison.
The CLI permits at most 40 cases per invocation, with bounded input/output and a
30-second socket timeout. A missing key fails before creating an output folder.
HTTP, transport or malformed response failures stop the run as partial. There
are no automatic retries or provider substitutions. A new output directory is
required on every run; interrupted and previous trials are retained.

`results.json` includes full option probabilities, confidence, request hash,
requested/reported model, observed elapsed time, usage, expected label and match.
`summary.json` includes accuracy, false-support errors, errors at confidence >=
0.9, median/p95 latency and estimated input cost. Missing measurements remain
null. The 0.9 threshold is diagnostic, not an approved automatic-action threshold.
`review.md` lists decisions for inspection. Failed attempts may still incur
provider charges not represented in the successful-response cost estimate.

Use the same cases and grouping for Flash and Standard. Include explicit
contradictions, missing evidence, subtle scope mismatches, ambiguous briefs and
instructions embedded inside source text. Report mistakes by decision category;
an overall score can hide dangerous false support. These small operator-labeled
trials are diagnostic, not independent benchmarks or proof of calibrated
confidence. Correct routing does not establish a good task plan or good research.

The next integration step depends on observed results: record advisory decisions
inside a normal investigation before allowing them to influence acquisition or
publication. Requested actions always remain subject to existing permissions.

Protocol and published prices checked 2026-10-19:
[Perplexity Decisions API](https://docs.perplexity.ai/docs/decisions/quickstart).
Flash v1.2: $0.01 per million input tokens; Standard v1.2: $0.02; output free.
Pricing in receipts is an estimate using these rates, not a billing statement.
