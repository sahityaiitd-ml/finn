# AI build history

FINN was built across three Claude sessions. Read them in this order:

| # | File | Tool | What it covers |
|---|---|---|---|
| 1 | [claude-chat-1-research-and-planning.md](claude-chat-1-research-and-planning.md) | Claude (claude.ai, project "ENAM Holdings") | Reading the brief, user journey maps and pain points, synthetic interviews, first technology planning. |
| 2 | [claude-chat-2-design-and-prd.md](claude-chat-2-design-and-prd.md) | Claude (claude.ai) with sub-agents and the Figma connector | Prioritising the pain points into the MVP, the PRD and implementation plan, the Figma designs (v1 lo-fi → v3 "Calm ledger"), and the Claude Code kickoff prompt. |
| 3 | [claude-code-session.md](claude-code-session.md) | Claude Code | The build itself: milestones M0–M6, the live deploy, the Android app. Instructions, replies and a one-line summary of every tool call. |

For the decisions and dead ends in one place, see [../build-log.md](../build-log.md).

**How these files were made.** Chats 1 and 2 were exported from claude.ai; chat 2 is Claude's own end-of-session write-up of the conversation (user messages verbatim, replies lightly condensed, actions summarised). The Claude Code session was converted from its transcript. In all three, hidden reasoning is not included, and a home-folder path or email address was redacted. All three were scanned for the real values of the project's API keys and for common key patterns before being committed; none were found.
