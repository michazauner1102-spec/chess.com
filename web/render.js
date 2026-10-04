// Report rendering. Port of chess_trainer/report.py.

import { boardSvg } from "./board.js";
import { ADVICE, ARCHETYPES, DIM_LABEL, DIMS, PHASES, REPERTOIRE, TAGS } from "./data.js";

const e = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const bar = (pct) => `<div class="bar"><i style="width:${Math.max(0, Math.min(100, pct)).toFixed(0)}%"></i></div>`;
const fmtEval = (cp) => (Math.abs(cp) >= 9000 ? (cp > 0 ? "Matt" : "−Matt") : `${cp >= 0 ? "+" : "−"}${Math.abs(cp / 100).toFixed(1)}`);
const colorDe = (c) => (c === "white" ? "Weiß" : "Schwarz");

function projectionSvg(p) {
  const w = 560, h = 220, pad = 36;
  const lo = Math.min(p.current, ...p.quarters.map((q) => q.realistic)) - 100, hi = p.target + 50;
  const xy = (i, v) => [pad + (i * (w - 2 * pad)) / 4, h - pad - ((v - lo) * (h - 2 * pad)) / (hi - lo)];
  const path = (k) => [xy(0, p.current), ...p.quarters.map((q) => xy(q.q, q[k]))].map(([x, y]) => `${x.toFixed(0)},${y.toFixed(0)}`).join(" ");
  const labels = ["Heute", "Q1", "Q2", "Q3", "Q4"].map((t, i) => `<text x="${xy(i, lo)[0]}" y="${h - 10}" font-size="12" text-anchor="middle" fill="currentColor">${t}</text>`).join("");
  const dots = p.quarters.map((q) => { const [x, y] = xy(q.q, q.realistic); return `<circle cx="${x}" cy="${y}" r="4" fill="var(--acc)"/><text x="${x}" y="${y - 9}" font-size="12" text-anchor="middle" fill="currentColor">${q.realistic}</text>`; }).join("");
  const [, ty] = xy(4, p.target);
  return `<svg viewBox="0 0 ${w} ${h}" style="width:100%;max-width:${w}px;color:var(--ink)">
    <polyline points="${path("target")}" fill="none" stroke="var(--acc2)" stroke-width="2" stroke-dasharray="6 5"/>
    <polyline points="${path("realistic")}" fill="none" stroke="var(--acc)" stroke-width="3"/>
    <text x="${w - pad}" y="${ty - 8}" font-size="12" text-anchor="end" fill="var(--acc2)">Ziel ${p.target}</text>${dots}${labels}</svg>`;
}

export function renderReport(p, plan, proj, username) {
  const o = p.outcomes, arche = ARCHETYPES[p.archetype], rep = REPERTOIRE[p.archetype];
  const out = [];
  out.push(`<p class="mute">Rapid-Analyse · ${p.n_games} Partien</p><h1>Elo-Trainer für ${e(username)}</h1>
  <div class="kpis">
    <div class="kpi"><b>${p.current_rating ?? "–"}</b><span>aktuelle Wertung</span></div>
    <div class="kpi"><b>${p.n_games}</b><span>analysierte Partien</span></div>
    <div class="kpi"><b>${o.win || 0}/${o.draw || 0}/${o.loss || 0}</b><span>S / R / N</span></div>
    <div class="kpi"><b>${p.accuracy} %</b><span>Ø Genauigkeit</span></div>
    <div class="kpi"><b>${p.blunders_per_game}</b><span>Patzer pro Partie</span></div>
    <div class="kpi"><b>${p.errors_per_game}</b><span>Fehler+Patzer pro Partie</span></div>
  </div>`);

  if (proj) {
    out.push(`<h2>Ziel ${proj.target} – ehrliche Einordnung</h2><div class="note">
      <p>Von <b>${proj.current}</b> auf <b>${proj.target}</b> sind es <b>${proj.gap} Punkte</b>. Mit 1 Stunde pro Tag sind
      erfahrungsgemäß etwa <b>+${proj.yearly} Punkte im ersten Jahr</b> realistisch (je niedriger die Wertung, desto schneller
      der Anstieg). 2600 in 12 Monaten hat praktisch kein Erwachsener mit 1 h/Tag geschafft – Großmeister trainieren meist
      4–8 h täglich über viele Jahre. Der GM-Titel ist außerdem ein FIDE-Titel (Elo ≥ 2500 + drei GM-Normen am Brett),
      keine Chess.com-Wertung.</p><p>Der Plan ist trotzdem auf maximale Steigerung ausgelegt. Gestrichelt = Wunschpfad,
      durchgezogen = realistischer Pfad. Miss dich an der durchgezogenen Linie.</p></div>
      <div class="card">${projectionSvg(proj)}</div>`);
  }

  out.push(`<h2>Dein Spielstil: ${e(arche.name)}</h2><p>${e(arche.desc)}</p><div class="grid2"><div class="card"><table>
    ${DIMS.map((d) => `<tr><td>${DIM_LABEL[d]}</td><td style="width:55%">${bar(100 * p.style[d])}</td><td>${(100 * p.style[d]).toFixed(0)}</td></tr>`).join("")}
    </table></div><div class="card"><table>${Object.entries(p.metrics).map(([k, v]) => `<tr><td>${e(k)}</td><td>${e(v)}</td></tr>`).join("")}</table></div></div>
    <div class="card"><table><tr><th>Farbe</th><th>Siege</th><th>Remis</th><th>Niederlagen</th></tr>
    ${["white", "black"].map((c) => `<tr><td>${colorDe(c)}</td><td>${p.by_color[c]?.win || 0}</td><td>${p.by_color[c]?.draw || 0}</td><td>${p.by_color[c]?.loss || 0}</td></tr>`).join("")}
    </table></div>`);

  const totalTags = Math.max(1, Object.values(p.tags).reduce((a, b) => a + b, 0));
  out.push(`<h2>Deine typischen Fehler</h2><div class="grid2"><div class="card"><h3>Fehlertypen (Fehler + Patzer)</h3><table>
    ${Object.entries(p.tags).map(([k, v]) => `<tr><td>${e(k)}</td><td style="width:40%">${bar((100 * v) / totalTags)}</td><td>${v}</td></tr>`).join("") || "<tr><td>Keine Fehler gefunden</td></tr>"}
    </table></div><div class="card"><h3>Nach Partiephase</h3><table><tr><th>Phase</th><th>Genauigkeit</th><th>Fehlerquote</th></tr>
    ${["Eröffnung", "Mittelspiel", "Endspiel"].filter((ph) => ph in p.phase_acc).map((ph) => `<tr><td>${ph}</td><td>${p.phase_acc[ph]} %</td><td>${p.phase_err_rate[ph]} % der Züge</td></tr>`).join("")}
    </table></div></div><h3>Deine größten Baustellen (in dieser Reihenfolge)</h3>
    ${p.weaknesses.slice(0, 3).map((w, i) => `<div class="card"><b>${i + 1}. ${e(ADVICE[w][0])}</b><br>${e(ADVICE[w][1])}</div>`).join("")}`);

  out.push(`<h2>Deine Trainingsstellungen – was du hättest spielen sollen</h2>
    <p class="mute">Rot = dein Zug, Grün = Engine-Empfehlung. Erst selbst lösen, dann aufdecken. Das sind deine „Fehlerkarten“ aus dem Trainingsplan.</p>`);
  p.worst.slice(0, 25).forEach(([g, m], k) => {
    const arrows = [{ from: m.uci.slice(0, 2), to: m.uci.slice(2, 4), color: "#c0392b" }];
    if (m.best_uci) arrows.push({ from: m.best_uci.slice(0, 2), to: m.best_uci.slice(2, 4), color: "#2f9e5f" });
    const lichess = "https://lichess.org/analysis/" + encodeURI(m.fen.replace(/ /g, "_"));
    const mvLabel = `${m.move_no}${g.color === "white" ? "." : "…"}`;
    out.push(`<div class="card pos"><div class="boardwrap">${boardSvg(m.fen, { flip: g.color === "black", arrows })}</div><div>
      <b>#${k + 1} · ${e(m.class)} · ${e(m.phase)}</b> <span class="mute">(${colorDe(g.color)} gegen ${e(g.opp_name)}, ${e(g.opening.slice(0, 50))})</span><br>
      Du spieltest <b class="bad">${mvLabel} ${e(m.san)}</b> (Bewertung ${fmtEval(m.cp_before)} → ${fmtEval(m.cp_after)}, Gewinnchance −${m.drop.toFixed(0)} %).
      <details><summary>Lösung anzeigen</summary>Besser: <b class="good">${e(m.best_san || "?")}</b><br>
      Hauptvariante: <code>${e(m.best_line)}</code><br>Nach deinem Zug folgt: <code>${e(m.reply_line)}</code></details>
      ${m.tags.map((t) => `<span class="tag">${e(TAGS[t])}</span>`).join("")}<br>
      ${g.url && g.url.startsWith("http") ? `<a href="${e(g.url)}" target="_blank" rel="noopener">Partie</a> · ` : ""}
      <a href="${e(lichess)}" target="_blank" rel="noopener">Stellung analysieren</a></div></div>`);
  });

  out.push(`<h2>Eröffnungen</h2><h3>Deine bisherigen Eröffnungen</h3><div class="card tbl"><table>
    <tr><th>Farbe</th><th>Eröffnung</th><th>Partien</th><th>S/R/N</th><th>Score</th><th>Ø Genauigk.</th></tr>
    ${p.openings.slice(0, 15).map((op) => `<tr><td>${colorDe(op.color)}</td><td>${e(op.name)}</td><td>${op.n}</td><td>${op.w}/${op.d}/${op.l}</td>
      <td class="${op.score >= 55 ? "good" : op.score < 45 ? "bad" : ""}">${op.score} %</td><td>${op.acc} %</td></tr>`).join("")}
    </table></div><h3>Empfohlenes Repertoire auf Großmeister-Niveau – passend zu deinem Stil</h3>`);
  for (const [key, title] of [["weiss", "Mit Weiß"], ["schwarz_e4", "Mit Schwarz gegen 1.e4"], ["schwarz_d4", "Mit Schwarz gegen 1.d4/1.c4"]]) {
    const r = rep[key];
    out.push(`<div class="card"><b>${title}: ${e(r.name)}</b><br><code>${e(r.line)}</code>
      ${r.extra ? `<br><span class="mute">${e(r.extra)}</span>` : ""}<br><b>Pläne:</b> ${e(r.plans)}<br><b>Vorbilder:</b> ${e(r.gms)}</div>`);
  }

  out.push(`<h2>Großmeister, die zu dir passen</h2><div class="grid2">
    ${p.gm_matches.map((gm) => `<div class="card"><b>${e(gm.name)}</b> <span class="mute">· Ähnlichkeit ${gm.match} %</span>
      <p>${e(gm.why)}</p><b>Zum Nachspielen:</b><ul>${gm.games.map((x) => `<li>${e(x)}</li>`).join("")}</ul></div>`).join("")}</div>`);

  out.push(`<h2>Dein 1-Stunden-Trainingsplan für 365 Tage</h2><div class="grid2">
    ${PHASES.map(([a, b, n, g]) => `<div class="card"><b>Wochen ${a}–${b}: ${e(n)}</b><br>${e(g)}</div>`).join("")}</div>
    ${proj ? `<div class="card"><b>Meilensteine (realistisch):</b> ${proj.quarters.map((q) => `Q${q.q}: ${q.realistic}`).join(" · ")}</div>` : ""}
    <p><button id="csv" class="btn secondary">Plan als CSV herunterladen</button></p>`);
  let week = null;
  for (const day of plan) {
    if (day.week !== week) {
      if (week !== null) out.push("</details>");
      week = day.week;
      out.push(`<details${week === 1 ? " open" : ""}><summary>Woche ${week} · ${e(day.phase)} <span class="mute">(ab ${day.date})</span></summary>`);
    }
    out.push(`<div class="day"><b>Tag ${day.day} · ${day.weekday} ${day.date}</b>
      ${day.blocks.map((b) => `<div><span class="cat">${b.min} min ${e(b.cat)}</span> ${e(b.task)}</div>`).join("")}</div>`);
  }
  out.push("</details>");
  return out.join("");
}

export function planCsv(plan) {
  const q = (s) => `"${String(s).replace(/"/g, '""')}"`;
  const rows = [["Tag", "Datum", "Wochentag", "Woche", "Phase", "Minuten", "Kategorie", "Aufgabe"]];
  for (const d of plan) for (const b of d.blocks) rows.push([d.day, d.date, d.weekday, d.week, d.phase, b.min, b.cat, b.task]);
  return "﻿" + rows.map((r) => r.map(q).join(";")).join("\n");
}
