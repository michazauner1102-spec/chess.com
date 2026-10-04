// Aggregate analysed games into a player profile. Port of chess_trainer/profile.py.

import { DIMS, GRANDMASTERS, TAGS } from "./data.js";

const clamp = (x) => Math.max(0, Math.min(1, x));
const avg = (xs) => { xs = xs.filter((x) => x !== null && x !== undefined); return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0; };
const count = (arr, key) => arr.reduce((m, x) => { const k = key(x); m[k] = (m[k] || 0) + 1; return m; }, {});
const dist = (a, b) => Math.sqrt(a.reduce((s, x, i) => s + (x - b[i]) ** 2, 0));

function shortOpening(name) {
  const cut = name.split(/\s+/).filter((w) => !/\d/.test(w));
  return cut.slice(0, 4).join(" ") || name;
}

export function buildProfile(games) {
  const n = games.length;
  const my = games.flatMap((g) => g.moves);
  const total = my.length || 1;
  const outcomes = count(games, (g) => g.outcome);
  const byColor = {};
  for (const c of ["white", "black"]) byColor[c] = count(games.filter((g) => g.color === c), (g) => g.outcome);

  const classes = count(my, (m) => m.class);
  const errors = my.filter((m) => m.class === "Fehler" || m.class === "Patzer");
  const tagCount = {};
  for (const m of errors) for (const t of m.tags) tagCount[t] = (tagCount[t] || 0) + 1;
  const phaseMoves = count(my, (m) => m.phase);
  const phaseErrors = count(errors, (m) => m.phase);
  const phaseAcc = {}, phaseErr = {};
  for (const p of Object.keys(phaseMoves)) {
    phaseAcc[p] = +avg(my.filter((m) => m.phase === p).map((m) => m.accuracy)).toFixed(1);
    phaseErr[p] = +(100 * (phaseErrors[p] || 0) / phaseMoves[p]).toFixed(1);
  }

  const f = games.map((g) => g.features);
  const sum = (k) => f.reduce((a, x) => a + (x[k] || 0), 0);
  const captureRate = sum("captures") / total;
  const checkRate = sum("checks") / total;
  const storm = sum("pawn_storm") / n;
  const sacs = sum("sound_sacs") / n;
  const earlyQ = f.filter((x) => x.early_queen).length / n;
  const castled = f.filter((x) => x.castle_move);
  const castleRate = castled.length / n;
  const castleAvg = avg(castled.map((x) => x.castle_move));
  const longC = castled.filter((x) => x.castle_side === "lang").length / (castled.length || 1);
  const opposite = castled.filter((x) => x.opp_castle_side && x.opp_castle_side !== x.castle_side).length / n;
  const qtEarly = f.filter((x) => x.queen_trade_move && x.queen_trade_move <= 20).length / n;
  const avgLen = avg(games.map((g) => g.n_moves));
  const decisive = ((outcomes.win || 0) + (outcomes.loss || 0)) / n;
  const mateWins = games.filter((g) => g.outcome === "win" && g.end_reason === "checkmated").length / n;
  const blunderRate = (classes.Patzer || 0) / total;
  const errRate = errors.length / total;
  const egMoves = phaseMoves.Endspiel || 0;
  const egErr = egMoves ? (phaseErrors.Endspiel || 0) / egMoves : errRate;

  const style = {
    angriff: clamp(0.2 + 2.0 * checkRate + 0.08 * storm + 0.5 * sacs + 0.5 * opposite + 0.3 * mateWins + 0.3 * longC),
    position: clamp(0.35 + 0.5 * (1 - captureRate / 0.35) + 0.25 * castleRate + (avgLen - 35) / 80 - 0.4 * earlyQ),
    endspiel: clamp(0.45 + 6 * (errRate - egErr) + 0.4 * (egMoves / total)),
    schaerfe: clamp(0.15 + 0.35 * decisive + 0.6 * opposite + 0.3 * sacs + 0.1 * storm - 0.4 * qtEarly),
    solide: clamp(1.05 - 15 * blunderRate - 0.3 * earlyQ + 0.1 * castleRate - 0.2 * opposite),
  };
  const vec = DIMS.map((d) => style[d]);
  let archetype = "universal";
  if (style.angriff + style.schaerfe >= style.position + style.solide + 0.15) archetype = "angreifer";
  else if (style.position + style.solide >= style.angriff + style.schaerfe + 0.15) archetype = "positionell";

  const gmMatches = [...GRANDMASTERS].sort((a, b) => dist(vec, a.vec) - dist(vec, b.vec)).slice(0, 4)
    .map((gm) => ({ ...gm, match: Math.round(100 * (1 - dist(vec, gm.vec) / Math.sqrt(DIMS.length))) }));

  const op = {};
  for (const g of games) {
    const key = g.color + "|" + shortOpening(g.opening);
    op[key] ||= { n: 0, w: 0, d: 0, l: 0, acc: [] };
    op[key].n++; op[key][g.outcome[0]]++; op[key].acc.push(g.accuracy);
  }
  const openings = Object.entries(op).map(([k, v]) => {
    const [color, name] = k.split("|");
    return { color, name, n: v.n, w: v.w, d: v.d, l: v.l, score: Math.round(100 * (v.w + 0.5 * v.d) / v.n), acc: +avg(v.acc).toFixed(1) };
  }).sort((a, b) => b.n - a.n);

  const spent = my.map((m) => m.spent).filter((x) => x !== null);
  const timeouts = games.filter((g) => g.outcome === "loss" && g.end_reason === "timeout").length;
  const worst = games.flatMap((g) => g.moves.filter((m) => m.class === "Patzer" || m.class === "Fehler").map((m) => [g, m]))
    .sort((a, b) => b[1].drop - a[1].drop).slice(0, 40);
  const ratings = games.filter((g) => g.my_rating).map((g) => [g.end_time || 0, g.my_rating]).sort((a, b) => a[0] - b[0]);

  const tags = Object.fromEntries(Object.entries(tagCount).sort((a, b) => b[1] - a[1]).map(([k, v]) => [TAGS[k], v]));

  return {
    n_games: n, n_moves: total, outcomes, by_color: byColor,
    accuracy: +avg(games.map((g) => g.accuracy)).toFixed(1), classes,
    errors_per_game: +(errors.length / n).toFixed(2), blunders_per_game: +((classes.Patzer || 0) / n).toFixed(2),
    tags, tag_keys: tagCount, phase_acc: phaseAcc, phase_err_rate: phaseErr,
    style: Object.fromEntries(Object.entries(style).map(([k, v]) => [k, +v.toFixed(2)])), archetype,
    metrics: {
      "Schlagzüge pro Zug": `${(100 * captureRate).toFixed(0)} %`, "Schachgebote pro Zug": `${(100 * checkRate).toFixed(0)} %`,
      "Rochade-Quote": `${(100 * castleRate).toFixed(0)} % (Ø Zug ${castleAvg.toFixed(0)})`,
      "Lange Rochade": `${(100 * longC).toFixed(0)} %`, "Ungleichseitige Rochaden": `${(100 * opposite).toFixed(0)} %`,
      "Bauernsturm-Züge pro Partie": storm.toFixed(1), "Korrekte Opfer pro Partie": sacs.toFixed(2),
      "Frühe Damenzüge (Zug ≤ 6)": `${(100 * earlyQ).toFixed(0)} %`, "Damentausch bis Zug 20": `${(100 * qtEarly).toFixed(0)} %`,
      "Ø Partielänge (eigene Züge)": avgLen.toFixed(0), "Entschiedene Partien": `${(100 * decisive).toFixed(0)} %`,
      "Ø Bedenkzeit pro Zug": `${avg(spent).toFixed(1)} s`, "Zeitverluste": String(timeouts),
    },
    gm_matches: gmMatches, openings, worst, current_rating: ratings.length ? ratings[ratings.length - 1][1] : null,
    rating_history: ratings, weaknesses: rankWeaknesses(tagCount, errors.length, phaseErr, timeouts, n),
  };
}

function rankWeaknesses(t, nErr, phaseErr, timeouts, n) {
  const e = Math.max(1, nErr);
  const g = (k) => t[k] || 0;
  const s = {
    taktik: (g("hung") + g("missed_tactic") + g("missed_mate") + g("allowed_mate")) / e,
    strategie: g("positional") / e,
    zeit: (g("time_trouble") + g("too_fast")) / e + timeouts / n,
    verwertung: g("conversion") / e,
    endspiel: 0.05, eroeffnung: 0.05,
  };
  const phases = Object.keys(phaseErr);
  const worst = phases.length ? phases.reduce((a, b) => (phaseErr[a] >= phaseErr[b] ? a : b)) : "Mittelspiel";
  s[{ "Eröffnung": "eroeffnung", "Mittelspiel": "taktik", "Endspiel": "endspiel" }[worst]] += 0.25;
  return Object.entries(s).sort((a, b) => b[1] - a[1]).map(([k]) => k);
}
