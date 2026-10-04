"""Static chess knowledge: style archetypes, grandmaster profiles, GM-level
opening repertoires and training curricula."""

# Style vector dimensions, each 0..1
DIMS = ("angriff", "position", "endspiel", "schaerfe", "solide")
DIM_LABEL = {"angriff": "Angriffslust", "position": "Positionsspiel", "endspiel": "Endspiel",
             "schaerfe": "Risiko/Schärfe", "solide": "Solidität"}

GRANDMASTERS = [
    {"name": "Mikhail Tal", "vec": (0.95, 0.40, 0.45, 1.00, 0.10),
     "why": "Der 'Zauberer aus Riga': Opfer, Initiative und Komplikationen über alles.",
     "games": ["Tal – Botwinnik, WM 1960, Partie 6", "Tal – Larsen, Kandidaten Bled 1965, Partie 10"]},
    {"name": "Garry Kasparov", "vec": (0.90, 0.70, 0.60, 0.85, 0.40),
     "why": "Dynamik, Initiative und tiefe Eröffnungsvorbereitung – Angriff mit System.",
     "games": ["Kasparov – Topalov, Wijk aan Zee 1999", "Karpov – Kasparov, WM 1985, Partie 16"]},
    {"name": "Alexei Shirov", "vec": (0.95, 0.45, 0.50, 0.95, 0.15),
     "why": "Kompromisslos scharf, liebt Feuer auf dem Brett und ungleiche Materialverhältnisse.",
     "games": ["Topalov – Shirov, Linares 1998 (…Lh3!!)"]},
    {"name": "Hikaru Nakamura", "vec": (0.80, 0.60, 0.70, 0.80, 0.40),
     "why": "Weltklasse im Schnellschach: pragmatisch, schnell, extrem gute Intuition und Verteidigung.",
     "games": ["Seine kommentierten Rapid/Blitz-'Speedruns' (Kick/YouTube) als Lernmaterial"]},
    {"name": "Viswanathan Anand", "vec": (0.75, 0.75, 0.70, 0.70, 0.55),
     "why": "Blitzschnelle Berechnung und harmonische Figurenentwicklung – der Schnellschach-König.",
     "games": ["Aronian – Anand, Wijk aan Zee 2013"]},
    {"name": "Bobby Fischer", "vec": (0.75, 0.85, 0.90, 0.60, 0.60),
     "why": "Universell, kristallklar, aktive Figuren und perfekte Technik bis ins Endspiel.",
     "games": ["D. Byrne – Fischer, New York 1956 ('Partie des Jahrhunderts')",
               "Fischer – Spasski, WM 1972, Partie 6"]},
    {"name": "Fabiano Caruana", "vec": (0.60, 0.80, 0.75, 0.55, 0.70),
     "why": "Präzise Rechnung, tiefe Vorbereitung, klassisch-solides Repertoire.",
     "games": ["WM 2018 gegen Carlsen (12 Remis) – Lehrstück in Vorbereitung und Verteidigung"]},
    {"name": "Magnus Carlsen", "vec": (0.50, 0.95, 1.00, 0.40, 0.80),
     "why": "Kleine Vorteile sammeln, Druck halten, Gegner im Endspiel auspressen.",
     "games": ["Carlsen – Anand, WM 2013, Partie 5", "Anand – Carlsen, WM 2013, Partie 6"]},
    {"name": "Anatoly Karpov", "vec": (0.35, 1.00, 0.85, 0.20, 0.90),
     "why": "Würgegriff-Schach: Prophylaxe, Raumgewinn, Gegenspiel wird im Keim erstickt.",
     "games": ["Karpow – Unzicker, Nizza 1974"]},
    {"name": "Vladimir Kramnik", "vec": (0.40, 0.90, 0.85, 0.30, 0.90),
     "why": "Strategische Tiefe und Unbesiegbarkeit – hat die Berliner Mauer berühmt gemacht.",
     "games": ["Kasparow – Kramnik, WM London 2000 (Berliner Verteidigung)"]},
    {"name": "Tigran Petrosian", "vec": (0.20, 0.90, 0.70, 0.10, 1.00),
     "why": "Meister der Prophylaxe und des Qualitätsopfers – erst Sicherheit, dann Gewinn.",
     "games": ["Petrosjan – Spasski, WM 1966, Partie 10"]},
    {"name": "José Raúl Capablanca", "vec": (0.40, 0.90, 1.00, 0.20, 0.85),
     "why": "Einfachheit und Endspieltechnik: vereinfachen, wenn man besser steht.",
     "games": ["Capablanca – Tartakower, New York 1924 (Turmendspiel)"]},
]

ARCHETYPES = {
    "angreifer": {
        "name": "Angreifer / Taktiker",
        "desc": "Du suchst aktiv Initiative, Schachs und Schlagabtausch. Stärke: Dynamik. "
                "Risiko: unsaubere Opfer und offene Flanken.",
    },
    "universal": {
        "name": "Universalspieler",
        "desc": "Kein extremes Profil – du spielst je nach Stellung aktiv oder ruhig. "
                "Damit passt ein klassisches, prinzipielles Repertoire am besten.",
    },
    "positionell": {
        "name": "Positionsspieler / Stratege",
        "desc": "Du bevorzugst ruhige Züge, Struktur und lange Partien. Stärke: Stabilität. "
                "Risiko: Passivität und verpasste taktische Chancen.",
    },
}

# GM-level repertoires per archetype. Lines are main lines as played at top level.
REPERTOIRE = {
    "angreifer": {
        "weiss": {
            "name": "1.e4 – Offener Sizilianer & Schottisch",
            "line": "1.e4 c5 2.Sf3 d6 3.d4 cxd4 4.Sxd4 Sf6 5.Sc3 a6 6.Le3 e5 7.Sb3 Le6 8.f3 (Englischer Angriff)",
            "extra": "Gegen 1…e5: Schottisch 1.e4 e5 2.Sf3 Sc6 3.d4 exd4 4.Sxd4 · "
                     "gegen Caro-Kann: Vorstoß 3.e5 Lf5 4.Sf3 e6 5.Le2 (Short-System)",
            "plans": "Lange Rochade, Bauernsturm g4–g5/h4, Figuren schnell auf den Königsflügel.",
            "gms": "Kasparov, Anand, Nakamura, Caruana",
        },
        "schwarz_e4": {
            "name": "Sizilianisch Najdorf",
            "line": "1.e4 c5 2.Sf3 d6 3.d4 cxd4 4.Sxd4 Sf6 5.Sc3 a6",
            "plans": "…e5 oder …e6, Gegenspiel am Damenflügel mit …b5, Tc8, Qualitätsopfer auf c3.",
            "gms": "Fischer, Kasparov, Vachier-Lagrave",
        },
        "schwarz_d4": {
            "name": "Königsindisch",
            "line": "1.d4 Sf6 2.c4 g6 3.Sc3 Lg7 4.e4 d6 5.Sf3 O-O 6.Le2 e5 7.O-O Sc6 8.d5 Se7 (Mar del Plata)",
            "plans": "Bauernsturm …f5–f4–g5 gegen den weißen König, Weiß greift am Damenflügel an.",
            "gms": "Kasparov, Nakamura, Radjabov",
        },
    },
    "universal": {
        "weiss": {
            "name": "1.e4 – Spanisch (Ruy Lopez)",
            "line": "1.e4 e5 2.Sf3 Sc6 3.Lb5 a6 4.La4 Sf6 5.O-O Le7 6.Te1 b5 7.Lb3 d6 8.c3 O-O 9.h3",
            "extra": "Gegen Sizilianisch: 3.Lb5 (Rossolimo) bzw. 2…d6 3.Lb5+ · gegen Französisch: 3.Sd2 (Tarrasch)",
            "plans": "Zentrum d4 vorbereiten, Springermanöver Sbd2–f1–g3, langfristiger Druck.",
            "gms": "Fischer, Caruana, Carlsen, Anand",
        },
        "schwarz_e4": {
            "name": "1…e5 – Geschlossenes Spanisch / Marshall-Angriff",
            "line": "1.e4 e5 2.Sf3 Sc6 3.Lb5 a6 4.La4 Sf6 5.O-O Le7 6.Te1 b5 7.Lb3 O-O 8.c3 d5 (Marshall)",
            "plans": "Bauernopfer für Initiative am Königsflügel – solide Basis mit Angriffsoption.",
            "gms": "Aronian, Caruana, Anand",
        },
        "schwarz_d4": {
            "name": "Nimzoindisch",
            "line": "1.d4 Sf6 2.c4 e6 3.Sc3 Lb4",
            "plans": "Kontrolle über e4, Doppelbauern auf c3 provozieren, flexibles Zentrum.",
            "gms": "Karpov, Kasparov, Carlsen, Caruana",
        },
    },
    "positionell": {
        "weiss": {
            "name": "1.d4 – Katalanisch",
            "line": "1.d4 Sf6 2.c4 e6 3.g3 d5 4.Lg2 Le7 5.Sf3 O-O 6.O-O dxc4 7.Dc2",
            "extra": "Gegen Königsindisch/Grünfeld: Fianchetto-System mit g3 · "
                     "gegen Slawisch: 3.Sf3 Sf6 4.e3 (ruhige Struktur)",
            "plans": "Langfristiger Druck auf der Diagonale h1–a8 und am Damenflügel, kaum Risiko.",
            "gms": "Kramnik, Carlsen, Ding Liren",
        },
        "schwarz_e4": {
            "name": "Caro-Kann (Klassisch)",
            "line": "1.e4 c6 2.d4 d5 3.Sc3 dxe4 4.Sxe4 Lf5 5.Sg3 Lg6 6.h4 h6 7.Sf3 Sd7 8.h5 Lh7 9.Ld3 Lxd3 10.Dxd3",
            "plans": "Gesunde Bauernstruktur, guter Läufer außerhalb der Kette, Endspiele oft angenehm.",
            "gms": "Karpov, Anand, Ding Liren, Carlsen",
        },
        "schwarz_d4": {
            "name": "Abgelehntes Damengambit (Tartakower)",
            "line": "1.d4 d5 2.c4 e6 3.Sc3 Sf6 4.Lg5 Le7 5.e3 O-O 6.Sf3 h6 7.Lh4 b6",
            "plans": "Solides Zentrum, Befreiungsschläge …c5 oder …e5, Läufer auf b7.",
            "gms": "Kramnik, Karpov, Carlsen",
        },
    },
}

TACTIC_THEMES = [
    "Gabel (Springer/Bauer/Dame)", "Fesselung", "Spieß", "Abzugsangriff & Abzugsschach",
    "Doppelangriff", "Überlastung", "Ablenkung", "Hinlenkung", "Grundreihenmatt",
    "Zwischenzug", "Linienräumung & Feldräumung", "Desperado", "Hängende Figuren erkennen",
    "Läuferopfer auf h7/h2 (griechisches Geschenk)", "Erstickter Mattangriff",
    "Mattbilder: Anastasia, Arabisch, Boden, Epaulette", "Unterbrechung", "Patt-Tricks in der Verteidigung",
    "Bauerndurchbruch", "Schwache Grundreihe / Luftloch", "Qualitätsopfer", "X-Ray / Röntgenangriff",
    "Damenfang", "Gemischte Kombinationen (2–3 Motive)",
]

ENDGAME_CURRICULUM = [
    "Grundmatts: D+K, T+K, 2 Läufer gegen König",
    "Bauernendspiele: Opposition, Quadratregel",
    "Bauernendspiele: Schlüsselfelder, Triangulation",
    "Lucena-Stellung (Brückenbau)",
    "Philidor-Stellung (Verteidigung im Turmendspiel)",
    "Turm + Bauer gegen Turm: Vancura & Seitenschach",
    "Turmendspiele: aktiver Turm, Turm hinter Freibauern",
    "Leichtfigurenendspiele: guter vs. schlechter Läufer",
    "Springer gegen Läufer",
    "Ungleichfarbige Läufer: Festung erkennen",
    "Damenendspiele: Dauerschach & Königssicherheit",
    "Läufer + Springer Matt",
    "Praktische Turmendspiele (Capablanca/Carlsen-Partien)",
    "Festungen und Remistechniken",
]

STRATEGY_THEMES = [
    "Isolani (IQP) – Angriff vs. Blockade", "Hängende Bauern", "Carlsbad-Struktur & Minoritätsangriff",
    "Offene Linien & Vorposten", "Schwache Felder & Felderkomplexe", "Guter vs. schlechter Läufer",
    "Königsangriff bei gleichseitiger Rochade", "Königsangriff bei ungleichseitiger Rochade",
    "Prophylaxe: Was will mein Gegner?", "Figurenverbesserung (schlechteste Figur zuerst)",
    "Zentrum: Druck, Bruch, Blockade", "Vereinfachung & Abtausch in Gewinnstellung",
    "Raumvorteil nutzen", "Bauernmehrheiten am Damenflügel", "Qualitätsopfer als Strategie",
    "Dynamik vs. Statik: Initiative bewerten",
]
