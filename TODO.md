# TODO — ticket-master

## Near-term

- [ ] Python helper script (`bin/ticket_master.py`) as a thin wrapper that reads
      `config/ticket-master.config.json` and dispatches to the correct provider
      without shell-specific scripts — easier cross-platform maintenance.
- [ ] `--list` mode: print open tickets from `tickets/` to stdout.
- [ ] `--intake "description"` flag: pre-create a ticket file from the command line
      before launching the agent session.
- [ ] Config validation on startup: warn if `project_roots` is empty or provider
      commands are not found in PATH.

## Medium-term

- [ ] Optional TUI dashboard (curses or textual) showing ticket counts per
      lifecycle state.
- [ ] GitHub Issues bridge: pull open issues from a repo into `tickets/` as `.txt`
      files automatically.
- [ ] Webhook receiver: accept tickets via HTTP POST (e.g. from n8n or a CI system).
- [ ] pytest integration: convert `tests/test_smoke.py` to proper pytest suite.

## Long-term / Ideas

- [ ] Multi-repo support: manage tickets across several Git repositories from one
      ticket-master instance.
- [ ] Automatic companion rotation based on context-token watermarks.
- [ ] Web UI for ticket overview and manual routing overrides.
