# CLAUDE.md

This file provides guidance to Claude Code when working with the desktop-moodbot repository.

## CRITICAL: Two Contexts — Don't Confuse Them

This project has two distinct contexts. Mixing them up causes real problems.

### 1. THE PRODUCT (code in this repo)
Desktop Mood Bot is a **standalone, lightweight Python service** with **no database**. It reads JSONL files, computes mood state, pushes to displays. The product code in this repo must never depend on PostgreSQL, Ziggy, or kokoro-tts.

### 2. PROJECT MANAGEMENT (external infrastructure)
We track todos, requirements, and project entities in an **external PostgreSQL database called `ada`**, managed via MCP tools and the kokoro-tts codebase. This is how Duggy manages all his projects — it's the project management system, not part of the product.

**Rule of thumb**: If you're writing product code (sentiment scoring, file watching, publishers), you're in Context 1. If you're creating todos, updating entities, or checking requirements, you're in Context 2.

---

# Context 1: The Product

## Project Overview

Desktop Mood Bot (DTMB) is a standalone, lightweight Python service that reads AI coding agent conversation logs, computes a combined mood state (activity × emotion), and pushes it to display subscribers — a dashboard widget via SSE, or an M5Stack CoreInk e-ink display via HTTP.

This is an **open-source product**. No database, no Ziggy dependency, no kokoro-tts dependency.

## Key Design Decision: One Device Per Agent

Each moodbot is dedicated to a **single agent**. A Claude Code moodbot only shows Claude Code mood. An OpenClaw moodbot only shows OpenClaw mood. Users collect the ones matching the agents they use.

This means:
- No cross-agent arbitration ("which agent should I show?")
- Each agent has its own watcher, parser, and HTTP endpoint
- Devices are fully independent: `GET /mood/claude-code`, `GET /mood/openclaw`
- Each ESP32 is flashed knowing which agent it represents, polls its own endpoint
- Adding a new agent = new parser file + new route. Scoring pipeline is shared.

## Architecture

```
desktop-moodbot/
  core/              # Mood state computation (shared across agents)
    sentiment.py     # VADER scoring + rolling window + hysteresis
    activity.py      # Tool-use classification into Big 6 states
    state.py         # 6 activities × 5 emotions matrix + variant pooling
  parsers/           # Agent-specific JSONL parsers
    base.py          # Abstract parser interface
    claude_code.py   # Claude Code JSONL parser
    openclaw.py      # OpenClaw JSONL parser (future)
  watcher/           # File watcher — one per agent, polls JSONL files
  server/            # HTTP server exposing /mood/<agent> endpoints
  config/            # YAML config for agent paths, display targets
```

## Data Model

### Activity States: The Big 6 (94.2% coverage)

Derived from analysis of 68,475 real events across 1,110 Claude Code sessions.

| State | Source Activities | % of Events |
|-------|------------------|-------------|
| Thinking | thinking blocks | 34.6% |
| Conversing | text blocks | 22.0% |
| Reading | Read, Grep, Glob, WebSearch | 17.0% |
| Executing | Bash (non-git, non-test) | 14.8% |
| Editing | Edit, Write | 6.9% |
| System | committing, testing, planning, delegating, browsing | 4.7% |

Long-tail collapse rules:
- committing/writing → editing
- testing → executing
- planning/managing → thinking
- browsing/delegating → reading

### Emotion Bands: 5 (collapsed from 9)

Transition matrix confirmed adjacency-only movement. 9 bands had imperceptible visual differences.

| Band | Score Range | Dwell % |
|------|------------|---------|
| Negative | lowest | ~2% |
| Uneasy | low | ~15% |
| Neutral | middle | ~35% |
| Positive | high | ~45% |
| Elated | highest | ~3% |

### Visual State Matrix

6 activities × 5 emotions = 30 base states, plus variant pooling for high-frequency combos:
- Neutral (35% dwell): 3-4 variants
- Positive (45% dwell): 3-4 variants
- Uneasy (15% dwell): 2 variants
- Negative/Elated (rare): 1 each

**Total: ~40 visual treatments.**

## Sentiment Scoring Pipeline

1. **Parse**: Extract assistant messages (type=text), skip tool_use/thinking blocks
2. **Filter**: Remove tool call messages, messages < 20 chars
3. **Truncate**: Cap at 1,500 chars per message
4. **Score**: VADER compound score (-1 to +1)
5. **Weight**: Emotional weight (0.2-1.0) based on emotional vs technical signal density
6. **Window**: Rolling 15-message weighted average
7. **Hysteresis**: 0.08 threshold to prevent band flickering
8. **Band**: Map to 5-level emotion scale

## Key Calibration Numbers

- 17.5 band changes per 100 messages
- Mean 2.8 changes per session
- Median time between band changes: 2.0 minutes
- 70% of changes happen within 5 minutes → 5-min polling interval is well-calibrated
- Sentiment mostly oscillates between adjacent bands; large jumps are extremely rare

## Data Sources

- **Claude Code**: `~/.claude/projects/*/*.jsonl`
- **OpenClaw**: `~/.openclaw/agents/main/sessions/*.jsonl`
- Others TBD (Cursor, Gemini CLI, Codex CLI)

Start with Claude Code support only.

## Hardware Target

- **Display**: M5Stack CoreInk — 200×200px black/white e-ink, ESP32-PICO-D4, WiFi, battery
- **Housing**: 3D printed (Creality Ender 3), brand-colored per agent
- Simple mascot/smiley style faces, generated not hand-drawn
- Activity shown through expression (eyes scanning = reading, mouth open = talking)
- Emotion shown through valence (smile vs frown, relaxed vs tense)

## Design Principles

- **One device per agent**: No cross-agent complexity. Each moodbot is independent.
- **No database**: Lightweight, stateless — reads JSONL files, computes state, serves via HTTP
- **Plugin architecture**: New agents added by writing a parser. Scoring pipeline is shared.
- **ESP32 polls server**: Simple `GET /mood/<agent>` endpoint. No WebSocket, no push.
- **Docker-first**: `docker run -v ~/.claude:... desktopmoodbot/server` for one-line setup
- **Also supports**: `pip install` + `moodbot serve` CLI

## Code Style

- No comments unless explicitly requested
- Follow existing patterns
- Type hints on all new functions
- Tests for new functionality

---

# Context 2: Project Management Infrastructure

Everything below is about how we **manage this project** — tracking todos, requirements, and entities. None of this belongs in the product code.

## Ada Database Access

Project metadata, todos, and entities live in the **ada** PostgreSQL database (shared across all of Duggy's projects).

```bash
psql -d ada
```

**NEVER use `psql -d postgres`** — that's the system database.

When running Python scripts that need database access (psycopg2, etc.), use the kokoro-tts conda environment:

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/kokoro-tts-py310/bin/python script.py
```

**NEVER use bare `python` or `python3`** — they won't have psycopg2 or other database dependencies.

## Todo Management — Use MCP Server

**ALWAYS use the MCP todo server (`mcp__todo-server__todo_add`) to create todos, NOT direct SQL.**

Why:
- MCP server automatically creates timeline entries for new todos
- Direct SQL bypasses timeline logging, breaking daily briefings
- MCP server handles task_number assignment automatically

**Duggy is on 6-week medical leave. NEVER create todos with task_type='work'.**

When creating todos via MCP server:
- ALWAYS set `task_type: "personal"`
- Vacation mode filters out work tasks from the UI

**Linking todos to this project:** After creating via MCP, do TWO things:

1. Link to the Desktop Mood Bot project entity:
```sql
INSERT INTO entity_relationships (from_entity_id, to_entity_id, relationship_type)
VALUES ('<new_todo_entity_id>', 'f50748b6-74e9-4ee0-a344-91ad9b63cee9', 'belongs_to');
```

2. Add to the frontlog (if it's an active priority) via REST endpoint:
```bash
# Get current frontlog
curl http://localhost:8765/v1/frontlog

# Replace frontlog with new ordered list
curl -X POST http://localhost:8765/v1/frontlog \
  -H "Content-Type: application/json" \
  -d '[{"item_type": "todo", "task_number": 1152}, {"item_type": "todo", "task_number": 1161}]'
```

Other useful frontlog endpoints:
- `POST /v1/frontlog/autofill` — auto-populate with ranked items
- `POST /v1/frontlog/refresh` — rebuild from scratch
- `POST /v1/frontlog/dismiss` — "not right now" with TTL

The frontlog is a **curated, ordered list** — creating a todo and linking it to the project does NOT automatically add it to the frontlog. The frontlog is what drives the ziggy-web UI and session planning.

Project entity ID: `f50748b6-74e9-4ee0-a344-91ad9b63cee9`

## Entity CRUD — Use Service Functions

**ALWAYS use `db/entities/core.py` functions (in kokoro-tts repo) for entity operations, NOT raw SQL.**

Why:
- `create_entity()` logs to timeline AND generates summary + summary_embedding
- `update_entity()` logs to timeline AND regenerates summary/embedding
- Raw SQL bypasses both

For relationships, raw SQL is fine.

## Branch Naming & Workflow

**ALWAYS create a feature branch when working on ANY todo. NEVER commit work directly to main.**

### Branch naming convention:
```
feature/{task_number}-{slugified-todo-title}
```

Examples:
- Todo #1150 "Create desktop-moodbot standalone repo + architecture" → `feature/1150-create-desktop-moodbot-standalone-repo-architecture`

**The FIRST thing you do after picking up a todo is `git checkout -b feature/{task_number}-{slug}`. Do this BEFORE writing any code.**

### Todo completion protocol:

**Only mark a todo as completed when the feature branch is merged into main.**

Do NOT complete todos when:
- Making commits during development
- Finishing a coding session
- The feature "works" but hasn't been merged

Workflow:
1. Create feature branch: `feature/{task_number}-{slug}`
2. Make commits as needed (todo stays open)
3. When work is complete, **ask user to initiate close-out**
4. User approves → merge to main + mark todo as completed

**Close-out (merge + complete) is a shared decision. Never merge to main or mark a todo as completed without explicit user approval.**

## No Destructive Operations Without Approval

**NEVER DELETE, UPDATE, or modify production data without explicit user approval.**

Before any destructive database operation:
1. Show what will be affected (run a SELECT first)
2. Ask for approval before executing
3. Use precise filters (date, specific IDs)
4. Prefer soft deletes (`is_active = FALSE`)
