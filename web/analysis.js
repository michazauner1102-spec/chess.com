// Per-move engine analysis, error classification and style features.
// JavaScript port of chess_trainer/analyze.py.

import { Chess } from "./vendor/chess.js";

const VAL = { p: 1, n: 3, b: 3, r: 5, q: 9, k: 0 };
const MATE = 10000;
const INACCURACY = 5, MISTAKE = 10, BLUNDER = 15;
const DRAWS = new Set(["agreed", "repetition", "stalemate", "insufficient", "50move", "timevsinsufficient"]);

export const winPct = (cp) => 50 + 50 * (2 / (1 + Math.exp(-0.00368208 * cp)) - 1);
const moveAcc = (wb, wa) => Math.max(0, Math.min(100, 103.1668 * Math.exp(-0.04354 * Math.max(0, wb - wa)) - 3.1669));

function material(fen, color) {
  let s = 0;
  for (const ch of fen.split(" ")[0]) {
    const lc = ch.toLowerCase();
    if (VAL[lc] === undefined) continue;
    const mine = (ch === lc ? "b" : "w") === color;
    s += mine ? VAL[lc] : -VAL[lc];
  }
  return s;
}

function nonPawnMaterial(fen) {
  let s = 0;
  for (const ch of fen.split(" ")[0]) if ("nbrqNBRQ".includes(ch)) s += VAL[ch.toLowerCase()];
  return s;
}

function phaseOf(fen) {
  const npm = nonPawnMaterial(fen);
  const fullmove = parseInt(fen.split(" ")[5], 10);
  if (npm <= 20) return "Endspiel";
  if (fullmove <= 12 && npm >= 54) return "Eröffnung";
  return "Mittelspiel";
}

const hasQueens = (fen) => /[qQ]/.test(fen.split(" ")[0]);

function playUci(chess, uci) {
  try {
    return chess.move({ from: uci.slice(0, 2), to: uci.slice(2, 4), promotion: uci[4] });
  } catch {
    return null;
  }
}

/** Material after `plies` moves of a line, continued through pending captures. */
function materialAfterLine(fen, line, color, plies) {
  const c = new Chess(fen);
  for (let k = 0; k < line.length; k++) {
    if (k >= plies + 4) break;
    if (k >= plies) {
      const legal = c.moves({ verbose: true }).find((m) => m.from + m.to + (m.promotion || "") === line[k]);
      if (!legal || !legal.captured) break;
    }
    if (!playUci(c, line[k])) break;
  }
  return material(c.fen(), color);
}

function lineSan(fen, pv, n) {
  const c = new Chess(fen);
  const out = [];
  for (const u of pv.slice(0, n)) {
    const m = playUci(c, u);
    if (!m) break;
    out.push(m.san);
  }
  return out.join(" ");
}

function baseTime(tc) {
  const n = parseInt(String(tc || "600").split("+")[0].split("/").pop(), 10);
  return Number.isFinite(n) ? n : 600;
}

function parseClock(s) {
  const parts = s.split(":").map(Number);
  return parts.reduce((a, b) => a * 60 + b, 0);
}

export function parseGame(gameJson) {
  const chess = new Chess();
  chess.loadPgn(gameJson.pgn);
  const history = chess.history({ verbose: true });
  const movetext = gameJson.pgn.replace(/^\[.*\]\s*$/gm, "");
  const clocks = [...movetext.matchAll(/\[%clk ([\d:.]+)\]/g)].map((m) => parseClock(m[1]));
  const headers = chess.getHeaders ? chess.getHeaders() : chess.header();
  return { history, clocks: clocks.length === history.length ? clocks : null, headers };
}

export async function analyseGame(engine, gameJson, username, depth, onPos) {
  const me = username.toLowerCase();
  let color, my, opp;
  if (gameJson.white.username.toLowerCase() === me) [color, my, opp] = ["w", gameJson.white, gameJson.black];
  else if (gameJson.black.username.toLowerCase() === me) [color, my, opp] = ["b", gameJson.black, gameJson.white];
  else return null;

  const { history, clocks, headers } = parseGame(gameJson);
  if (!history.length) return null;
  const fens = [history[0].before, ...history.map((m) => m.after)];

  await engine.newGame();
  const infos = [];
  for (let i = 0; i < fens.length; i++) {
    const c = new Chess(fens[i]);
    infos.push(c.isGameOver() ? null : await engine.analyse(fens[i], depth));
    if (onPos) onPos(i + 1, fens.length);
  }

  const evalUser = (i) => {
    const info = infos[i];
    const turn = fens[i].split(" ")[1];
    if (!info) {
      const c = new Chess(fens[i]);
      if (c.isCheckmate()) return turn === color ? -MATE : MATE;
      return 0;
    }
    return turn === color ? info.cp : -info.cp;
  };
  const mateUser = (i) => {
    const info = infos[i];
    if (!info || info.mate === null) return null;
    return fens[i].split(" ")[1] === color ? info.mate : -info.mate;
  };

  const base = baseTime(gameJson.time_control || headers.TimeControl);
  const feats = { captures: 0, checks: 0, pawn_storm: 0, sound_sacs: 0, early_queen: 0,
    castle_move: null, castle_side: null, opp_castle_side: null, queen_trade_move: null };
  const prevClock = { w: base, b: base };
  const moves = [];

  for (let i = 0; i < history.length; i++) {
    const mv = history[i];
    const before = fens[i], after = fens[i + 1];
    const fullmove = parseInt(before.split(" ")[5], 10);
    let spent = null;
    if (clocks) {
      spent = Math.max(0, prevClock[mv.color] - clocks[i]);
      prevClock[mv.color] = clocks[i];
    }
    const castle = mv.flags.includes("k") ? "kurz" : mv.flags.includes("q") ? "lang" : null;
    if (hasQueens(before) && !hasQueens(after) && feats.queen_trade_move === null) feats.queen_trade_move = fullmove;

    if (mv.color !== color) {
      if (castle) feats.opp_castle_side = castle;
      continue;
    }

    if (mv.captured) feats.captures++;
    if (mv.san.includes("+") || mv.san.includes("#")) feats.checks++;
    if (castle && feats.castle_move === null) { feats.castle_move = fullmove; feats.castle_side = castle; }
    if (mv.piece === "q" && fullmove <= 6) feats.early_queen++;
    if (mv.piece === "p" && feats.opp_castle_side) {
      const oppKing = new Chess(before).findPiece({ type: "k", color: color === "w" ? "b" : "w" })[0];
      if (oppKing) {
        const file = (sq) => sq.charCodeAt(0) - 97;
        const rank = parseInt(mv.to[1], 10) - 1;
        const rel = color === "w" ? rank : 7 - rank;
        if (Math.abs(file(mv.to) - file(oppKing)) <= 1 && rel >= 3 && rel <= 5) feats.pawn_storm++;
      }
    }

    const cpB = evalUser(i), cpA = evalUser(i + 1);
    const wB = winPct(cpB), wA = winPct(cpA);
    const drop = Math.max(0, wB - wA);
    const cls = drop >= BLUNDER ? "Patzer" : drop >= MISTAKE ? "Fehler" : drop >= INACCURACY ? "Ungenauigkeit" : "ok";

    const info = infos[i];
    const bestPv = info ? info.pv : [];
    const replyPv = infos[i + 1] ? infos[i + 1].pv : [];
    const best = bestPv[0] || null;
    const matNow = material(before, color);
    const matBest = materialAfterLine(before, bestPv, color, 4);
    const matPlayed = materialAfterLine(after, replyPv, color, 3);

    if (drop < 5 && wB >= 25 && wB <= 75 && matPlayed <= matNow - 2 && matBest >= matNow - 1) feats.sound_sacs++;

    const tags = [];
    if (cls === "Fehler" || cls === "Patzer") {
      const mb = mateUser(i), ma = mateUser(i + 1);
      if (mb !== null && mb > 0 && !(ma !== null && ma > 0)) tags.push("missed_mate");
      if (ma !== null && ma < 0 && !(mb !== null && mb < 0)) tags.push("allowed_mate");
      if (matBest - matPlayed >= 2) tags.push(matBest >= matNow + 2 ? "missed_tactic" : "hung");
      if (wB >= 75 && wA < 60) tags.push("conversion");
      const left = clocks ? clocks[i] : null;
      if (left !== null && left < Math.max(30, 0.1 * base)) tags.push("time_trouble");
      else if (spent !== null && spent < 5) tags.push("too_fast");
      if (!tags.some((t) => ["missed_mate", "allowed_mate", "hung", "missed_tactic"].includes(t))) tags.push("positional");
    }

    moves.push({
      ply: i, move_no: fullmove, san: mv.san, uci: mv.from + mv.to + (mv.promotion || ""), fen: before,
      best_uci: best, best_san: best ? lineSan(before, [best], 1) : null,
      best_line: lineSan(before, bestPv, 6), reply_line: lineSan(after, replyPv, 4),
      cp_before: cpB, cp_after: cpA, win_before: +wB.toFixed(1), win_after: +wA.toFixed(1),
      drop: +drop.toFixed(1), accuracy: +moveAcc(wB, wA).toFixed(1), class: cls, phase: phaseOf(before),
      clock: clocks ? clocks[i] : null, spent, tags,
    });
  }

  const acc = moves.length ? moves.reduce((a, m) => a + m.accuracy, 0) / moves.length : 0;
  const outcome = my.result === "win" ? "win" : DRAWS.has(my.result) ? "draw" : "loss";
  const ecoUrl = gameJson.eco || headers.ECOUrl || "";
  const opening = ecoUrl ? ecoUrl.split("/").pop().replace(/-/g, " ")
    : headers.Opening || history.slice(0, 4).map((m) => m.san).join(" ");

  return {
    url: gameJson.url, end_time: gameJson.end_time, color: color === "w" ? "white" : "black",
    my_rating: my.rating, opp_rating: opp.rating, opp_name: opp.username, outcome,
    end_reason: outcome === "win" ? opp.result : my.result, eco: headers.ECO || "", opening,
    first_moves: history.slice(0, 6).map((m) => m.san).join(" "),
    time_control: gameJson.time_control, base_time: base, n_moves: moves.length, accuracy: +acc.toFixed(1),
    features: feats, moves,
  };
}
