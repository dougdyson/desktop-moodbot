#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

const OUT = path.join(__dirname, 'sprites');
fs.mkdirSync(OUT, { recursive: true });

const ACTIVITIES = ['thinking', 'conversing', 'reading', 'executing', 'editing', 'system'];
const EMOTIONS = ['negative', 'uneasy', 'neutral', 'positive', 'elated'];
const VARIANT_COUNTS = { negative: 1, uneasy: 2, neutral: 4, positive: 4, elated: 1 };

function circle(cx, cy, r, fill = 'black', stroke = null, strokeWidth = 0) {
  const obj = {
    type: 'circle',
    left: cx,
    top: cy,
    radius: r,
    fill: fill || '',
    stroke: stroke || '',
    strokeWidth: strokeWidth,
    originX: 'center',
    originY: 'center',
    strokeLineCap: 'round'
  };
  return obj;
}

function ellipse(cx, cy, rx, ry, fill = 'black', stroke = null, strokeWidth = 0) {
  return {
    type: 'ellipse',
    left: cx,
    top: cy,
    rx, ry,
    fill: fill || '',
    stroke: stroke || '',
    strokeWidth,
    originX: 'center',
    originY: 'center'
  };
}

function line(x1, y1, x2, y2, strokeWidth = 3, stroke = 'black') {
  return {
    type: 'line',
    x1, y1, x2, y2,
    left: (x1 + x2) / 2,
    top: (y1 + y2) / 2,
    stroke,
    strokeWidth,
    strokeLineCap: 'round',
    fill: '',
    originX: 'center',
    originY: 'center'
  };
}

function bezierPath(points, strokeWidth = 4, fill = '', stroke = 'black') {
  return {
    type: 'path',
    path: points,
    fill: fill || '',
    stroke,
    strokeWidth,
    strokeLineCap: 'round',
    strokeLineJoin: 'round',
    originX: 'center',
    originY: 'center'
  };
}

// --- EMOTION DEFINITIONS ---

function getMouth(emotion, variant = 0) {
  const cx = 100;
  const baseY = 128;
  const vShift = variant * 2; // subtle per-variant shift

  switch (emotion) {
    case 'negative':
      // deep frown
      return bezierPath([
        ['M', 72, baseY - 2], ['Q', cx, baseY - 25, 128, baseY - 2]
      ], 4);

    case 'uneasy':
      // slight worried frown, asymmetric per variant
      if (variant === 0) {
        return bezierPath([
          ['M', 78, baseY], ['Q', cx, baseY - 12, 122, baseY + 3]
        ], 3.5);
      }
      return bezierPath([
        ['M', 75, baseY + 2], ['Q', cx - 5, baseY - 10, 125, baseY]
      ], 3.5);

    case 'neutral':
      // straight or very subtle curve
      if (variant === 0) {
        return bezierPath([['M', 82, baseY], ['L', 118, baseY]], 3);
      } else if (variant === 1) {
        return bezierPath([['M', 80, baseY], ['Q', cx, baseY + 4, 120, baseY]], 3);
      } else if (variant === 2) {
        return bezierPath([['M', 80, baseY], ['Q', cx, baseY - 3, 120, baseY]], 3);
      }
      // variant 3: slightly open mouth
      return bezierPath([['M', 85, baseY - 2], ['Q', cx, baseY + 5, 115, baseY - 2]], 3);

    case 'positive':
      // smile variants
      if (variant === 0) {
        return bezierPath([['M', 70, 125], ['Q', cx, 155, 130, 125]], 4);
      } else if (variant === 1) {
        return bezierPath([['M', 72, 123], ['Q', cx, 150, 128, 123]], 3.5);
      } else if (variant === 2) {
        // gentle closed smile
        return bezierPath([['M', 75, 126], ['Q', cx, 148, 125, 126]], 3.5);
      }
      // variant 3: slight open smile
      return bezierPath([['M', 73, 122], ['Q', cx, 152, 127, 122]], 4);

    case 'elated':
      // big beaming smile
      return bezierPath([
        ['M', 65, 118], ['Q', cx, 162, 135, 118]
      ], 4.5);
  }
}

function getEyes(emotion, activity, variant = 0) {
  const objects = [];

  // base eye positions
  let lx = 72, ly = 80, rx = 128, ry = 80;
  let eyeR = 8;
  let glintR = 2.5;
  let glintOff = 3; // offset from center for glint

  // activity shifts
  switch (activity) {
    case 'thinking':
      lx = 75; ly = 75; rx = 131; ry = 75; // looking up-right
      glintOff = 3;
      break;
    case 'reading':
      ly = 85; ry = 85; // looking down
      break;
    case 'editing':
      lx = 70; ly = 83; rx = 126; ry = 83; // looking down-left
      break;
    case 'executing':
      // focused, slightly narrower spacing
      lx = 76; rx = 124;
      break;
  }

  // per-variant subtle shifts
  lx += (variant % 2) * 2;
  rx += (variant % 2) * 2;

  // emotion modifiers
  switch (emotion) {
    case 'negative':
      eyeR = 6;
      glintR = 1.5;
      break;
    case 'uneasy':
      eyeR = 7;
      break;
    case 'elated':
      eyeR = 10;
      glintR = 3;
      break;
  }

  // special: reading = half-closed eyes (arcs instead of circles)
  if (activity === 'reading') {
    // half-lid effect: draw eyes as circles then add lid lines
    objects.push(circle(lx, ly, eyeR, 'black'));
    objects.push(circle(rx, ry, eyeR, 'black'));
    // eyelid arcs
    objects.push(bezierPath([
      ['M', lx - eyeR - 2, ly - 2], ['Q', lx, ly - eyeR - 4, lx + eyeR + 2, ly - 2]
    ], 2.5));
    objects.push(bezierPath([
      ['M', rx - eyeR - 2, ry - 2], ['Q', rx, ry - eyeR - 4, rx + eyeR + 2, ry - 2]
    ], 2.5));
  } else {
    objects.push(circle(lx, ly, eyeR, 'black'));
    objects.push(circle(rx, ry, eyeR, 'black'));
  }

  // glints (skip for negative — no sparkle)
  if (emotion !== 'negative') {
    objects.push(circle(lx + glintOff, ly - glintOff, glintR, 'white'));
    objects.push(circle(rx + glintOff, ry - glintOff, glintR, 'white'));
  }

  // emotion-specific eye additions
  if (emotion === 'negative') {
    // angry/sad brows — angled down toward center
    objects.push(line(lx - 10, ly - 16, lx + 8, ly - 12, 2.5));
    objects.push(line(rx + 10, ry - 16, rx - 8, ry - 12, 2.5));
  }

  if (emotion === 'uneasy') {
    // worried brows — one raised
    objects.push(line(lx - 8, ly - 14, lx + 6, ly - 16, 2));
    objects.push(line(rx - 6, ry - 16, rx + 8, ry - 14, 2));
  }

  if (emotion === 'elated') {
    // sparkle marks near eyes
    objects.push(line(lx - 16, ly - 10, lx - 12, ly - 14, 1.5));
    objects.push(line(lx - 16, ly - 14, lx - 12, ly - 10, 1.5));
    objects.push(line(rx + 12, ry - 10, rx + 16, ry - 14, 1.5));
    objects.push(line(rx + 12, ry - 14, rx + 16, ry - 10, 1.5));
  }

  return objects;
}

// --- ACTIVITY DECORATIONS ---

function getActivityDecor(activity, emotion, variant = 0) {
  const objects = [];

  switch (activity) {
    case 'thinking':
      // thought bubbles (upper right)
      objects.push(circle(155, 50, 12, '', 'black', 2.5));
      objects.push(circle(143, 68, 6, '', 'black', 2));
      objects.push(circle(137 + variant, 80, 3, 'black'));
      break;

    case 'conversing':
      // speech lines emanating from right side of mouth
      objects.push(line(135, 125, 148, 118, 2));
      objects.push(line(135, 130, 150, 128, 2));
      objects.push(line(135, 135, 148, 138, 2));
      break;

    case 'reading':
      // scanning lines (like text being read) in lower area
      if (variant < 2) {
        objects.push(line(45, 150, 95, 150, 1.5, 'black'));
        objects.push(line(45, 158, 85, 158, 1.5, 'black'));
        objects.push(line(45, 166, 90, 166, 1.5, 'black'));
      } else {
        // alternate: book-like lines
        objects.push(line(50, 152, 90, 152, 1.5, 'black'));
        objects.push(line(110, 152, 155, 152, 1.5, 'black'));
        objects.push(line(50, 160, 85, 160, 1.5, 'black'));
        objects.push(line(115, 160, 150, 160, 1.5, 'black'));
      }
      break;

    case 'executing':
      // terminal prompt > in bottom left
      objects.push(bezierPath([
        ['M', 28, 155], ['L', 40, 163], ['L', 28, 171]
      ], 2.5));
      // cursor blink line
      objects.push(line(45, 156, 45, 170, 2));
      break;

    case 'editing':
      // pencil icon in upper left
      objects.push(line(30, 55, 45, 40, 2.5));
      objects.push(line(45, 40, 48, 43, 2.5));
      objects.push(line(48, 43, 33, 58, 2.5));
      objects.push(line(33, 58, 30, 55, 2.5));
      // pencil tip
      objects.push(line(28, 60, 30, 55, 2));
      break;

    case 'system':
      // gear-like circles in upper right
      objects.push(circle(160, 40, 10, '', 'black', 2));
      objects.push(circle(160, 40, 4, 'black'));
      // small dots around gear
      objects.push(circle(160, 26, 2, 'black'));
      objects.push(circle(160, 54, 2, 'black'));
      objects.push(circle(146, 40, 2, 'black'));
      objects.push(circle(174, 40, 2, 'black'));
      break;
  }

  return objects;
}

// --- SLEEPING ---

function getSleeping() {
  const objects = [];

  // closed eyes — peaceful arcs
  objects.push(bezierPath([['M', 58, 85], ['Q', 72, 95, 86, 85]], 3.5));
  objects.push(bezierPath([['M', 114, 85], ['Q', 128, 95, 142, 85]], 3.5));

  // tiny content smile
  objects.push(bezierPath([['M', 88, 130], ['Q', 100, 138, 112, 130]], 3));

  // Zzz — represented as small z-shaped paths
  // Big Z
  objects.push(bezierPath([
    ['M', 142, 52], ['L', 158, 52], ['L', 142, 68], ['L', 158, 68]
  ], 2.5));
  // medium z
  objects.push(bezierPath([
    ['M', 155, 36], ['L', 166, 36], ['L', 155, 47], ['L', 166, 47]
  ], 2));
  // small z
  objects.push(bezierPath([
    ['M', 163, 23], ['L', 171, 23], ['L', 163, 31], ['L', 171, 31]
  ], 1.5));

  return objects;
}

// --- GENERATE ---

function makeSprite(objects, meta) {
  return {
    version: '5.3.1',
    objects: objects,
    background: '#ffffff',
    _spriteMeta: meta
  };
}

let count = 0;

// Activity × Emotion sprites
for (const activity of ACTIVITIES) {
  for (const emotion of EMOTIONS) {
    const vc = VARIANT_COUNTS[emotion];
    for (let v = 0; v < vc; v++) {
      const objects = [];

      // eyes first (they go behind glints)
      objects.push(...getEyes(emotion, activity, v));
      // mouth
      objects.push(getMouth(emotion, v));
      // activity decoration
      objects.push(...getActivityDecor(activity, emotion, v));

      const filename = `${activity}_${emotion}_${v}.json`;
      const meta = { activity, emotion, variant: v, version: 1 };
      const sprite = makeSprite(objects, meta);

      fs.writeFileSync(path.join(OUT, filename), JSON.stringify(sprite, null, 2));
      count++;
    }
  }
}

// Sleeping sprite
{
  const objects = getSleeping();
  const meta = { activity: 'sleeping', emotion: 'neutral', variant: 0, version: 1 };
  const sprite = makeSprite(objects, meta);
  fs.writeFileSync(path.join(OUT, 'sleeping_0.json'), JSON.stringify(sprite, null, 2));
  count++;
}

console.log(`Generated ${count} sprites in ${OUT}/`);

// Summary
console.log('\nBreakdown:');
for (const act of ACTIVITIES) {
  const totals = EMOTIONS.map(e => VARIANT_COUNTS[e]);
  const sum = totals.reduce((a, b) => a + b, 0);
  console.log(`  ${act}: ${sum} sprites (${EMOTIONS.map((e, i) => `${e}×${totals[i]}`).join(', ')})`);
}
console.log('  sleeping: 1 sprite');
