# Sprite Design Vocabulary

## The Mixing Desk Model

Instead of bundling all visual decisions per emotion ("uneasy = smaller eyes + worried brows + slight frown"), we separate expression into independent **channels**. Each channel controls one expressive dimension. Faces are composed by setting each channel independently, then combining.

## The 8 Channels

| Channel | Feature | What it communicates | Primary driver |
|---------|---------|---------------------|----------------|
| Curvature | Mouth curve up/down | "How are things going?" | Emotion band |
| Shape | Mouth closed-line vs. open oval | "How engaged/activated am I?" | Activity or emotion |
| Symmetry | Mouth straight vs. crooked | "How sure am I about how I feel?" | Emotion nuance |
| Eye size | Pupil radius | Intensity / arousal | Emotion intensity |
| Gaze | Pupil position within eye socket | "Where am I looking?" | Activity state |
| Lids | Open vs. half-closed eyelids | Energy / focus level | Activity |
| Brows | Angle, height, presence | Emotional intensifier | Emotion (sparse) |
| Glints | Highlight dots in eyes | Liveliness / spark | Emotion |

## Channel Details

### Curvature (primary valence indicator)

The main slider. What the user reads first. The bezier control point Y moves on a spectrum:

```
deep frown  <--  slight frown  <--  flat  -->  gentle smile  -->  big smile  -->  grin
   -1.0           -0.3              0.0          0.2               0.5            0.8
```

Maps directly to the five emotion bands. This is already well-established in the current renderer.

### Symmetry (uncertainty axis)

The key to making uneasy feel like its own thing rather than "diet sad." An asymmetric mouth reads as *uncertainty* — one corner stays neutral, the other dips or rises slightly. Humans do this instinctively: the lopsided "ehh" expression.

- **Symmetric**: clear emotional state (confident smile, definite frown)
- **Asymmetric**: ambiguous state (crooked line, one corner dipping)
- **Smirk**: one-sided smile, reads as wry/knowing

For the uneasy band: instead of a tiny symmetric frown, use an angled mouth — one corner staying roughly neutral, the other dipping down, maybe a bit of curvature at the high end. This gives uneasy its own personality instead of being a weaker version of negative.

### Shape (mouth openness)

Adds a second dimension to the mouth. Currently every mouth is a single bezier line. An open mouth — drawn as two bezier curves forming an oval or O-shape — expresses surprise, active speech, or high energy.

- **Closed line**: default, calm, neutral
- **Slightly open**: engaged, talking, warm smile
- **Open oval**: surprised, excited, big laugh

This creates variety within a band. A conversing+positive face could have a gently open smile. An executing+elated face could have a wide-open grin. Four positive variants that actually feel different instead of four nearly-identical smiles with 3px coordinate shifts.

### Gaze (attention direction)

The single biggest expressiveness upgrade. Switch from solid black eye circles to a white eye socket with a black pupil inside. Pupil moves independently within the socket to show where attention is directed.

Activity mappings:
- **Thinking**: pupils up and to the right (looking into the distance)
- **Reading**: pupils slightly down, maybe offset left-to-right (scanning)
- **Editing**: pupils down-left (looking at work in progress)
- **Executing**: pupils center, direct (watching output)
- **Conversing**: pupils forward (making eye contact with the user)
- **System**: varies — catch-all state

Gaze direction is one of the most powerful expressive cues humans read. This is how activity becomes visible without needing props or icons.

### Lids (energy level)

Currently only reading gets half-lids. But lid position is a useful secondary lever:

- **Full open**: alert, excited, engaged
- **Half-lidded**: relaxed, contemplative, chill
- **Slightly narrowed**: focused, scrutinizing

Not on every face, but useful for distinguishing variants. A calm positive (half-lids + gentle smile) feels very different from an energetic positive (wide open + big grin).

### Brows (emotional intensifier)

Used sparingly. Not on every face. When they appear, they carry weight:

- **Slight single raise**: curious, intrigued (good for a neutral variant)
- **Both raised**: surprised, delighted (good for elated or sudden positive)
- **Angled inward**: frustrated, angry (current negative brows — keep)
- **Angled outward**: worried, concerned (current uneasy brows — keep but more subtle)
- **Absent**: the default for most faces

### Eye Size (arousal/intensity)

Current system works well:
- **Small** (12-14px radius): squinting, focused, negative states
- **Normal** (16px): baseline
- **Large** (20px): wide-eyed, alert, elated

### Glints (liveliness)

Current system works well:
- **Present**: alive, engaged (default for all except negative)
- **Absent**: dull, flat affect (negative only)
- **Extra sparkles**: joyful, elated (current x-marks beside eyes)

## How Channels Combine

Emotion controls the mouth and eye decorations. Activity controls the gaze. Variants mix in the secondary channels (symmetry, shape, lids, brows) to create distinct faces within the same band.

Example combinations:

| Activity | Emotion | Curvature | Symmetry | Shape | Gaze | Lids | Brows |
|----------|---------|-----------|----------|-------|------|------|-------|
| Thinking | Positive | gentle smile | symmetric | closed | up-right | open | -- |
| Reading | Uneasy | -- | asymmetric (one corner down) | closed | down | half | slight worry |
| Executing | Elated | big grin | symmetric | open | center | wide | raised |
| Conversing | Neutral | flat line | symmetric | closed | forward | open | -- |
| Editing | Positive v2 | smile | slight smirk | closed | down-left | open | one raised |
| Thinking | Negative | frown | symmetric | closed | up-right | open | angry |
| Conversing | Positive v3 | smile | symmetric | slightly open | forward | open | -- |
| Reading | Neutral v2 | gentle curve | symmetric | closed | down | half-lid | -- |
| Executing | Uneasy | -- | asymmetric | closed | center | slightly narrow | -- |
| System | Positive | smile | symmetric | closed | varies | open | -- |

## Variant Strategy

Variants use the secondary channels to differentiate faces within the same (activity, emotion) pair:

- **Positive (4 variants, 45% dwell)**: needs the most variety
  - v0: classic symmetric smile, closed mouth
  - v1: gentle open-mouth smile (shape channel)
  - v2: slight smirk, one brow raised (symmetry + brows)
  - v3: wide grin, wide-open eyes (shape + lids)

- **Neutral (4 variants, 35% dwell)**: subtle differences
  - v0: flat line, default everything
  - v1: very slight upward curve, relaxed
  - v2: very slight downward curve
  - v3: flat line, one brow slightly raised (curious)

- **Uneasy (2 variants, 15% dwell)**: asymmetry is the signature
  - v0: asymmetric mouth (one corner dips), subtle worry brows
  - v1: slightly crooked line, no brows (milder uncertainty)

- **Negative (1 variant, ~2% dwell)**: committed frown, angry brows, no glints
- **Elated (1 variant, ~3% dwell)**: big open grin, wide eyes, sparkles, raised brows

## Implementation Notes

### Eye socket + pupil (replacing solid circles)

Current: `draw_circle(cx, cy, eye_r, fill=0)` — solid black dot.

Proposed: white-filled circle with black outline (the socket), plus a smaller filled circle inside (the pupil). Pupil position offset from socket center based on activity.

```
Socket: draw_circle(cx, cy, socket_r, fill=255, outline=0, width=3)
Pupil:  draw_circle(cx + gaze_dx, cy + gaze_dy, pupil_r, fill=0)
Glint:  draw_circle(cx + gaze_dx + 3, cy + gaze_dy - 3, glint_r, fill=255)
```

Socket radius ~20-22px, pupil radius ~10-12px, leaving room for visible gaze shifts of 4-6px in any direction.

### Asymmetric mouth

For uneasy/uncertain expressions, use two separate bezier segments meeting at center rather than one symmetric curve:

```
Left half:  bezier(left_x, left_y) -> (cx, mid_y_left) -> (cx, center_y)
Right half: bezier(cx, center_y) -> (cx, mid_y_right) -> (right_x, right_y)
```

Where `left_y != right_y` creates the asymmetric angle.

### Open mouth

Two bezier curves — one for upper lip, one for lower lip — with a filled black region between them:

```
Upper lip: bezier(left, mid) -> (cx, top_ctrl) -> (right, mid)
Lower lip: bezier(left, mid) -> (cx, bot_ctrl) -> (right, mid)
Fill the enclosed region black.
```

The gap between `top_ctrl` and `bot_ctrl` controls how open the mouth is.

## Parking Lot (future ideas)

- **Continuous mouth curvature**: mouth curve proportional to raw sentiment score instead of discrete 5-band snapping. Would require faster polling and partial e-ink redraws. Interesting but not needed short-term — 17.5 band changes per 100 messages with 2-minute median intervals already feels alive.
- **Blinking animation**: periodic eye-close frame for "alive" feel. Would need firmware support for timed frame swaps on the ESP32.
- **Cheek marks**: small diagonal lines under eyes for embarrassment or warmth. Very anime. Could be fun for elated.
