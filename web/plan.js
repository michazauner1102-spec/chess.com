// 365-day training plan (60 min/day) and rating projection. Port of chess_trainer/plan.py.

import { ENDGAME_CURRICULUM, PHASES, REPERTOIRE, STRATEGY_THEMES, TACTIC_THEMES, WEEKDAYS } from "./data.js";

const CAT_WEAKNESS = { Taktik: "taktik", Rechnen: "taktik", Strategie: "strategie", Endspiel: "endspiel",
  "Eröffnung": "eroeffnung", Fehlerkarten: "verwertung", Zeit: "zeit" };
const FIXED = new Set(["Partie", "Analyse", "Review"]);

function phaseOf(week) {
  for (const [a, b, name, goal] of PHASES) if (week >= a && week <= b) return [name, goal];
  const last = PHASES[PHASES.length - 1];
  return [last[2], last[3]];
}

function template(wd, phase) {
  const late = phase === "Strategie & Modellpartien" || phase === "Wettkampf";
  let t = [
    [[25, "Taktik"], [20, "Eröffnung"], [15, "Fehlerkarten"]],
    [[20, "Rechnen"], [25, "Endspiel"], [15, "Taktik"]],
    [[30, "Partie"], [20, "Analyse"], [10, "Taktik"]],
    [[30, "Strategie"], [20, "Taktik"], [10, "Fehlerkarten"]],
    [[25, "Eröffnung"], [20, "Endspiel"], [15, "Zeit"]],
    [[45, "Partie"], [15, "Analyse"]],
    [[30, "Review"], [15, "Fehlerkarten"], [15, late ? "Strategie" : "Endspiel"]],
  ][wd];
  if (phase === "Fundament" && wd === 3) t = [[20, "Strategie"], [30, "Taktik"], [10, "Fehlerkarten"]];
  if (phase === "Wettkampf" && wd === 1) t = [[30, "Partie"], [15, "Analyse"], [15, "Endspiel"]];
  return t;
}

function weight(blocks, weaknesses) {
  const mult = {};
  weaknesses.slice(0, 2).forEach((w, i) => { mult[w] = i === 0 ? 1.3 : 1.15; });
  const scaled = blocks.map(([m, c]) => [FIXED.has(c) ? m : m * (mult[CAT_WEAKNESS[c]] || 1), c]);
  const fixed = scaled.filter(([, c]) => FIXED.has(c)).reduce((a, [m]) => a + m, 0);
  const flex = scaled.filter(([, c]) => !FIXED.has(c)).reduce((a, [m]) => a + m, 0);
  const out = scaled.map(([m, c]) => {
    if (!FIXED.has(c) && flex) m = (m * (60 - fixed)) / flex;
    return [Math.max(5, 5 * Math.round(m / 5)), c];
  });
  const diff = 60 - out.reduce((a, [m]) => a + m, 0);
  let idx = out.map((_, i) => i).filter((i) => !FIXED.has(out[i][1]));
  if (!idx.length) idx = [0];
  const big = idx.reduce((a, b) => (out[b][0] > out[a][0] ? b : a));
  out[big][0] += diff;
  return out;
}

function task(cat, day, week, phase, profile, gmNames) {
  const rep = REPERTOIRE[profile.archetype];
  const tactic = TACTIC_THEMES[Math.floor(day / 2) % TACTIC_THEMES.length];
  const endgame = ENDGAME_CURRICULUM[Math.min(ENDGAME_CURRICULUM.length - 1, Math.floor(((week - 1) * ENDGAME_CURRICULUM.length) / 52))];
  const strategy = STRATEGY_THEMES[(week - 1) % STRATEGY_THEMES.length];
  const gm = gmNames[(week - 1) % gmNames.length];
  const opening = rep[["weiss", "schwarz_e4", "schwarz_d4"][(week - 1) % 3]];
  switch (cat) {
    case "Taktik":
      if (phase === "Fundament") return `Themen-Puzzles '${tactic}' (Chess.com Puzzles/Lichess-Themen), Ziel 100 % Trefferquote vor Tempo.`;
      if (phase === "Rechnen & Pläne") return `Woodpecker-Methode: festes Set von 20 Aufgaben wiederholen + Thema '${tactic}'.`;
      return `Gemischte Puzzles ≥ deine Puzzle-Wertung +200, jede Lösung vollständig im Kopf, Thema '${tactic}'.`;
    case "Rechnen":
      return "Visualisierung: 3 schwere Aufgaben NUR im Kopf lösen (kein Figurenziehen), alle Kandidatenzüge notieren (Schachs, Schläge, Drohungen), erst dann prüfen.";
    case "Endspiel":
      return `Endspiel: ${endgame} – Theorie lesen, dann gegen Engine/Freund ausspielen (Lichess 'Practice').`;
    case "Eröffnung":
      if (phase === "Fundament") return `Repertoire: ${opening.name} – Hauptlinie ${opening.line} auswendig + Ideen verstehen.`;
      return `Repertoire vertiefen: ${opening.name} – 2 Meisterpartien in dieser Linie durchspielen, eigene Partien aus der Woche damit abgleichen. Pläne: ${opening.plans}`;
    case "Strategie":
      if (phase === "Strategie & Modellpartien" || phase === "Wettkampf")
        return `Modellpartie von ${gm}: Partie mit Kommentar durchspielen, vor jedem Zug selbst tippen ('Guess the Move').`;
      return `Strategie-Thema: ${strategy} – Erklärung lesen + 2 Beispielpartien.`;
    case "Fehlerkarten":
      return "Deine Fehlerkarten (Abschnitt 'Deine Trainingsstellungen'): 5 Stellungen lösen, Fehler von gestern wiederholen (Spaced Repetition).";
    case "Zeit":
      return "Zeitmanagement: 1 Partie 10|0 spielen mit Regel 'Vor jedem Zug: Was droht der Gegner?' – Ziel: nie unter 2 Min. fallen. Alternativ Puzzle Rush (Tempo-Taktik).";
    case "Partie":
      return "Gewertete Rapid-Partie 15|10 (Wochenende) bzw. 10|5 – voll konzentriert, Blunder-Check vor jedem Zug.";
    case "Analyse":
      return "Partie sofort OHNE Engine analysieren (kritische Momente notieren), danach mit Engine vergleichen.";
    case "Review":
      return "Wochenreview: diese Seite neu laden und neue Partien analysieren lassen, Fehlertypen notieren, Ziel für nächste Woche setzen.";
  }
  return cat;
}

export function buildPlan(profile, start, days = 365) {
  const gmNames = profile.gm_matches.map((g) => g.name);
  const plan = [];
  for (let d = 0; d < days; d++) {
    const date = new Date(start.getTime() + d * 86400000);
    const wd = (date.getDay() + 6) % 7; // Monday = 0
    const week = Math.floor(d / 7) + 1;
    const [phase, goal] = phaseOf(week);
    const blocks = weight(template(wd, phase), profile.weaknesses);
    plan.push({
      day: d + 1, date: date.toISOString().slice(0, 10), weekday: WEEKDAYS[wd], week, phase, phase_goal: goal,
      blocks: blocks.map(([m, c]) => ({ min: m, cat: c, task: task(c, d, week, phase, profile, gmNames) })),
    });
  }
  return plan;
}

export function ratingProjection(current, target = 2600) {
  if (!current) return null;
  const yearly = Math.max(100, Math.min(450, 600 - current / 4));
  const quarters = [1, 2, 3, 4].map((q) => ({
    q, realistic: Math.round(current + yearly * (1 - (1 - q / 4) ** 1.5)),
    target: Math.round(current + ((target - current) * q) / 4),
  }));
  return { current, target, gap: target - current, yearly: Math.round(yearly), quarters };
}
