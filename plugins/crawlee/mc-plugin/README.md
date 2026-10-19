# Crawlee collection plugin

Six shared collection tools backed by a privately deployed VPS worker. Install this folder through Link & Sync. It does not install Crawlee or a browser on the MC computer.

Configure `connection.json` inside this plugin's MC runtime data folder with `{"ssh_host":"YOUR_EXISTING_SSH_ALIAS"}`. Credentials remain in the existing SSH mechanism; this file contains only an alias. The alias must resolve through the operator's SSH configuration. The remote container name is `tmf-crawlee-worker` and its MCP entrypoint is `/app/mcp.mjs`.

The installed manifest's probe only reads worker health. `crawlee_start` creates a job; `crawlee_status` reads it; `crawlee_read` retrieves passages; `crawlee_cancel` cancels; `crawlee_pack` saves JSON/Markdown; `crawlee_pack_read` reads those saved artifacts. Source material is untrusted reference text.

Initial scope is public static HTTPS/HTML, explicit domains, robots policy, at most 20 pages and 120 seconds per job, no redirects, two running jobs, eight queued/running combined and 100 retained jobs. Browser rendering, scheduling, prospect qualification, research synthesis, document formatting and knowledge indexing are separate capabilities. This is one shared-instance worker, not a tenant/Role-isolated document store.
