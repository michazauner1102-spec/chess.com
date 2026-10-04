"""Aggregate analysed games into a player profile: style vector, archetype,
error statistics, opening statistics, worst mistakes."""

import math
from collections import Counter, defaultdict

from .analyze import TAGS
from .knowledge import DIMS, GRANDMASTERS


def _clamp(x):
    return max(0.0, min(1.0, x))


def _avg(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else 0.0


def build_profile(games):
    if not games:
        raise SystemExit("Keine analysierten Partien vorhanden.")
    n = len(games)
    my_moves = [m for g in games for m in g["moves"]]
    total_moves = len(my_moves) or 1

    outcomes = Counter(g["outcome"] for g in games)
    by_color = {c: Counter(g["outcome"] for g in games if g["color"] == c) for c in ("white", "black")}
    end_reasons = Counter((g["outcome"], g["end_reason"]) for g in games)

    # ---- error statistics
    classes = Counter(m["class"] for m in my_moves)
    errors = [m for m in my_moves if m["class"] in ("Fehler", "Patzer")]
    tag_count = Counter(t for m in errors for t in m["tags"])
    phase_moves = Counter(m["phase"] for m in my_moves)
    phase_errors = Counter(m["phase"] for m in errors)
    phase_acc = {p: round(_avg(m["accuracy"] for m in my_moves if m["phase"] == p), 1) for p in phase_moves}
    phase_err_rate = {p: round(100 * phase_errors[p] / phase_moves[p], 1) for p in phase_moves}

    # ---- style features
    f = [g["features"] for g in games]
    capture_rate = sum(x["captures"] for x in f) / total_moves
    check_rate = sum(x["checks"] for x in f) / total_moves
    storm_rate = sum(x["pawn_storm"] for x in f) / n
    sacs = sum(x["sound_sacs"] for x in f) / n
    early_queen = sum(1 for x in f if x["early_queen"]) / n
    castled = [x for x in f if x["castle_move"]]
    castle_rate = len(castled) / n
    castle_avg = _avg(x["castle_move"] for x in castled)
    long_castle = sum(1 for x in castled if x["castle_side"] == "lang") / (len(castled) or 1)
    opposite = sum(1 for x in castled if x["opp_castle_side"] and x["opp_castle_side"] != x["castle_side"]) / n
    qtrade_early = sum(1 for x in f if x["queen_trade_move"] and x["queen_trade_move"] <= 20) / n
    avg_len = _avg(g["n_moves"] for g in games)
    decisive = (outcomes["win"] + outcomes["loss"]) / n
    mate_wins = sum(1 for g in games if g["outcome"] == "win" and g["end_reason"] == "checkmated") / n

    blunder_rate = classes["Patzer"] / total_moves
    err_rate = len(errors) / total_moves
    eg_moves = phase_moves.get("Endspiel", 0)
    eg_err = phase_errors.get("Endspiel", 0) / eg_moves if eg_moves else err_rate
    style = {
        "angriff": _clamp(0.2 + 2.0 * check_rate + 0.08 * storm_rate + 0.5 * sacs + 0.5 * opposite
                          + 0.3 * mate_wins + 0.3 * long_castle),
        "position": _clamp(0.35 + 0.5 * (1 - capture_rate / 0.35) + 0.25 * castle_rate
                           + (avg_len - 35) / 80 - 0.4 * early_queen),
        "endspiel": _clamp(0.45 + 6 * (err_rate - eg_err) + 0.4 * (eg_moves / total_moves)),
        "schaerfe": _clamp(0.15 + 0.35 * decisive + 0.6 * opposite + 0.3 * sacs + 0.1 * storm_rate
                           - 0.4 * qtrade_early),
        "solide": _clamp(1.05 - 15 * blunder_rate - 0.3 * early_queen + 0.1 * castle_rate - 0.2 * opposite),
    }
    vec = tuple(style[d] for d in DIMS)

    # archetype
    if style["angriff"] + style["schaerfe"] >= style["position"] + style["solide"] + 0.15:
        archetype = "angreifer"
    elif style["position"] + style["solide"] >= style["angriff"] + style["schaerfe"] + 0.15:
        archetype = "positionell"
    else:
        archetype = "universal"

    gms = sorted(GRANDMASTERS, key=lambda gm: _dist(vec, gm["vec"]))
    gm_matches = [{**gm, "match": round(100 * (1 - _dist(vec, gm["vec"]) / math.sqrt(len(DIMS))))}
                  for gm in gms[:4]]

    # ---- openings
    op = defaultdict(lambda: {"n": 0, "w": 0, "d": 0, "l": 0, "acc": []})
    for g in games:
        name = _short_opening(g["opening"])
        key = (g["color"], name)
        op[key]["n"] += 1
        op[key][g["outcome"][0]] += 1
        op[key]["acc"].append(g["accuracy"])
    openings = sorted(
        [{"color": c, "name": nme, "n": v["n"], "w": v["w"], "d": v["d"], "l": v["l"],
          "score": round(100 * (v["w"] + 0.5 * v["d"]) / v["n"]), "acc": round(_avg(v["acc"]), 1)}
         for (c, nme), v in op.items()], key=lambda x: -x["n"])
    first_moves_white = Counter(g["first_moves"].split()[0] for g in games if g["color"] == "white" and g["first_moves"])

    # ---- time management
    spent = [m["spent"] for m in my_moves if m["spent"] is not None]
    tt_errors = tag_count.get("time_trouble", 0)
    timeouts = sum(1 for g in games if g["outcome"] == "loss" and g["end_reason"] == "timeout")

    # ---- worst mistakes (training positions)
    worst = sorted(((g, m) for g in games for m in g["moves"] if m["class"] in ("Patzer", "Fehler")),
                   key=lambda gm: -gm[1]["drop"])[:40]

    ratings = sorted((g["end_time"] or 0, g["my_rating"]) for g in games if g.get("my_rating"))
    current = ratings[-1][1] if ratings else None

    weaknesses = _rank_weaknesses(tag_count, len(errors), phase_err_rate, timeouts, n)

    return {
        "n_games": n, "n_moves": total_moves, "outcomes": dict(outcomes),
        "by_color": {c: dict(v) for c, v in by_color.items()},
        "end_reasons": {f"{k[0]}:{k[1]}": v for k, v in end_reasons.items()},
        "accuracy": round(_avg(g["accuracy"] for g in games), 1),
        "classes": dict(classes), "errors_per_game": round(len(errors) / n, 2),
        "blunders_per_game": round(classes["Patzer"] / n, 2),
        "tags": {TAGS[k]: v for k, v in tag_count.most_common()}, "tag_keys": dict(tag_count),
        "phase_acc": phase_acc, "phase_err_rate": phase_err_rate,
        "style": {k: round(v, 2) for k, v in style.items()}, "archetype": archetype,
        "metrics": {
            "Schlagzüge pro Zug": f"{100 * capture_rate:.0f} %", "Schachgebote pro Zug": f"{100 * check_rate:.0f} %",
            "Rochade-Quote": f"{100 * castle_rate:.0f} % (Ø Zug {castle_avg:.0f})",
            "Lange Rochade": f"{100 * long_castle:.0f} %", "Ungleichseitige Rochaden": f"{100 * opposite:.0f} %",
            "Bauernsturm-Züge pro Partie": f"{storm_rate:.1f}", "Korrekte Opfer pro Partie": f"{sacs:.2f}",
            "Frühe Damenzüge (Zug ≤ 6)": f"{100 * early_queen:.0f} %",
            "Damentausch bis Zug 20": f"{100 * qtrade_early:.0f} %",
            "Ø Partielänge (eigene Züge)": f"{avg_len:.0f}",
            "Entschiedene Partien": f"{100 * decisive:.0f} %",
            "Ø Bedenkzeit pro Zug": f"{_avg(spent):.1f} s",
            "Zeitverluste": f"{timeouts}",
        },
        "gm_matches": gm_matches, "openings": openings, "first_moves_white": dict(first_moves_white),
        "worst": worst, "weaknesses": weaknesses, "current_rating": current,
        "rating_history": ratings, "tt_errors": tt_errors,
    }


def _dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _short_opening(name):
    words = name.split()
    # Chess.com ECO slugs look like "Sicilian Defense Najdorf Variation 6.Be3"; keep the family + variation
    cut = [w for w in words if not any(ch.isdigit() for ch in w)]
    return " ".join(cut[:4]) or name


def _rank_weaknesses(tag_count, n_errors, phase_err_rate, timeouts, n_games):
    """Return weakness keys sorted by severity, used to weight the training plan."""
    score = Counter()
    e = max(1, n_errors)
    score["taktik"] = (tag_count["hung"] + tag_count["missed_tactic"] + tag_count["missed_mate"]
                       + tag_count["allowed_mate"]) / e
    score["strategie"] = tag_count["positional"] / e
    score["zeit"] = (tag_count["time_trouble"] + tag_count["too_fast"]) / e + timeouts / n_games
    score["verwertung"] = tag_count["conversion"] / e
    worst_phase = max(phase_err_rate, key=phase_err_rate.get) if phase_err_rate else "Mittelspiel"
    phase_key = {"Eröffnung": "eroeffnung", "Mittelspiel": "taktik", "Endspiel": "endspiel"}[worst_phase]
    score[phase_key] += 0.25
    score["endspiel"] += 0.05
    score["eroeffnung"] += 0.05
    return [k for k, _ in score.most_common()]
