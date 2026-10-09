#!/usr/bin/env python3
"""
================================================================================
  IL GIOCO DELLA VITA DI CONWAY (GAME OF LIFE) — PYTHON PER NERDS
  Simulazione Algoritmica di Automi Cellulari 2D con Topologia Toroidale
================================================================================
Autore: Francesco Clementoni (Python per Nerds)
Paradigma: Esclusivamente Procedurale & Algoritmico (Senza Classi/OOP)
Librerie: Solo Libreria Standard Python (curses, time, random, typing)
================================================================================
"""

import time
import random
import curses
from typing import List, Tuple, Dict, Any

# ==============================================================================
# 1. COSTANTI E CONFIGURAZIONE MATEMATICA (PEP 8)
# ==============================================================================

DENSITA_POPOLAZIONE_INIZIALE = 0.22  # Percentuale di celle vive al setup casuale (22%)
RITARDO_BASE_SECONDI = 0.05          # Velocità predefinita del loop (~20 generazioni/sec)
RITARDO_MINIMO_SECONDI = 0.005       # Velocità massima
RITARDO_MASSIMO_SECONDI = 0.5        # Velocità minima

# Spostamenti relativi delle 8 celle del vicinato di Moore: Δy, Δx
VICINATO_MOORE = (
    (-1, -1), (-1,  0), (-1,  1),
    ( 0, -1),          ( 0,  1),
    ( 1, -1), ( 1,  0), ( 1,  1)
)

# Pattern notevoli per studio matematico
PATTERN_GLIDER = [
    [0, 1, 0],
    [0, 0, 1],
    [1, 1, 1]
]

PATTERN_R_PENTOMINO = [
    [0, 1, 1],
    [1, 1, 0],
    [0, 1, 0]
]

PATTERN_PULSAR = [
    [0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1],
    [0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0],
    [1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0]
]

PATTERN_GOSPER_GUN = [
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,1,1],
    [0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,1,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,1,1],
    [1,1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [1,1,0,0,0,0,0,0,0,0,1,0,0,0,1,0,1,1,0,0,0,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
]

LISTA_PATTERN = [
    ("Glider (Aliante)", PATTERN_GLIDER),
    ("R-Pentomino (Caos)", PATTERN_R_PENTOMINO),
    ("Pulsar (Oscillatore)", PATTERN_PULSAR),
    ("Gosper Glider Gun", PATTERN_GOSPER_GUN)
]


# ==============================================================================
# 2. FUNZIONI MATEMATICHE E ALGORITMICHE PURE
# ==============================================================================

def crea_griglia_vuota(righe: int, colonne: int) -> List[List[int]]:
    """
    Alloca in memoria una matrice 2D di zeri di dimensioni righe x colonne.
    Ogni cella contiene un intero rappresentante l'età della cella (0 = morta).
    """
    return [[0 for _ in range(colonne)] for _ in range(righe)]


def genera_griglia_casuale(righe: int, colonne: int, densita: float = DENSITA_POPOLAZIONE_INIZIALE) -> List[List[int]]:
    """
    Inizializza stocasticamente una matrice 2D distribuendo celle vive (età = 1)
    secondo una distribuzione di Bernoulli con probabilità pari a 'densita'.
    """
    return [
        [1 if random.random() < densita else 0 for _ in range(colonne)]
        for _ in range(righe)
    ]


def inserisci_pattern(
    griglia: List[List[int]],
    pattern: List[List[int]],
    riga_centro: int,
    colonna_centro: int
) -> None:
    """
    Inietta una matrice binaria di un pattern notevole all'interno della griglia,
    centrandola alle coordinate fornite e gestendo il wrap-around toroidale.
    """
    num_righe = len(griglia)
    num_colonne = len(griglia[0]) if num_righe > 0 else 0

    p_h = len(pattern)
    p_w = len(pattern[0]) if p_h > 0 else 0

    r_offset = riga_centro - (p_h // 2)
    c_offset = colonna_centro - (p_w // 2)

    for r in range(p_h):
        for c in range(p_w):
            if pattern[r][c] == 1:
                # Coordinate sul toroide bidimensionale
                ty = (r_offset + r) % num_righe
                tx = (c_offset + c) % num_colonne
                griglia[ty][tx] = 1


def conta_vicini_vivi(
    griglia: List[List[int]],
    riga: int,
    colonna: int,
    tot_righe: int,
    tot_colonne: int
) -> int:
    """
    Calcola la convoluzione discreta del Vicinato di Moore a 8 celle.
    Applica le condizioni periodiche al contorno (Topologia Toroidale T^2):
      y_vicino = (riga + dy) mod tot_righe
      x_vicino = (colonna + dx) mod tot_colonne
    """
    somma_vicini = 0
    for dy, dx in VICINATO_MOORE:
        ny = (riga + dy) % tot_righe
        nx = (colonna + dx) % tot_colonne
        if griglia[ny][nx] > 0:
            somma_vicini += 1
    return somma_vicini


def calcola_prossima_generazione(
    griglia_corrente: List[List[int]],
    tot_righe: int,
    tot_colonne: int
) -> Tuple[List[List[int]], int, int, int]:
    """
    Funzione di transizione globale per l'automa cellulare di Conway.
    Regola B3/S23 (Birth on 3, Survival on 2 or 3):
      1. Sotto-popolazione: una cella viva con < 2 vicini muore (diventa 0).
      2. Sopravvivenza: una cella viva con 2 o 3 vicini sopravvive (incrementa età).
      3. Sovrappopolazione: una cella viva con > 3 vicini muore (diventa 0).
      4. Riproduzione: una cella morta con esattamente 3 vicini nasce (diventa 1).

    Restituisce: (nuova_griglia, popolazione_totale, nuove_nascite, morti)
    """
    nuova_griglia = crea_griglia_vuota(tot_righe, tot_colonne)
    popolazione = 0
    nascite = 0
    morti = 0

    for r in range(tot_righe):
        for c in range(tot_colonne):
            eta_attuale = griglia_corrente[r][c]
            vicini = conta_vicini_vivi(griglia_corrente, r, c, tot_righe, tot_colonne)

            if eta_attuale > 0:
                # Cella viva: sopravvive solo con 2 o 3 vicini
                if vicini == 2 or vicini == 3:
                    nuova_griglia[r][c] = min(eta_attuale + 1, 1000)  # Incremento età
                    popolazione += 1
                else:
                    nuova_griglia[r][c] = 0  # Morte per isolamento o sovraffollamento
                    morti += 1
            else:
                # Cella morta: nasce se ha esattamente 3 vicini
                if vicini == 3:
                    nuova_griglia[r][c] = 1  # Nuova nascita
                    popolazione += 1
                    nascite += 1
                else:
                    nuova_griglia[r][c] = 0

    return nuova_griglia, popolazione, nascite, morti


# ==============================================================================
# 3. INTERFACCIA GRAFICA TERMINALE (CURSES)
# ==============================================================================

def inizializza_colori() -> None:
    """Configura le coppie di colori basate sull'età biologica delle celle."""
    curses.start_color()
    curses.use_default_colors()

    # ID 1: Neonato (Età 1) -> Ciano brillante
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    # ID 2: Giovane (Età 2-5) -> Verde brillante
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    # ID 3: Maturo (Età 6-15) -> Giallo
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    # ID 4: Anziano (Età 16-50) -> Magenta
    curses.init_pair(4, curses.COLOR_MAGENTA, -1)
    # ID 5: Antico / Oscillatore Stabile (Età > 50) -> Blu / Bianco
    curses.init_pair(5, curses.COLOR_WHITE, -1)
    # ID 6: HUD & Cornici
    curses.init_pair(6, curses.COLOR_WHITE, -1)
    # ID 7: Allarme / Pausa
    curses.init_pair(7, curses.COLOR_RED, -1)


def ottieni_attributo_cella(eta: int) -> Tuple[int, str]:
    """Restituisce il colore e il glifo ASCII in base all'età della cella."""
    if eta == 1:
        return curses.color_pair(1) | curses.A_BOLD, "o"
    elif eta <= 5:
        return curses.color_pair(2) | curses.A_BOLD, "O"
    elif eta <= 15:
        return curses.color_pair(3) | curses.A_BOLD, "0"
    elif eta <= 50:
        return curses.color_pair(4) | curses.A_BOLD, "@"
    else:
        return curses.color_pair(5) | curses.A_BOLD, "#"


def disegna_simulazione(
    stdscr: Any,
    griglia: List[List[int]],
    generazione: int,
    popolazione: int,
    picco_popolazione: int,
    in_pausa: bool,
    ritardo: float,
    pattern_selezionato_idx: int
) -> None:
    """Renderizza la griglia sul terminale con cornice informativa e statistiche."""
    max_y, max_x = stdscr.getmaxyx()
    tot_righe = len(griglia)
    tot_colonne = len(griglia[0]) if tot_righe > 0 else 0

    stdscr.erase()

    # 1. Barra Superiore: Statistiche e Stato
    stato_str = "[PAUSA]" if in_pausa else "[ATTIVO]"
    attr_stato = curses.color_pair(7) | curses.A_BOLD if in_pausa else curses.color_pair(2) | curses.A_BOLD
    gen_str = f"GEN: {generazione:06d}"
    pop_str = f"POP: {popolazione:04d} (MAX: {picco_popolazione:04d})"
    vel_str = f"VEL: {1.0 / ritardo:4.1f} gen/s"

    try:
        stdscr.addstr(0, 2, " Conway's Game of Life ", curses.color_pair(6) | curses.A_BOLD | curses.A_STANDOUT)
        stdscr.addstr(0, 28, stato_str, attr_stato)
        stdscr.addstr(0, 38, gen_str, curses.color_pair(6) | curses.A_BOLD)
        stdscr.addstr(0, 52, pop_str, curses.color_pair(3) | curses.A_BOLD)
        stdscr.addstr(0, max_x - 20, vel_str, curses.color_pair(1))
        stdscr.addstr(1, 0, "─" * (max_x - 1), curses.color_pair(6) | curses.A_DIM)
    except Exception:
        pass

    # 2. Rendering della Griglia di Celle
    # Si mappa la matrice all'area visibile tra riga 2 e max_y - 3
    area_h = min(tot_righe, max_y - 5)
    area_w = min(tot_colonne, (max_x - 2) // 2)

    for r in range(area_h):
        for c in range(area_w):
            eta = griglia[r][c]
            if eta > 0:
                attr, char = ottieni_attributo_cella(eta)
                # Nel terminale le celle sono stampate a coppie di caratteri per aspect ratio 2:1
                try:
                    stdscr.addstr(2 + r, 1 + (c * 2), char + " ", attr)
                except Exception:
                    pass

    # 3. Barra Inferiore: Pattern Selezionato & Comandi (compatibile con 80 colonne)
    riga_f = max_y - 2
    nome_pattern, _ = LISTA_PATTERN[pattern_selezionato_idx]

    if max_x >= 105:
        riga_pattern = f" Pattern: [{pattern_selezionato_idx + 1}/4] <{nome_pattern}>  ([TAB/N] Sfoglia  [P/INVIO] Inietta) | Età: o -> O -> 0 -> @ -> #"
    else:
        riga_pattern = f" Pattern: [{pattern_selezionato_idx + 1}/4] <{nome_pattern}>  ([TAB/N] Sfoglia  [P/INVIO] Inietta  [1-4] Rapido)"

    guida = " [SPAZIO] Pausa  [S] Step  [R] Random  [C] Reset  [+/-] Vel  [Q/ESC] Esci "

    try:
        stdscr.addstr(riga_f - 1, 0, "─" * (max_x - 1), curses.color_pair(6) | curses.A_DIM)
        stdscr.addstr(riga_f - 1, 2, riga_pattern[:max_x - 4], curses.color_pair(6) | curses.A_BOLD)
        stdscr.addstr(riga_f, 1, guida[:max_x - 2], curses.color_pair(6) | curses.A_STANDOUT)
    except Exception:
        pass

    stdscr.refresh()


# ==============================================================================
# 4. GAME LOOP PROCEDURALE PRINCIPALE
# ==============================================================================

def esegui_gioco_della_vita(stdscr: Any) -> None:
    """Ciclo principale di esecuzione: coordinamento input, evoluzione e rendering."""
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)
    inizializza_colori()

    max_y, max_x = stdscr.getmaxyx()
    # Dimensioni della matrice basate sullo spazio terminale
    righe_griglia = max(10, max_y - 5)
    colonne_griglia = max(10, (max_x - 2) // 2)

    # Inizializzazione variabili di stato algoritmico
    griglia = genera_griglia_casuale(righe_griglia, colonne_griglia)
    generazione = 0
    popolazione = sum(1 for riga in griglia for val in riga if val > 0)
    picco_popolazione = popolazione
    in_pausa = False
    ritardo_frame = RITARDO_BASE_SECONDI
    pattern_idx = 0
    in_esecuzione = True

    while in_esecuzione:
        t_inizio = time.perf_counter()

        # 1. Rilevamento ridimensionamento terminale
        cur_y, cur_x = stdscr.getmaxyx()
        if cur_y != max_y or cur_x != max_x:
            max_y, max_x = cur_y, cur_x
            nuove_r = max(10, max_y - 5)
            nuove_c = max(10, (max_x - 2) // 2)
            # Rialloca griglia preservando la popolazione precedente
            nuova_g = crea_griglia_vuota(nuove_r, nuove_c)
            for r in range(min(righe_griglia, nuove_r)):
                for c in range(min(colonne_griglia, nuove_c)):
                    nuova_g[r][c] = griglia[r][c]
            griglia = nuova_g
            righe_griglia, colonne_griglia = nuove_r, nuove_c

        # 2. Gestione Input Asincrono
        try:
            tasto = stdscr.getch()
        except Exception:
            tasto = -1

        if tasto in (27, ord('q'), ord('Q')):        # ESC o Q: Esci
            in_esecuzione = False
            break
        elif tasto == ord(' '):                       # Spazio: Pausa / Riprendi
            in_pausa = not in_pausa
        elif tasto in (ord('s'), ord('S')):           # S: Esegui Singolo Step
            griglia, popolazione, _, _ = calcola_prossima_generazione(griglia, righe_griglia, colonne_griglia)
            generazione += 1
            if popolazione > picco_popolazione:
                picco_popolazione = popolazione
        elif tasto in (ord('r'), ord('R')):           # R: Re-inizializza Casuale
            griglia = genera_griglia_casuale(righe_griglia, colonne_griglia)
            generazione = 0
            popolazione = sum(1 for riga in griglia for val in riga if val > 0)
            picco_popolazione = popolazione
        elif tasto in (ord('c'), ord('C')):           # C: Pulisci Griglia
            griglia = crea_griglia_vuota(righe_griglia, colonne_griglia)
            generazione = 0
            popolazione = 0
            picco_popolazione = 0
        elif tasto in (9, ord('\t'), ord('n'), ord('N')):   # TAB o N: Sfoglia / seleziona il prossimo pattern
            pattern_idx = (pattern_idx + 1) % len(LISTA_PATTERN)
        elif tasto in (ord('1'), ord('2'), ord('3'), ord('4')): # 1-4: Seleziona e inietta direttamente
            scelta_idx = int(chr(tasto)) - 1
            if 0 <= scelta_idx < len(LISTA_PATTERN):
                pattern_idx = scelta_idx
                _, pattern_mat = LISTA_PATTERN[pattern_idx]
                centro_y = righe_griglia // 2
                centro_x = colonne_griglia // 2
                inserisci_pattern(griglia, pattern_mat, centro_y, centro_x)
                popolazione = sum(1 for riga in griglia for val in riga if val > 0)
        elif tasto in (ord('p'), ord('P'), 10, ord('\n'), curses.KEY_ENTER): # P o INVIO: Inietta il pattern selezionato
            _, pattern_mat = LISTA_PATTERN[pattern_idx]
            centro_y = righe_griglia // 2
            centro_x = colonne_griglia // 2
            inserisci_pattern(griglia, pattern_mat, centro_y, centro_x)
            popolazione = sum(1 for riga in griglia for val in riga if val > 0)
        elif tasto in (ord('+'), ord('='), curses.KEY_UP):   # Aumenta Velocità
            ritardo_frame = max(RITARDO_MINIMO_SECONDI, ritardo_frame * 0.75)
        elif tasto in (ord('-'), ord('_'), curses.KEY_DOWN): # Diminuisci Velocità
            ritardo_frame = min(RITARDO_MASSIMO_SECONDI, ritardo_frame * 1.35)

        # 3. Evoluzione dell'Automa (se non in pausa)
        if not in_pausa:
            griglia, popolazione, _, _ = calcola_prossima_generazione(griglia, righe_griglia, colonne_griglia)
            generazione += 1
            if popolazione > picco_popolazione:
                picco_popolazione = popolazione

        # 4. Disegno a Video (Curses)
        disegna_simulazione(
            stdscr,
            griglia,
            generazione,
            popolazione,
            picco_popolazione,
            in_pausa,
            ritardo_frame,
            pattern_idx
        )

        # 5. Temporizzazione del Frame
        tempo_impiegato = time.perf_counter() - t_inizio
        tempo_attesa = ritardo_frame - tempo_impiegato
        if tempo_attesa > 0:
            time.sleep(tempo_attesa)


def main() -> None:
    """Entrypoint di avvio con gestione sicura di curses."""
    try:
        curses.wrapper(esegui_gioco_della_vita)
    except KeyboardInterrupt:
        pass
    finally:
        print("\nSimulazione terminata. Buona esplorazione matematica con Python per Nerds!\n")


if __name__ == "__main__":
    main()
