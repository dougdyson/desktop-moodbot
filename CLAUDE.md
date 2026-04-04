# CLAUDE.md

This file provides guidance to Claude Code when working with the desktop-moodbot repository.

## Project Overview

Desktop Mood Bot (DTMB) is a standalone, lightweight Python service that reads AI coding agent conversation logs, computes a combined mood state (activity x emotion), and pushes it to display subscribers — a dashboard widget via SSE, or an M5Stack CoreInk e-ink display via HTTP.

This is an **open-source product**. No database dependency.

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
    state.py         # 6 activities x 5 emotions matrix + variant pooling
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
- committing/writing -> editing
- testing -> executing
- planning/managing -> thinking
- browsing/delegating -> reading

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

6 activities x 5 emotions = 30 base states, plus variant pooling for high-frequency combos:
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
- 70% of changes happen within 5 minutes -> 5-min polling interval is well-calibrated
- Sentiment mostly oscillates between adjacent bands; large jumps are extremely rare

## Data Sources

- **Claude Code**: `~/.claude/projects/*/*.jsonl`
- **OpenClaw**: `~/.openclaw/agents/main/sessions/*.jsonl`
- Others TBD (Cursor, Gemini CLI, Codex CLI)

Start with Claude Code support only.

## Hardware Target

- **Display**: M5Stack CoreInk — 200x200px black/white e-ink, ESP32-PICO-D4, WiFi, 390mAh battery
- **Housing**: 3D printed, brand-colored per agent
- Simple mascot/smiley style faces, generated not hand-drawn
- Activity shown through expression (eyes scanning = reading, mouth open = talking)
- Emotion shown through valence (smile vs frown, relaxed vs tense)

### CoreInk Physical Specs (CRITICAL — enclosure must match these exactly)

The enclosure wraps the CoreInk hardware. All enclosure dimensions MUST derive from these specs. The reference model lives at `hardware/reference/coreink_reference.scad` — always use it as the source of truth.

**Portrait orientation** (how the device stands on a desk):
- **Width (X)**: 40mm
- **Height (Z)**: 56mm (tall axis)
- **Depth (Y)**: 16mm (thickness)

**Display**: 27.6 x 27.6mm active area, centered horizontally, in the **upper portion** of the front face (center ~36mm from bottom)

**Ports and buttons**:
- USB-C: bottom edge, center
- Dial/button: top edge
- Side button: right side (when facing screen), ~28mm from bottom

**Enclosure design rules**:
- All cutout positions derive from the reference model, not freehand
- Enclosure = shell around hardware + tolerance (0.3mm typical)
- Wall thickness: 2mm (suitable for FDM printers)
- The reference model should be visible as a ghost overlay during design

## ESP32 Communication Protocol

### Endpoint
ESP32 polls `GET /mood/<agent>` (e.g. `/mood/claude-code`). Returns:
```json
{
  "activity": "thinking",
  "emotion": "positive",
  "variant": 2,
  "timestamp": "2026-02-20T14:30:00Z",
  "sleeping": false,
  "bitmap": null
}
```

### Image Transfer
- ~40 sprites preloaded on ESP32 flash (~200KB, ESP32 has 4MB+)
- `bitmap: null` -> use preloaded sprite (activity/emotion/variant lookup)
- `bitmap: "<base64>"` -> server-sent override (~5KB), enables face updates without firmware push

### Discovery
- **mDNS primary**: server advertises as `moodbot.local`, zero config for users
- **IP fallback**: hold side button on boot -> config AP -> set static IP via web page

### WiFi Dropout
1. Connected -> normal mood display
2. Briefly disconnected (< 5 min) -> hold last state (e-ink retains image at zero power)
3. Offline (> 5 min) -> show offline/disconnected face

### OTA Firmware Updates
- ESP32 checks `GET /firmware/latest?device=<agent>` on boot
- If newer version available, downloads and installs (standard ESP32 HTTP OTA)

### Power Management
- **USB powered** (primary): poll every 30 seconds
- **Battery mode** (detected by voltage): deep sleep between polls, wake every 2-3 min
- Deep sleep ~10uA -> battery lasts days; e-ink holds image at zero power

### Sleep Mode
- 30 min of no JSONL activity -> server returns `sleeping: true`
- ESP32 shows sleep face, reduces polling to every 5 minutes
- First new activity wakes on next poll

## Design Principles

- **One device per agent**: No cross-agent complexity. Each moodbot is independent.
- **No database**: Lightweight, stateless — reads JSONL files, computes state, serves via HTTP
- **Plugin architecture**: New agents added by writing a parser. Scoring pipeline is shared.
- **ESP32 polls server**: Simple `GET /mood/<agent>` endpoint. No WebSocket, no push.
- **Docker-first**: `docker run -v ~/.claude:... desktopmoodbot/server` for one-line setup
- **Also supports**: `pip install` + `moodbot serve` CLI

## Development

```bash
pip install -e ".[dev]"
python __main__.py
```

## Port Assignment

**Default port: 9400.**

## Code Style

- No comments unless explicitly requested
- Follow existing patterns
- Type hints on all new functions
- Tests for new functionality
