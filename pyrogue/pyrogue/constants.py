"""
Costanti globali per PyRogue (Roguelike da terminale in Curses).

Questo modulo centralizza tutti i parametri di configurazione del gioco:
glifi tipografici per tessere ed entità, identificativi delle coppie di colore ANSI
e dimensioni geometriche di riferimento per il dungeon.
"""

# ==============================================================================
# Glifi ASCII per le tessere della mappa (Tile)
# ==============================================================================
CHAR_PLAYER = '@'         # Il protagonista (simbolo classico del genere Roguelike fin dal 1980)
CHAR_WALL = '#'           # Muro impenetrabile di pietra grezza
CHAR_FLOOR = '.'          # Pavimento piano calpestabile
CHAR_DOOR_CLOSED = '+'    # Porta di legno chiusa (richiede interazione per aprirsi)
CHAR_DOOR_OPEN = '/'      # Porta spalancata (calpestabile e trasparente alla vista)
CHAR_WATER = '~'          # Pozza d'acqua sotterranea (estingue gli effetti di fuoco)
CHAR_SPIKES = '^'         # Trappola a spuntoni nascosta nel pavimento (infligge danni fisici)
CHAR_FIRE = '*'           # Fiamme ardenti (infligge danni da fuoco e applica lo stato Bruciatura)
CHAR_CHEST = '$'          # Forziere contenente armi e munizioni
CHAR_STAIRS = '>'         # Scala in discesa verso il piano inferiore del dungeon

# ==============================================================================
# Glifi ASCII per i mostri (Entity)
# ==============================================================================
CHAR_GOBLIN = 'g'         # Goblin: creatura agile, rapida ma con pochi punti ferita
CHAR_ORC = 'O'            # Orco: guerriero robusto con buona forza e resistenza
CHAR_DEMON = 'D'          # Demone: creatura infernale ad alto danno con attacchi infuocati
CHAR_BOSS = 'B'           # Signore dei Demoni (Boss finale al 5° livello)

# ==============================================================================
# Identificativi delle coppie di colore Curses (Color Pair IDs)
# ==============================================================================
COLOR_DEFAULT = 1         # Testo bianco su sfondo trasparente/nero
COLOR_PLAYER = 2          # Giallo brillante per il giocatore
COLOR_WALL = 3            # Bianco / grigio chiaro per le mura
COLOR_FLOOR = 4           # Verde tenue per il pavimento
COLOR_DOOR = 5            # Giallo/ambra per le porte in legno
COLOR_WATER = 6           # Ciano per le pozze d'acqua
COLOR_SPIKES = 7          # Rosso vivo per le trappole a spuntoni
COLOR_FIRE = 8            # Magenta/arancio per le fiamme
COLOR_CHEST = 9           # Giallo dorato per i tesori e forzieri
COLOR_STAIRS = 10         # Verde brillante per le scale sotterranee
COLOR_GOBLIN = 11         # Verde scuro per i Goblin
COLOR_ORC = 12            # Rosso per gli Orchi
COLOR_DEMON = 13          # Magenta per i Demoni
COLOR_BOSS = 14           # Rosso acceso per il Boss infernale
COLOR_UI_HEALTH = 15      # Verde per la barra dei Punti Vita (HP)
COLOR_UI_MANA = 16        # Blu per la barra dei Punti Magia (MP)
COLOR_UI_WARN = 17        # Rosso per avvisi di pericolo e messaggi critici
COLOR_UI_TITLE = 18       # Ciano per titoli di finestre, bordi e menu

# ==============================================================================
# Parametri di configurazione del Dungeon
# ==============================================================================
DEFAULT_MAP_WIDTH = 60    # Larghezza in caselle della mappa sotterranea (asse X)
DEFAULT_MAP_HEIGHT = 20   # Altezza in caselle della mappa sotterranea (asse Y)
INITIAL_DUNGEONS = 4      # 4 livelli normali di discesa prima del livello Boss finale (totale 5 piani)
