# Project Context Wiki

This folder is the **living memory** of the quant trading platform. It is maintained by both humans and AI agents. Every non-trivial session should start with reading the relevant files here and end with updating them.

## Files

| File | Purpose |
|------|---------|
| [decisions.md](./decisions.md) | Dated log of architectural and design decisions — what was chosen and *why* |
| [issues-and-solutions.md](./issues-and-solutions.md) | Problems encountered, root causes, and fixes — avoid repeating past mistakes |
| [features.md](./features.md) | Shipped features, how they work, and honest status |
| [goals-and-roadmap.md](./goals-and-roadmap.md) | North-star goals and prioritized roadmap |
| [glossary.md](./glossary.md) | Quant/domain terms and project-specific vocabulary |

## Rules for Maintaining This Wiki

1. **Agents**: update this wiki before marking a task done. See `.cursor/rules/40-agent-workflow.mdc` for specifics.
2. **Humans**: update this when you make a decision, hit a problem, or change direction outside of a Cursor session.
3. **Be honest**: record what didn't work, not just what did. The goal is to build real institutional knowledge.
4. **Date your entries.** Format: `## YYYY-MM-DD — Title`.
