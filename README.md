# Chess.com Elo-Trainer

Lädt alle Rapid-Partien eines Chess.com-Spielers (Standard: `sleepy_micha`) über die
[Published-Data API](https://www.chess.com/news/view/published-data-api), analysiert jeden Zug mit
Stockfish und erzeugt einen HTML-Report mit:

- **Spielstil-Profil**: Angriffslust, Positionsspiel, Endspiel, Risiko, Solidität (aus Schlagzügen,
  Schachs, Rochaden, Bauernstürmen, Opfern, Damentausch, Partielänge, Patzerquote)
- **Typischen Fehlern**: Ungenauigkeit / Fehler / Patzer (Gewinnwahrscheinlichkeits-Modell wie Lichess),
  getaggt als *Material eingestellt*, *Taktik verpasst*, *Matt übersehen*, *Mattdrohung übersehen*,
  *Gewonnene Stellung verdorben*, *Zeitnot*, *Zu schnell gezogen*, *Positionsfehler* – plus Auswertung
  nach Eröffnung / Mittelspiel / Endspiel
- **Trainingsstellungen** aus deinen eigenen Partien: Brett mit deinem Zug (rot) und dem besseren Zug
  (grün), Hauptvariante, Link zur Partie und zur Analyse
- **Eröffnungsstatistik** und einem **GM-Repertoire**, das zu deinem Stil passt
- **Großmeistern mit ähnlichem Stil** und Modellpartien zum Nachspielen
- **365-Tage-Trainingsplan, 60 Minuten pro Tag**, gewichtet nach deinen größten Schwächen
  (auch als `trainingsplan.csv`)
- einer **ehrlichen Einordnung** des Ziels 2600 mit realistischen Meilensteinen

## Installation

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
# Stockfish: Linux `sudo apt install stockfish`, macOS `brew install stockfish`,
# Windows: https://stockfishchess.org/download/ und Pfad mit --stockfish angeben
```

## Benutzung

```bash
# alles in einem Schritt: laden, analysieren, Report bauen
.venv/bin/python -m chess_trainer all --user sleepy_micha

# danach öffnen:
open report/report.html          # macOS  (Linux: xdg-open, Windows: start)
```

Einzelschritte und Optionen:

```bash
python -m chess_trainer fetch   --user sleepy_micha            # nur Partien laden -> data/
python -m chess_trainer analyze --user sleepy_micha --depth 14  # Analyse (Cache: data/analysis_d14.json)
python -m chess_trainer report  --user sleepy_micha --start 2026-10-05

--time-class rapid|blitz|bullet|daily   # Standard: rapid
--depth 12        # Stockfish-Tiefe: 12 = schnell (~1–2 s/Partie), 16 = gründlicher
--max-games 200   # nur die neuesten N Partien
--threads 4       # CPU-Threads für Stockfish
```

Die Analyse ist inkrementell: bei erneutem Aufruf werden nur neue Partien analysiert. Ideal für das
wöchentliche Review im Trainingsplan.

**Ohne API-Zugriff**: Auf Chess.com unter *Archiv → Partien herunterladen* eine PGN-Datei exportieren und

```bash
python -m chess_trainer import-pgn meine_partien.pgn --user sleepy_micha
python -m chess_trainer report --user sleepy_micha
```

## Aufbau

| Datei | Aufgabe |
|---|---|
| `chess_trainer/fetch.py` | API-Download (seriell, mit Retry bei 429) |
| `chess_trainer/analyze.py` | Stockfish-Analyse pro Zug, Fehlerklassen, Fehler-Tags, Stilmerkmale |
| `chess_trainer/profile.py` | Aggregation: Stilvektor, Archetyp, GM-Ähnlichkeit, Eröffnungsstatistik |
| `chess_trainer/knowledge.py` | GM-Profile, Repertoires, Taktik-/Endspiel-/Strategie-Lehrplan |
| `chess_trainer/plan.py` | 365-Tage-Plan und Rating-Projektion |
| `chess_trainer/report.py` | HTML-Report, CSV-Plan, JSON-Profil |
| `tests/make_fixture.py` | erzeugt künstliche Testpartien (Stockfish gegen sich selbst) |
