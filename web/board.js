// Minimal SVG chess board with move arrows.

import { PIECES } from "./pieces.js";

const SQ = 45;
const LIGHT = "#efdcb8", DARK = "#b88a62";
const pieceSvg = Object.fromEntries(Object.entries(PIECES).map(([k, v]) => [k, v.replace(/ id="[^"]*"/, "")]));

function arrow(from, to, flip, color) {
  const c = (sq) => {
    let f = sq.charCodeAt(0) - 97, r = 7 - (parseInt(sq[1], 10) - 1);
    if (flip) { f = 7 - f; r = 7 - r; }
    return [f * SQ + SQ / 2, r * SQ + SQ / 2];
  };
  const [x1, y1] = c(from), [x2, y2] = c(to);
  const ang = Math.atan2(y2 - y1, x2 - x1), head = 16, w = 8;
  const bx = x2 - head * Math.cos(ang), by = y2 - head * Math.sin(ang);
  const px = (w * Math.sin(ang)), py = (w * Math.cos(ang));
  return `<line x1="${x1}" y1="${y1}" x2="${bx}" y2="${by}" stroke="${color}" stroke-width="8" stroke-linecap="round" opacity=".85"/>` +
    `<polygon points="${x2},${y2} ${bx + px},${by - py} ${bx - px},${by + py}" fill="${color}" opacity=".85"/>`;
}

export function boardSvg(fen, { flip = false, arrows = [] } = {}) {
  const rows = fen.split(" ")[0].split("/");
  let out = `<svg viewBox="0 0 ${8 * SQ} ${8 * SQ}" xmlns="http://www.w3.org/2000/svg" role="img">`;
  for (let r = 0; r < 8; r++) {
    for (let f = 0; f < 8; f++) {
      const x = (flip ? 7 - f : f) * SQ, y = (flip ? 7 - r : r) * SQ;
      out += `<rect x="${x}" y="${y}" width="${SQ}" height="${SQ}" fill="${(r + f) % 2 ? DARK : LIGHT}"/>`;
    }
  }
  rows.forEach((row, r) => {
    let f = 0;
    for (const ch of row) {
      if (/\d/.test(ch)) { f += parseInt(ch, 10); continue; }
      const x = (flip ? 7 - f : f) * SQ, y = (flip ? 7 - r : r) * SQ;
      out += `<g transform="translate(${x},${y})">${pieceSvg[ch]}</g>`;
      f++;
    }
  });
  for (let i = 0; i < 8; i++) {
    const file = String.fromCharCode(97 + (flip ? 7 - i : i)), rank = flip ? i + 1 : 8 - i;
    out += `<text x="${i * SQ + SQ - 3}" y="${8 * SQ - 3}" font-size="9" text-anchor="end" fill="${(7 + i) % 2 ? LIGHT : DARK}">${file}</text>`;
    out += `<text x="2" y="${i * SQ + 10}" font-size="9" fill="${i % 2 ? LIGHT : DARK}">${rank}</text>`;
  }
  for (const a of arrows) out += arrow(a.from, a.to, flip, a.color);
  return out + "</svg>";
}
