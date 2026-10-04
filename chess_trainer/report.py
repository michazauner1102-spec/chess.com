"""Render the profile and plan as a self-contained HTML report (+ CSV/JSON exports)."""

import csv
import html
import json
import urllib.parse
from pathlib import Path

import chess
import chess.svg

from .analyze import TAGS
from .knowledge import ARCHETYPES, DIM_LABEL, DIMS, REPERTOIRE
from .plan import PHASES

ADVICE = {
    "taktik": ("Taktik & Blunder-Check",
               "Die meisten deiner Fehler kosten direkt Material oder übersehen Matt. Vor JEDEM Zug: "
               "1) Was hat der Gegner mit seinem letzten Zug gedroht? 2) Welche Figuren hängen (meine & seine)? "
               "3) Schachs, Schläge, Drohungen – für beide Seiten. Täglich Themen-Puzzles."),
    "strategie": ("Pläne & Positionsverständnis",
                  "Viele Fehler entstehen ohne direkten Materialverlust: falscher Plan, schlechte Figur, "
                  "falscher Abtausch. Lerne Bauernstrukturen und frage dich: 'Was ist meine schlechteste Figur?'"),
    "zeit": ("Zeitmanagement",
             "Fehler in Zeitnot oder nach Schnellschüssen. Faustregel 15|10: Eröffnung zügig (Repertoire!), "
             "in kritischen Stellungen (Schlagabtausch, Opfer, Endspielübergang) bewusst 1–3 Minuten investieren."),
    "verwertung": ("Gewinnstellungen verwerten",
                   "Du verspielst Vorteile. Wenn du klar besser stehst: Gegenspiel verhindern, Figuren tauschen, "
                   "Königssicherheit prüfen – kein Risiko mehr. Übe Gewinnstellungen gegen die Engine auszuspielen."),
    "endspiel": ("Endspieltechnik",
                 "Im Endspiel ist deine Fehlerquote am höchsten. Lerne die Kernstellungen (Lucena, Philidor, "
                 "Opposition) und spiele Endspiele gegen die Engine aus."),
    "eroeffnung": ("Eröffnung",
                   "Früh entstehen Nachteile. Ein festes, schlankes Repertoire (unten) mit Verständnis der Pläne "
                   "statt auswendig gelernter Zugfolgen spart Zeit und Fehler."),
}

CSS = """
:root{--bg:#f6f4ef;--card:#fff;--ink:#1d1d1f;--mute:#6b6b70;--line:#e3e0d8;--acc:#2f6f4f;--acc2:#b4532a;
--bar:#2f6f4f;--bad:#c0392b;--warn:#d68910}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#141516;--card:#1e2022;--ink:#ececec;
--mute:#9a9ba0;--line:#2d3033;--acc:#5fb98a;--acc2:#e08a5f;--bar:#5fb98a;--bad:#e5675a;--warn:#f0b14a}}
:root[data-theme="dark"]{--bg:#141516;--card:#1e2022;--ink:#ececec;--mute:#9a9ba0;--line:#2d3033;--acc:#5fb98a;
--acc2:#e08a5f;--bar:#5fb98a;--bad:#e5675a;--warn:#f0b14a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:1040px;margin:0 auto;padding:24px 16px 80px}
h1{font-size:2rem;margin:.2em 0}h2{margin:2.2em 0 .6em;font-size:1.4rem;border-bottom:2px solid var(--line);padding-bottom:.3em}
h3{margin:1.2em 0 .4em}.mute{color:var(--mute)}.card{background:var(--card);border:1px solid var(--line);
border-radius:12px;padding:16px;margin:12px 0}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px}
.kpi b{display:block;font-size:1.6rem}.kpi span{color:var(--mute);font-size:.85rem}
table{width:100%;border-collapse:collapse;font-size:.92rem}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--mute);font-weight:600}.tbl{overflow-x:auto}
.bar{height:10px;background:var(--line);border-radius:5px;overflow:hidden;min-width:80px}.bar i{display:block;height:100%;background:var(--bar)}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}
.pos{display:grid;grid-template-columns:minmax(0,260px) 1fr;gap:16px;align-items:start}
@media(max-width:620px){.pos{grid-template-columns:1fr}}
.pos svg{width:100%;height:auto;max-width:260px}.tag{display:inline-block;font-size:.78rem;padding:1px 8px;border-radius:999px;
border:1px solid var(--line);margin:2px 4px 2px 0}.bad{color:var(--bad)}.warn{color:var(--warn)}.good{color:var(--acc)}
details{background:var(--card);border:1px solid var(--line);border-radius:10px;margin:6px 0;padding:6px 12px}
summary{cursor:pointer;font-weight:600}.day{border-top:1px dashed var(--line);padding:6px 0}
.cat{display:inline-block;min-width:105px;font-weight:600}.note{border-left:4px solid var(--acc2);padding:8px 14px;background:var(--card);border-radius:6px}
code{font-size:.88rem}a{color:var(--acc)}
"""


def _bar(pct, cls=""):
    pct = max(0, min(100, pct))
    return f'<div class="bar"><i class="{cls}" style="width:{pct:.0f}%"></i></div>'


def _board_svg(m, color):
    board = chess.Board(m["fen"])
    arrows = [chess.svg.Arrow(chess.parse_square(m["uci"][:2]), chess.parse_square(m["uci"][2:4]), color="#c0392bcc")]
    if m["best_uci"]:
        arrows.append(chess.svg.Arrow(chess.parse_square(m["best_uci"][:2]), chess.parse_square(m["best_uci"][2:4]),
                                      color="#2f9e5fcc"))
    return chess.svg.board(board, orientation=chess.WHITE if color == "white" else chess.BLACK,
                           arrows=arrows, size=260, coordinates=True)


def _fmt_eval(cp):
    if abs(cp) >= 9000:
        return "Matt" if cp > 0 else "-Matt"
    return f"{cp / 100:+.1f}"


def _projection_svg(proj):
    w, h, pad = 560, 220, 36
    lo = min(proj["current"], min(q["realistic"] for q in proj["quarters"])) - 100
    hi = proj["target"] + 50

    def xy(i, v):
        return pad + i * (w - 2 * pad) / 4, h - pad - (v - lo) * (h - 2 * pad) / (hi - lo)

    def path(key):
        pts = [xy(0, proj["current"])] + [xy(q["q"], q[key]) for q in proj["quarters"]]
        return " ".join(f"{x:.0f},{y:.0f}" for x, y in pts)

    labels = "".join(f'<text x="{xy(i, lo)[0]:.0f}" y="{h - 10}" font-size="12" text-anchor="middle" '
                     f'fill="currentColor">{t}</text>' for i, t in enumerate(["Heute", "Q1", "Q2", "Q3", "Q4"]))
    dots = "".join(f'<circle cx="{xy(q["q"], q["realistic"])[0]:.0f}" cy="{xy(q["q"], q["realistic"])[1]:.0f}" r="4" '
                   f'fill="var(--acc)"/><text x="{xy(q["q"], q["realistic"])[0]:.0f}" '
                   f'y="{xy(q["q"], q["realistic"])[1] - 9:.0f}" font-size="12" text-anchor="middle" '
                   f'fill="currentColor">{q["realistic"]}</text>' for q in proj["quarters"])
    return (f'<svg viewBox="0 0 {w} {h}" style="width:100%;max-width:{w}px;color:var(--ink)">'
            f'<polyline points="{path("target")}" fill="none" stroke="var(--acc2)" stroke-width="2" stroke-dasharray="6 5"/>'
            f'<polyline points="{path("realistic")}" fill="none" stroke="var(--acc)" stroke-width="3"/>'
            f'<text x="{w - pad}" y="{xy(4, proj["target"])[1] - 8:.0f}" font-size="12" text-anchor="end" '
            f'fill="var(--acc2)">Ziel {proj["target"]}</text>{dots}{labels}</svg>')


def render(profile, plan, proj, username, out_dir="report"):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    e = html.escape
    p = profile
    o = p["outcomes"]
    arche = ARCHETYPES[p["archetype"]]
    rep = REPERTOIRE[p["archetype"]]
    parts = [f"<!doctype html><html lang='de'><head><meta charset='utf-8'>"
             f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
             f"<title>Elo-Trainer {e(username)}</title><style>{CSS}</style></head><body><main>"]

    parts.append(f"<p class='mute'>Rapid-Analyse · Chess.com</p><h1>Elo-Trainer für {e(username)}</h1>")
    parts.append("<div class='kpis'>"
                 f"<div class='kpi'><b>{p['current_rating'] or '–'}</b><span>aktuelle Rapid-Wertung</span></div>"
                 f"<div class='kpi'><b>{p['n_games']}</b><span>analysierte Partien</span></div>"
                 f"<div class='kpi'><b>{o.get('win', 0)}/{o.get('draw', 0)}/{o.get('loss', 0)}</b><span>S / R / N</span></div>"
                 f"<div class='kpi'><b>{p['accuracy']} %</b><span>Ø Genauigkeit (Engine)</span></div>"
                 f"<div class='kpi'><b>{p['blunders_per_game']}</b><span>Patzer pro Partie</span></div>"
                 f"<div class='kpi'><b>{p['errors_per_game']}</b><span>Fehler+Patzer pro Partie</span></div></div>")

    # ---- honest goal
    if proj:
        parts.append("<h2>Ziel 2600 – ehrliche Einordnung</h2>")
        parts.append(
            f"<div class='note'><p>Von <b>{proj['current']}</b> auf <b>{proj['target']}</b> sind es "
            f"<b>{proj['gap']} Punkte</b>. Mit 1 Stunde pro Tag sind erfahrungsgemäß etwa "
            f"<b>+{proj['yearly']} Punkte im ersten Jahr</b> realistisch (je niedriger die Wertung, desto schneller "
            f"der Anstieg). 2600 in 12 Monaten hat praktisch kein Erwachsener mit 1 h/Tag geschafft – "
            f"Großmeister trainieren meist 4–8 h täglich über viele Jahre. Außerdem ist der GM-Titel ein "
            f"FIDE-Titel (Elo ≥ 2500 + drei GM-Normen in Turnieren am Brett), keine Chess.com-Wertung.</p>"
            f"<p>Der Plan unten ist trotzdem auf maximale Steigerung ausgelegt. Die gestrichelte Linie ist dein "
            f"Wunschpfad, die durchgezogene der realistische Pfad – miss dich an der durchgezogenen.</p></div>")
        parts.append(f"<div class='card'>{_projection_svg(proj)}</div>")

    # ---- style
    parts.append(f"<h2>Dein Spielstil: {e(arche['name'])}</h2><p>{e(arche['desc'])}</p><div class='grid2'><div class='card'>")
    parts.append("<table>" + "".join(
        f"<tr><td>{DIM_LABEL[d]}</td><td style='width:55%'>{_bar(100 * p['style'][d])}</td>"
        f"<td>{100 * p['style'][d]:.0f}</td></tr>" for d in DIMS) + "</table></div><div class='card'><table>")
    parts.append("".join(f"<tr><td>{e(k)}</td><td>{e(v)}</td></tr>" for k, v in p["metrics"].items()))
    parts.append("</table></div></div>")
    bc = p["by_color"]
    parts.append("<div class='card'><table><tr><th>Farbe</th><th>Siege</th><th>Remis</th><th>Niederlagen</th></tr>" + "".join(
        f"<tr><td>{'Weiß' if c == 'white' else 'Schwarz'}</td><td>{bc.get(c, {}).get('win', 0)}</td>"
        f"<td>{bc.get(c, {}).get('draw', 0)}</td><td>{bc.get(c, {}).get('loss', 0)}</td></tr>" for c in ("white", "black"))
        + "</table></div>")

    # ---- mistakes
    parts.append("<h2>Deine typischen Fehler</h2>")
    parts.append("<div class='grid2'><div class='card'><h3>Fehlertypen (Fehler + Patzer)</h3><table>")
    total_tags = max(1, sum(p["tags"].values()))
    parts.append("".join(f"<tr><td>{e(k)}</td><td style='width:40%'>{_bar(100 * v / total_tags)}</td><td>{v}</td></tr>"
                         for k, v in p["tags"].items()) or "<tr><td>Keine Fehler gefunden</td></tr>")
    parts.append("</table></div><div class='card'><h3>Nach Partiephase</h3><table>"
                 "<tr><th>Phase</th><th>Genauigkeit</th><th>Fehlerquote</th></tr>")
    for ph in ("Eröffnung", "Mittelspiel", "Endspiel"):
        if ph in p["phase_acc"]:
            parts.append(f"<tr><td>{ph}</td><td>{p['phase_acc'][ph]} %</td><td>{p['phase_err_rate'][ph]} % der Züge</td></tr>")
    parts.append("</table></div></div>")
    parts.append("<h3>Deine größten Baustellen (in dieser Reihenfolge)</h3>")
    for i, w in enumerate(p["weaknesses"][:3], 1):
        t, txt = ADVICE[w]
        parts.append(f"<div class='card'><b>{i}. {e(t)}</b><br>{e(txt)}</div>")

    # ---- training positions
    parts.append("<h2>Deine Trainingsstellungen – was du hättest spielen sollen</h2>"
                 "<p class='mute'>Rot = dein Zug, Grün = Engine-Empfehlung. Erst selbst lösen, dann aufdecken. "
                 "Das sind deine 'Fehlerkarten' aus dem Trainingsplan.</p>")
    for k, (g, m) in enumerate(p["worst"][:25], 1):
        lichess = "https://lichess.org/analysis/" + urllib.parse.quote(m["fen"].replace(" ", "_"))
        move_label = f"{m['move_no']}{'.' if g['color'] == 'white' else '…'}"
        tags = "".join(f"<span class='tag'>{e(t)}</span>" for t in _tag_names(m["tags"]))
        parts.append(
            f"<div class='card pos'><div>{_board_svg(m, g['color'])}</div><div>"
            f"<b>#{k} · {e(m['class'])} · {e(m['phase'])}</b> "
            f"<span class='mute'>({'Weiß' if g['color'] == 'white' else 'Schwarz'} gegen {e(str(g['opp_name']))}, "
            f"{e(g['opening'][:50])})</span><br>"
            f"Du spieltest <b class='bad'>{move_label} {e(m['san'])}</b> "
            f"(Bewertung {_fmt_eval(m['cp_before'])} → {_fmt_eval(m['cp_after'])}, Gewinnchance −{m['drop']:.0f} %).<br>"
            f"<details><summary>Lösung anzeigen</summary>Besser: <b class='good'>{e(m['best_san'] or '?')}</b><br>"
            f"Hauptvariante: <code>{e(m['best_line'])}</code><br>"
            f"Nach deinem Zug folgt: <code>{e(m['reply_line'])}</code></details>{tags}<br>"
            f"<a href='{e(g['url'] or '#')}' target='_blank' rel='noopener'>Partie</a> · "
            f"<a href='{e(lichess)}' target='_blank' rel='noopener'>Stellung analysieren</a></div></div>")

    # ---- openings
    parts.append("<h2>Eröffnungen</h2><h3>Deine bisherigen Eröffnungen</h3><div class='card tbl'><table>"
                 "<tr><th>Farbe</th><th>Eröffnung</th><th>Partien</th><th>S/R/N</th><th>Score</th><th>Ø Genauigk.</th></tr>")
    for op in p["openings"][:15]:
        cls = "good" if op["score"] >= 55 else "bad" if op["score"] < 45 else ""
        parts.append(f"<tr><td>{'Weiß' if op['color'] == 'white' else 'Schwarz'}</td><td>{e(op['name'])}</td>"
                     f"<td>{op['n']}</td><td>{op['w']}/{op['d']}/{op['l']}</td><td class='{cls}'>{op['score']} %</td>"
                     f"<td>{op['acc']} %</td></tr>")
    parts.append("</table></div><h3>Empfohlenes Repertoire auf Großmeister-Niveau – passend zu deinem Stil</h3>")
    for key, title in (("weiss", "Mit Weiß"), ("schwarz_e4", "Mit Schwarz gegen 1.e4"), ("schwarz_d4", "Mit Schwarz gegen 1.d4/1.c4")):
        r = rep[key]
        extra = f"<br><span class='mute'>{e(r['extra'])}</span>" if r.get("extra") else ""
        parts.append(f"<div class='card'><b>{title}: {e(r['name'])}</b><br><code>{e(r['line'])}</code>{extra}<br>"
                     f"<b>Pläne:</b> {e(r['plans'])}<br><b>Vorbilder:</b> {e(r['gms'])}</div>")

    # ---- GMs
    parts.append("<h2>Großmeister, die zu dir passen</h2><div class='grid2'>")
    for gm in p["gm_matches"]:
        games = "".join(f"<li>{e(x)}</li>" for x in gm["games"])
        parts.append(f"<div class='card'><b>{e(gm['name'])}</b> <span class='mute'>· Ähnlichkeit {gm['match']} %</span>"
                     f"<p>{e(gm['why'])}</p><b>Zum Nachspielen:</b><ul>{games}</ul></div>")
    parts.append("</div>")

    # ---- plan
    parts.append("<h2>Dein 1-Stunden-Trainingsplan für 365 Tage</h2>")
    parts.append("<div class='grid2'>" + "".join(
        f"<div class='card'><b>Wochen {a}–{b}: {e(n)}</b><br>{e(g)}</div>" for a, b, n, g in PHASES) + "</div>")
    if proj:
        parts.append("<div class='card'><b>Meilensteine (realistisch):</b> " + " · ".join(
            f"Q{q['q']}: {q['realistic']}" for q in proj["quarters"]) + "</div>")
    parts.append("<p class='mute'>Der Plan gewichtet deine größten Baustellen stärker. "
                 "Als Kalender-/Tabellendatei: <code>trainingsplan.csv</code>.</p>")
    week = None
    for day in plan:
        if day["week"] != week:
            if week is not None:
                parts.append("</details>")
            week = day["week"]
            parts.append(f"<details{' open' if week == 1 else ''}><summary>Woche {week} · {e(day['phase'])} "
                         f"<span class='mute'>(ab {day['date']})</span></summary>")
        blocks = "".join(f"<div><span class='cat'>{b['min']} min {e(b['cat'])}</span> {e(b['task'])}</div>"
                         for b in day["blocks"])
        parts.append(f"<div class='day'><b>Tag {day['day']} · {day['weekday']} {day['date']}</b>{blocks}</div>")
    parts.append("</details>")
    parts.append("<p class='mute'>Erstellt mit chess_trainer · Daten: Chess.com Published-Data API · Engine: Stockfish</p>"
                 "</main></body></html>")

    (out / "report.html").write_text("".join(parts), encoding="utf-8")
    with open(out / "trainingsplan.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["Tag", "Datum", "Wochentag", "Woche", "Phase", "Minuten", "Kategorie", "Aufgabe"])
        for d in plan:
            for b in d["blocks"]:
                w.writerow([d["day"], d["date"], d["weekday"], d["week"], d["phase"], b["min"], b["cat"], b["task"]])
    summary = {k: v for k, v in profile.items() if k not in ("worst", "rating_history")}
    (out / "profil.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return out / "report.html"


def _tag_names(tags):
    return [TAGS[t] for t in tags]
