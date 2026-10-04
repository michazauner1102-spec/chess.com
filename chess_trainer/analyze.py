"""Engine analysis of every game: per-move evaluation, error classification
and tagging of typical error patterns, plus raw style features."""

import io
import json
import math
import shutil
from pathlib import Path

import chess
import chess.engine
import chess.pgn

PIECE_VALUE = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
MATE_CP = 10000

# Thresholds on the drop in win probability (0-100 scale), same scale Lichess uses.
INACCURACY, MISTAKE, BLUNDER = 5, 10, 15

TAGS = {
    "hung": "Material eingestellt",
    "missed_tactic": "Taktik des Gegners nicht bestraft / Gewinn verpasst",
    "missed_mate": "Matt übersehen",
    "allowed_mate": "Mattdrohung übersehen",
    "conversion": "Gewonnene Stellung verdorben",
    "time_trouble": "Zeitnot",
    "too_fast": "Zu schnell gezogen (< 5 s)",
    "positional": "Positions-/Planfehler (ohne direkten Materialverlust)",
}


def find_stockfish(path=None):
    for cand in (path, shutil.which("stockfish"), "/usr/games/stockfish", "/usr/local/bin/stockfish",
                 "/opt/homebrew/bin/stockfish"):
        if cand and Path(cand).exists():
            return cand
    raise SystemExit("Stockfish nicht gefunden. Installieren (z.B. 'apt install stockfish' / "
                     "'brew install stockfish') oder Pfad mit --stockfish angeben.")


def win_pct(cp):
    """Centipawns (side-to-move POV) -> win probability 0..100 (Lichess model)."""
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1)


def move_accuracy(win_before, win_after):
    """Lichess per-move accuracy formula."""
    drop = max(0.0, win_before - win_after)
    return max(0.0, min(100.0, 103.1668 * math.exp(-0.04354 * drop) - 3.1669))


def material(board, color):
    return sum(PIECE_VALUE[p.piece_type] * (1 if p.color == color else -1) for p in board.piece_map().values())


def non_pawn_material(board):
    return sum(PIECE_VALUE[p.piece_type] for p in board.piece_map().values()
               if p.piece_type not in (chess.PAWN, chess.KING))


def game_phase(board):
    npm = non_pawn_material(board)
    if npm <= 20:
        return "Endspiel"
    if board.fullmove_number <= 12 and npm >= 54:
        return "Eröffnung"
    return "Mittelspiel"


def material_after_line(board, line, color, plies):
    """Material balance after `plies` moves of `line`, continued while captures
    are still being made so that exchanges are not cut off halfway."""
    b = board.copy(stack=False)
    for k, mv in enumerate(line):
        if mv not in b.legal_moves:
            break
        if k >= plies and not b.is_capture(mv):
            break
        if k >= plies + 4:
            break
        b.push(mv)
    return material(b, color)


def _score(info, color):
    return info["score"].pov(color).score(mate_score=MATE_CP)


def _mate(info, color):
    return info["score"].pov(color).mate()


def _base_time(tc):
    try:
        return int(str(tc).split("+")[0].split("/")[-1])
    except ValueError:
        return 600


def analyse_game(engine, game_json, username, limit):
    pgn = chess.pgn.read_game(io.StringIO(game_json["pgn"]))
    if pgn is None:
        return None
    h = pgn.headers
    me = username.lower()
    if game_json["white"]["username"].lower() == me:
        color, my, opp = chess.WHITE, game_json["white"], game_json["black"]
    elif game_json["black"]["username"].lower() == me:
        color, my, opp = chess.BLACK, game_json["black"], game_json["white"]
    else:
        return None

    nodes = list(pgn.mainline())
    boards = [pgn.board()]
    for n in nodes:
        b = boards[-1].copy(stack=False)
        b.push(n.move)
        boards.append(b)

    infos = []
    for b in boards:
        if b.is_game_over():
            infos.append(None)
        else:
            infos.append(engine.analyse(b, limit))

    base = _base_time(game_json.get("time_control", h.get("TimeControl", "600")))
    clocks = [n.clock() for n in nodes]

    def eval_user(i):
        """Evaluation (cp, user POV) of position i."""
        b, info = boards[i], infos[i]
        if info is None:
            if b.is_checkmate():
                return -MATE_CP if b.turn == color else MATE_CP
            return 0
        return _score(info, color)

    moves = []
    feats = {"captures": 0, "checks": 0, "pawn_storm": 0, "sound_sacs": 0, "early_queen": 0,
             "castle_move": None, "castle_side": None, "opp_castle_side": None, "queen_trade_move": None}
    prev_clock = {chess.WHITE: base, chess.BLACK: base}

    for i, node in enumerate(nodes):
        before, after = boards[i], boards[i + 1]
        mover = before.turn
        spent = None
        if clocks[i] is not None:
            spent = max(0.0, prev_clock[mover] - clocks[i])
            prev_clock[mover] = clocks[i]
        mv = node.move

        if mover != color:
            if before.is_castling(mv):
                feats["opp_castle_side"] = "kurz" if chess.square_file(mv.to_square) == 6 else "lang"
            if not after.queens and before.queens and feats["queen_trade_move"] is None:
                feats["queen_trade_move"] = before.fullmove_number
            continue

        # ---- style features (user moves only)
        san = before.san(mv)
        if before.is_capture(mv):
            feats["captures"] += 1
        if after.is_check():
            feats["checks"] += 1
        if before.is_castling(mv) and feats["castle_move"] is None:
            feats["castle_move"] = before.fullmove_number
            feats["castle_side"] = "kurz" if chess.square_file(mv.to_square) == 6 else "lang"
        piece = before.piece_type_at(mv.from_square)
        if piece == chess.QUEEN and before.fullmove_number <= 6:
            feats["early_queen"] += 1
        opp_king = before.king(not color)
        if piece == chess.PAWN and opp_king is not None and feats["opp_castle_side"]:
            rel_rank = chess.square_rank(mv.to_square) if color == chess.WHITE else 7 - chess.square_rank(mv.to_square)
            if abs(chess.square_file(mv.to_square) - chess.square_file(opp_king)) <= 1 and 3 <= rel_rank <= 5:
                feats["pawn_storm"] += 1
        if not after.queens and before.queens and feats["queen_trade_move"] is None:
            feats["queen_trade_move"] = before.fullmove_number

        # ---- evaluation
        cp_before, cp_after = eval_user(i), eval_user(i + 1)
        w_before, w_after = win_pct(cp_before), win_pct(cp_after)
        drop = max(0.0, w_before - w_after)
        cls = ("Patzer" if drop >= BLUNDER else "Fehler" if drop >= MISTAKE
               else "Ungenauigkeit" if drop >= INACCURACY else "ok")

        info = infos[i]
        best = info["pv"][0] if info and info.get("pv") else None
        best_pv = info.get("pv", []) if info else []
        reply_pv = infos[i + 1].get("pv", []) if infos[i + 1] else []

        mat_now = material(before, color)
        mat_best = material_after_line(before, best_pv, color, 4)
        mat_played = material_after_line(after, reply_pv, color, 3)

        if drop < 5 and 25 <= w_before <= 75 and mat_played <= mat_now - 2 and mat_best >= mat_now - 1:
            feats["sound_sacs"] += 1

        tags = []
        if cls in ("Fehler", "Patzer"):
            mate_b = _mate(info, color) if info else None
            mate_a = _mate(infos[i + 1], color) if infos[i + 1] else None
            if mate_b is not None and mate_b > 0 and not (mate_a is not None and mate_a > 0):
                tags.append("missed_mate")
            if mate_a is not None and mate_a < 0 and not (mate_b is not None and mate_b < 0):
                tags.append("allowed_mate")
            if mat_best - mat_played >= 2:
                tags.append("missed_tactic" if mat_best >= mat_now + 2 else "hung")
            if w_before >= 75 and w_after < 60:
                tags.append("conversion")
            clock_left = clocks[i]
            if clock_left is not None and clock_left < max(30, 0.1 * base):
                tags.append("time_trouble")
            elif spent is not None and spent < 5:
                tags.append("too_fast")
            if not any(t in tags for t in ("missed_mate", "allowed_mate", "hung", "missed_tactic")):
                tags.append("positional")

        moves.append({
            "ply": i, "move_no": before.fullmove_number, "san": san, "uci": mv.uci(),
            "fen": before.fen(), "best_uci": best.uci() if best else None,
            "best_san": before.san(best) if best else None,
            "best_line": _line_san(before, best_pv, 6),
            "reply_line": _line_san(after, reply_pv, 4),
            "cp_before": cp_before, "cp_after": cp_after,
            "win_before": round(w_before, 1), "win_after": round(w_after, 1),
            "drop": round(drop, 1), "accuracy": round(move_accuracy(w_before, w_after), 1),
            "class": cls, "phase": game_phase(before), "clock": clocks[i], "spent": spent, "tags": tags,
        })

    my_moves = len(moves)
    acc = sum(m["accuracy"] for m in moves) / my_moves if my_moves else 0
    result = my["result"]
    outcome = "win" if result == "win" else ("draw" if result in
              ("agreed", "repetition", "stalemate", "insufficient", "50move", "timevsinsufficient") else "loss")
    end_reason = opp["result"] if outcome == "win" else result

    eco_url = game_json.get("eco") or h.get("ECOUrl", "")
    opening = (eco_url.rsplit("/", 1)[-1].replace("-", " ") if eco_url
               else h.get("Opening") or " ".join(n.san() for n in nodes[:4]) or "?")

    return {
        "url": game_json.get("url"), "end_time": game_json.get("end_time"),
        "color": "white" if color == chess.WHITE else "black",
        "my_rating": my.get("rating"), "opp_rating": opp.get("rating"), "opp_name": opp.get("username"),
        "outcome": outcome, "end_reason": end_reason, "eco": h.get("ECO", ""), "opening": opening,
        "first_moves": " ".join(n.san() for n in nodes[:6]),
        "time_control": game_json.get("time_control"), "base_time": base,
        "n_moves": my_moves, "accuracy": round(acc, 1),
        "chesscom_accuracy": (game_json.get("accuracies") or {}).get("white" if color else "black"),
        "features": feats, "moves": moves,
    }


def _line_san(board, pv, n):
    b = board.copy(stack=False)
    out = []
    for mv in pv[:n]:
        if mv not in b.legal_moves:
            break
        out.append(b.san(mv))
        b.push(mv)
    return " ".join(out)


def analyse_all(games, username, out_dir="data", depth=12, stockfish=None, threads=2, hash_mb=128,
                max_games=None, verbose=True):
    """Analyse games (newest first if max_games is set); results are cached per game."""
    out = Path(out_dir)
    cache_file = out / f"analysis_d{depth}.json"
    cache = json.loads(cache_file.read_text()) if cache_file.exists() else {}

    games = sorted(games, key=lambda g: g.get("end_time", 0), reverse=True)
    if max_games:
        games = games[:max_games]
    todo = [g for g in games if g.get("url") not in cache]
    if verbose:
        print(f"{len(games)} Partien ausgewählt, {len(games) - len(todo)} bereits analysiert, {len(todo)} neu.")

    if todo:
        engine = chess.engine.SimpleEngine.popen_uci(find_stockfish(stockfish))
        engine.configure({"Threads": threads, "Hash": hash_mb})
        limit = chess.engine.Limit(depth=depth)
        try:
            for k, g in enumerate(todo, 1):
                res = analyse_game(engine, g, username, limit)
                if res:
                    cache[g["url"]] = res
                if verbose:
                    print(f"  [{k}/{len(todo)}] {g.get('url')}", flush=True)
                if k % 10 == 0:
                    cache_file.write_text(json.dumps(cache))
        finally:
            engine.quit()
        cache_file.write_text(json.dumps(cache))

    return [cache[g["url"]] for g in games if g.get("url") in cache]
