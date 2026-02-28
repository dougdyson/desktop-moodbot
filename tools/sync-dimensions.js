#!/usr/bin/env node
/**
 * Extracts dimensions from the OpenSCAD enclosure file (source of truth)
 * and writes hardware/dimensions.json for use by the 3D preview and other tools.
 *
 * Usage: node tools/sync-dimensions.js
 *
 * The SCAD file is the single source of truth for all physical dimensions.
 * This script parses the variable assignments, evaluates derived values,
 * and outputs a flat JSON object.
 */

const fs = require('fs');
const path = require('path');

const SCAD_PATH = path.join(__dirname, '..', 'hardware', 'enclosures', 'dtmb_enclosure_v3.scad');
const OUT_PATH = path.join(__dirname, '..', 'hardware', 'dimensions.json');

const scad = fs.readFileSync(SCAD_PATH, 'utf8');

const vars = {};

const lines = scad.split('\n');
for (const line of lines) {
  const trimmed = line.replace(/\/\/.*$/, '').trim();

  const match = trimmed.match(/^(\w+)\s*=\s*(.+?)\s*;$/);
  if (!match) continue;

  const [, name, expr] = match;

  try {
    const value = evalExpr(expr, vars);
    if (typeof value === 'number' && !isNaN(value)) {
      vars[name] = value;
    }
  } catch {
    // skip expressions we can't evaluate (function calls, etc.)
  }
}

function evalExpr(expr, context) {
  let resolved = expr;
  const varNames = Object.keys(context).sort((a, b) => b.length - a.length);
  for (const v of varNames) {
    resolved = resolved.replace(new RegExp(`\\b${v}\\b`, 'g'), `(${context[v]})`);
  }
  if (/[a-zA-Z_]/.test(resolved.replace(/\b(Math|PI|E)\b/g, ''))) {
    throw new Error(`Unresolved: ${resolved}`);
  }
  return Function(`"use strict"; return (${resolved})`)();
}

// Also extract tilt from the assembly section
const tiltMatch = scad.match(/^tilt\s*=\s*(-?\d+(?:\.\d+)?)\s*;/m);
if (tiltMatch) {
  vars.tilt = parseFloat(tiltMatch[1]);
}

const dims = {
  _source: 'hardware/enclosures/dtmb_enclosure_v3.scad',
  _generated: new Date().toISOString(),
  ...vars
};

fs.writeFileSync(OUT_PATH, JSON.stringify(dims, null, 2) + '\n');

console.log(`Extracted ${Object.keys(vars).length} dimensions from SCAD`);
console.log(`Written to ${OUT_PATH}`);
console.log();

const key = [
  'hw_w', 'hw_h', 'hw_d', 'wall', 'tol', 'edge_r',
  'enc_w', 'enc_h', 'enc_d', 'tilt', 'foot_h',
  'hw_disp_w', 'hw_disp_h', 'hw_disp_z', 'disp_cut_z'
];
for (const k of key) {
  if (vars[k] !== undefined) {
    console.log(`  ${k} = ${vars[k]}`);
  }
}
