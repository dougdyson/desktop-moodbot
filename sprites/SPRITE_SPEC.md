# Sprite Specification for Desktop Mood Bot

## Canvas
- **Size:** 200 x 200 pixels
- **Color:** Black and white only (1-bit, no grayscale)
- **Format:** PNG
- **Margin:** ~10px clear margin around character

## Display Hardware
- M5Stack CoreInk: 200x200px black/white e-ink display
- No grayscale — pixels are either black or white
- High contrast looks best on e-ink

## File Naming Convention
```
{activity}_{emotion}_{variant}.png
```
Examples: `thinking_neutral_0.png`, `conversing_positive_1.png`

Special: `sleeping_0.png` (used when agent is inactive for 30+ minutes)

## States to Create

### Activities (what the agent is doing)
| Activity    | Description                        |
|-------------|------------------------------------|
| thinking    | Extended thinking / reasoning      |
| conversing  | Talking to the user                |
| reading     | Reading files, searching code      |
| executing   | Running commands, tests            |
| editing     | Writing or editing code/files      |
| system      | Git operations, task management    |

### Emotions (how the agent feels)
| Emotion  | Sentiment Range | Frequency |
|----------|----------------|-----------|
| negative | < -0.35        | ~2%       |
| uneasy   | -0.35 to -0.10 | ~15%      |
| neutral  | -0.10 to 0.15  | ~35%      |
| positive | 0.15 to 0.45   | ~45%      |
| elated   | > 0.45         | ~3%       |

### Variant Counts per Emotion
| Emotion  | Variants | Files needed |
|----------|----------|-------------|
| negative | 1        | 1 per activity |
| uneasy   | 2        | 2 per activity |
| neutral  | 4        | 4 per activity |
| positive | 4        | 4 per activity |
| elated   | 1        | 1 per activity |

### Priority Sprites (most common states)
These combos appear most often — create these first:

1. **thinking_neutral** (0-3) — 4 variants
2. **thinking_positive** (0-3) — 4 variants
3. **conversing_positive** (0-3) — 4 variants
4. **conversing_neutral** (0-3) — 4 variants
5. **reading_neutral** (0-3) — 4 variants
6. **reading_positive** (0-3) — 4 variants
7. **executing_neutral** (0-3) — 4 variants
8. **executing_positive** (0-3) — 4 variants
9. **sleeping_0** — 1 sprite

Total priority: 33 sprites

### Full Set
6 activities x (1 + 2 + 4 + 4 + 1) = 6 x 12 = 72 sprites + 1 sleeping = 73 total

### Fallback Behavior
If a sprite is missing, the system falls back:
1. Same activity + emotion, variant 0
2. thinking + same emotion, variant 0
3. No bitmap (device shows preloaded default)

So you can start with just the priority set and fill in over time.

## Design Guidelines
- Character should convey the emotion clearly at small size
- Variants should be noticeably different (different pose, expression, gesture)
- Activities can be shown through props or body language:
  - thinking: hand on chin, thought bubble, eyes up
  - conversing: speech bubble, open posture, waving
  - reading: book/magnifying glass, focused eyes
  - executing: running, gears, lightning bolt
  - editing: pencil, typing gesture
  - system: wrench, gear, clipboard
- sleeping: eyes closed, zzz, curled up
- Keep the style consistent across all sprites
