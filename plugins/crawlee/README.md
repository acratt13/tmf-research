# Remote Crawlee collection worker

This optional plugin collects public static HTML, Markdown and plain text into retained evidence and source packs. It requests Markdown when the source supports it, retaining code samples and links as text. HTML pages retain scoped link discovery; Markdown/plain text do not automatically enqueue links. It does not run the research council, qualify leads, send outreach, render JavaScript, interpret financial data or index a knowledge base.

## Install

Requires Docker on a remote Linux host, an existing SSH alias on the MC host, and Node 22+ for the small local bridge. Keep SSH credentials in your existing SSH mechanism.

1. Copy this worker directory to the remote host. Build with `docker build -t tmf-crawlee:0.1.1 .`.
2. Create storage with `docker volume create tmf-crawlee-data`.
3. Run the container:

```sh
docker run -d --name tmf-crawlee-worker --restart unless-stopped \
  --read-only --tmpfs /tmp:rw,size=64m \
  --mount source=tmf-crawlee-data,target=/data \
  --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 128 --memory 768m --memory-swap 1g --cpus 1 \
  --log-opt max-size=10m --log-opt max-file=3 tmf-crawlee:0.1.1
```

No container ports are published. The bridge runs the remote MCP entrypoint through SSH and `docker exec`. Only trusted operators should hold that remote Docker access.

4. Import **only `mc-plugin/`** through MC Link & Sync. Importing the worker directory would unnecessarily stage Crawlee dependencies locally.
5. Save `{"ssh_host":"YOUR_EXISTING_SSH_ALIAS"}` as `connection.json` in MC's runtime data folder for this package, not its immutable installed source folder. Run the installed plugin test.
6. Enable it through the normal Builders/agent Role controls as appropriate. Import and a passed health probe do not establish a live agent turn.

## Verify

```sh
node --test plugins/crawlee/test/*.test.mjs
CRAWLEE_CONFIG=/absolute/private/connection.json \
  python3 plugins/crawlee/test/smoke.py https://YOUR_ALLOWED_DOCS_HOST/documentation
```

The live smoke test creates a bounded job, waits for completion, reads source passages, creates JSON/Markdown packs, checks artifact hashes and cancels a second job. It prints a receipt including source text; keep receipts private when collecting private business context. Use only a permitted public static HTML URL. A fresh isolated MC test needs its own connection configuration and SSH access.

Each source retains URL, retrieval time, body/text hashes, extraction limitations and robots-policy evidence. Passage reads verify the saved text hash. Packs retain unavailable sources and explicit limits. Retrieval time is not a source's effective date.

## Boundaries and operations

- Exact allowed domains, HTTPS/443, no credentials in URLs, no IP literals or redirects. DNS is validated and supplied directly to the HTTP connection. IPv6 is unsupported.
- Robots is required and unavailable policies fail closed. Crawl delays above two seconds are refused. Each job runs serially, up to 20 pages, 1 MB per response and 120 seconds. These bounds intentionally trade coverage for a small acquisition surface.
- Two running jobs, eight running/queued combined, and 100 retained jobs. There is no automatic deletion or resumption; interrupted work remains interrupted. The Docker volume is the durable storage and needs an operator backup/retention policy.
- One worker serves one trusted MC instance. This is **not** a tenant-isolated or per-Role document store. Do not share its connection across clients.
- Source content is untrusted reference data. It must not grant tools, change instructions or become approved guidance merely by being collected.
- After replacing the worker, MC may hold a disconnected MCP client. Reapply this package's connection environment through its normal settings to reconnect, then rerun its test. No whole-MC restart is necessary.
- Dependencies are pinned in the lockfile. `npm audit` is one signal, not a security approval; unavailable independent scanning must be reported as unknown.

See [knowledge-pack design](../../docs/KNOWLEDGE-PACKS.md) for the next layer: approved procedures and role-specific retrieval through the existing KB governance.
