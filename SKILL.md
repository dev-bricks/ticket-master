---
name: ticket-master
description: "Use when the user wants to keep an open triage console for a software project - capturing bugs/change-requests as structured tickets, scoring them, and routing them to the right AI provider/sub-agent for an immediate fix or into the project's task management. Triggers on /ticket-master or 'open the triage console / ticket master'."
---

# ticket-master — Triage Console Workflow

ticket-master is a **workflow / operating mode**, not a tool that acts on its own.
You (the agent) follow the TICKET-MASTER prompt and stay at **Position 0** — an open
triage console. When the user types a bug, change request, or any project problem,
you capture it, triage it, and route it.

## How to enter this mode

1. **Read the prompt.** Load `prompts/TICKET-MASTER.${TM_LANG:-en}.md` (default `en`;
   `de` is also available) and follow it as your operating instructions for the
   whole session.
2. **Read the config.** Use `config/ticket-master.config.json`. If it does not exist,
   copy it from `config/ticket-master.config.example.json` first, then have the user
   fill in `project_roots[]` and verify the provider commands.
3. **Go to Position 0.** Orient yourself on the configured projects, then wait
   silently for the user's first ticket. Do not act until a ticket arrives.

## The loop (per ticket)

```
capture  -> structured ticket file + intake-log line
triage   -> assign to the right project + score (5 dimensions)
route    -> delegate to best provider/sub-agent for an immediate fix,
            OR file into the project's own task management
back to Position 0 -> wait for the next ticket
```

## Roles

- **Worker:** A sub-agent (or Companion sub-agent reused across a ticket series) does
  the actual reading/editing/verifying and reports back compactly (commit hash + one
  line). You stay lean and route only.
- **Advisor:** For high-stakes tickets (score >= 35), an advisor model reviews before
  changes land (see `advisor` in the config).

The full protocol — decision ladder, score formula, gates, fallback chain,
ticket lifecycle — lives in the prompt. Read it; do not duplicate it here.
