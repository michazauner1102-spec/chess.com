"""Generate a personalised 365-day training plan (60 minutes per day)."""

import datetime as dt

from .knowledge import ENDGAME_CURRICULUM, REPERTOIRE, STRATEGY_THEMES, TACTIC_THEMES

WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

PHASES = [
    (1, 13, "Fundament", "Patzer eliminieren: Taktikmuster automatisieren, Repertoire-Grundgerüst, Grundendspiele."),
    (14, 26, "Rechnen & Pläne", "Variantenberechnung, Kandidatenzüge, Mittelspielpläne, Turmendspiele."),
    (27, 39, "Strategie & Modellpartien", "Bauernstrukturen, Partien deiner Vorbild-GMs, komplexe Endspiele."),
    (40, 52, "Wettkampf", "Mehr ernste Partien, Repertoire mit eigenen Partien vertiefen, Zeitmanagement, Mentales."),
]

# Category -> weakness key used to up-weight it
CAT_WEAKNESS = {"Taktik": "taktik", "Rechnen": "taktik", "Strategie": "strategie", "Endspiel": "endspiel",
                "Eröffnung": "eroeffnung", "Fehlerkarten": "verwertung", "Zeit": "zeit"}
FIXED = {"Partie", "Analyse", "Review"}


def _phase(week):
    for a, b, name, goal in PHASES:
        if a <= week <= b:
            return name, goal
    return PHASES[-1][2], PHASES[-1][3]


def _template(weekday, phase):
    """Base blocks (minutes, category) per weekday; adapted per phase."""
    late = phase in ("Strategie & Modellpartien", "Wettkampf")
    t = {
        0: [(25, "Taktik"), (20, "Eröffnung"), (15, "Fehlerkarten")],
        1: [(20, "Rechnen"), (25, "Endspiel"), (15, "Taktik")],
        2: [(30, "Partie"), (20, "Analyse"), (10, "Taktik")],
        3: [(30, "Strategie"), (20, "Taktik"), (10, "Fehlerkarten")],
        4: [(25, "Eröffnung"), (20, "Endspiel"), (15, "Zeit")],
        5: [(45, "Partie"), (15, "Analyse")],
        6: [(30, "Review"), (15, "Fehlerkarten"), (15, "Strategie" if late else "Endspiel")],
    }[weekday]
    if phase == "Fundament" and weekday == 3:
        t = [(20, "Strategie"), (30, "Taktik"), (10, "Fehlerkarten")]
    if phase == "Wettkampf" and weekday == 1:
        t = [(30, "Partie"), (15, "Analyse"), (15, "Endspiel")]
    return t


def _weight(blocks, weaknesses):
    mult = {}
    for i, w in enumerate(weaknesses[:2]):
        mult[w] = 1.3 if i == 0 else 1.15
    scaled = []
    for mins, cat in blocks:
        if cat in FIXED:
            scaled.append([mins, cat])
        else:
            scaled.append([mins * mult.get(CAT_WEAKNESS.get(cat), 1.0), cat])
    fixed = sum(m for m, c in scaled if c in FIXED)
    flex = sum(m for m, c in scaled if c not in FIXED)
    out = []
    for m, c in scaled:
        if c not in FIXED and flex:
            m = m * (60 - fixed) / flex
        out.append([max(5, int(5 * round(m / 5))), c])
    diff = 60 - sum(m for m, _ in out)
    flex_idx = [i for i, (_, c) in enumerate(out) if c not in FIXED] or [0]
    out[max(flex_idx, key=lambda i: out[i][0])][0] += diff
    return out


def _task(cat, day, week, phase, profile, gm_names):
    rep = REPERTOIRE[profile["archetype"]]
    tactic = TACTIC_THEMES[(day // 2) % len(TACTIC_THEMES)]
    endgame = ENDGAME_CURRICULUM[min(len(ENDGAME_CURRICULUM) - 1, (week - 1) * len(ENDGAME_CURRICULUM) // 52)]
    strategy = STRATEGY_THEMES[(week - 1) % len(STRATEGY_THEMES)]
    gm = gm_names[(week - 1) % len(gm_names)]
    rep_keys = ["weiss", "schwarz_e4", "schwarz_d4"]
    opening = rep[rep_keys[(week - 1) % 3]]
    if cat == "Taktik":
        if phase == "Fundament":
            return f"Themen-Puzzles '{tactic}' (Chess.com Puzzles/Lichess-Themen), Ziel 100 % Trefferquote vor Tempo."
        if phase == "Rechnen & Pläne":
            return f"Woodpecker-Methode: festes Set von 20 Aufgaben wiederholen + Thema '{tactic}'."
        return f"Gemischte Puzzles ≥ deine Puzzle-Wertung +200, jede Lösung vollständig im Kopf, Thema '{tactic}'."
    if cat == "Rechnen":
        return ("Visualisierung: 3 schwere Aufgaben NUR im Kopf lösen (kein Figurenziehen), alle Kandidatenzüge "
                "notieren (Schachs, Schläge, Drohungen), erst dann prüfen.")
    if cat == "Endspiel":
        return f"Endspiel: {endgame} – Theorie lesen, dann gegen Engine/Freund ausspielen (Lichess 'Practice')."
    if cat == "Eröffnung":
        if phase == "Fundament":
            return f"Repertoire: {opening['name']} – Hauptlinie {opening['line']} auswendig + Ideen verstehen."
        return (f"Repertoire vertiefen: {opening['name']} – 2 Meisterpartien in dieser Linie durchspielen, "
                f"eigene Partien aus der Woche damit abgleichen. Pläne: {opening['plans']}")
    if cat == "Strategie":
        if phase in ("Strategie & Modellpartien", "Wettkampf"):
            return f"Modellpartie von {gm}: Partie mit Kommentar durchspielen, vor jedem Zug selbst tippen ('Guess the Move')."
        return f"Strategie-Thema: {strategy} – Erklärung lesen + 2 Beispielpartien."
    if cat == "Fehlerkarten":
        return ("Deine Fehlerkarten (Report-Abschnitt 'Deine Trainingsstellungen'): 5 Stellungen lösen, "
                "Fehler von gestern wiederholen (Spaced Repetition).")
    if cat == "Zeit":
        return ("Zeitmanagement: 1 Partie 10|0 spielen mit Regel 'Vor jedem Zug: Was droht der Gegner?' "
                "– Ziel: nie unter 2 Min. fallen. Alternativ Puzzle Rush (Tempo-Taktik).")
    if cat == "Partie":
        return "Gewertete Rapid-Partie 15|10 (Wochenende) bzw. 10|5 – voll konzentriert, Blunder-Check vor jedem Zug."
    if cat == "Analyse":
        return "Partie sofort OHNE Engine analysieren (kritische Momente notieren), danach mit Engine vergleichen."
    if cat == "Review":
        return ("Wochenreview: alle Partien der Woche mit diesem Tool neu analysieren "
                "(python -m chess_trainer all), Fehlertypen notieren, Ziel für nächste Woche setzen.")
    return cat


def build_plan(profile, start=None, days=365):
    start = start or dt.date.today()
    gm_names = [g["name"] for g in profile["gm_matches"]]
    plan = []
    for d in range(days):
        date = start + dt.timedelta(days=d)
        week = d // 7 + 1
        phase, goal = _phase(week)
        blocks = _weight(_template(date.weekday(), phase), profile["weaknesses"])
        plan.append({
            "day": d + 1, "date": date.isoformat(), "weekday": WEEKDAYS[date.weekday()], "week": week,
            "phase": phase, "phase_goal": goal,
            "blocks": [{"min": m, "cat": c, "task": _task(c, d, week, phase, profile, gm_names)} for m, c in blocks],
        })
    return plan


def rating_projection(current, target=2600):
    """Honest projection: target path vs. typical progress with 1 h/day."""
    if not current:
        return None
    yearly = max(100, min(450, 600 - current / 4))
    quarters = []
    for q in range(1, 5):
        realistic = round(current + yearly * (1 - (1 - q / 4) ** 1.5))
        target_path = round(current + (target - current) * q / 4)
        quarters.append({"q": q, "realistic": realistic, "target": target_path})
    return {"current": current, "target": target, "gap": target - current, "yearly": round(yearly),
            "quarters": quarters}
