"""
==============================================================================
Dino Run in Terminale (ASCII Art)
Capitolo: Primi passi con Python e Programmazione Procedurale
==============================================================================

Questo programma implementa una versione da riga di comando del celebre
gioco "Dino Run" di Chrome (quando si è offline).

Concetti di Python trattati in questo esempio:
1. Variabili e Tipi primitivi (int, float, bool, str)
2. Costanti e convenzioni di denominazione
3. Liste e Dizionari per memorizzare elementi del gioco
4. Ciclo principale (Game Loop) con 'while'
5. Istruzioni condizionali ('if', 'elif', 'else')
6. Funzioni con argomenti e valori di ritorno ('def' e 'return')
7. Moduli della libreria standard di Python:
   - 'curses' : per gestire lo schermo e i tasti nel terminale
   - 'time'   : per regolare la velocità dei fotogrammi (FPS)
   - 'random' : per generare gli ostacoli in modo casuale
==============================================================================
"""

import curses
import random
import time
from typing import Any, Dict, List

# ==============================================================================
# 1. COSTANTI E CONFIGURAZIONI DEL GIOCO
# ==============================================================================

# Dimensioni dell'area di gioco
LARGHEZZA = 70
ALTEZZA = 20
RIGA_TERRENO = 15  # Livello del suolo (indice di riga nel terminale)

# Fotogrammi ASCII per il dinosauro (ognuno largo 7 caratteri e alto 4 righe)
DINO_CORSA_1 = [
    r"    __ ",
    r"   / _)",
    r"  | \_ ",
    r"   / \ "
]

DINO_CORSA_2 = [
    r"    __ ",
    r"   / _)",
    r"  | \_ ",
    r"   | | "
]

DINO_SALTO = [
    r"    __ ",
    r"   / _)",
    r"  | \_ ",
    r"   / / "
]

DINO_LARGHEZZA = 7
DINO_ALTEZZA = 4
DINO_POS_X = 6  # Posizione orizzontale fissa del dinosauro

# Parametri fisici del salto
VELOCITA_SALTO = -2.1  # Spinta iniziale verso l'alto (valore negativo)
GRAVITA = 0.33         # Accelerazione verso il basso per fotogramma


# Disegni ASCII dei Cactus (2 dimensioni diverse)
CACTUS_PICCOLO = [
    r" | ",
    r"\|/"
]
CACTUS_PICCOLO_W = 3
CACTUS_PICCOLO_H = 2

CACTUS_GRANDE = [
    r" | | ",
    r"\|_|/",
    r"  |  "
]
CACTUS_GRANDE_W = 5
CACTUS_GRANDE_H = 3


# ==============================================================================
# 2. FUNZIONI DI UTILITÀ E LOGICA DI GIOCO
# ==============================================================================

def crea_cactus(tipo: str, pos_x: float) -> Dict[str, Any]:
    """
    Crea un nuovo cactus utilizzando un dizionario.
    - 'tipo': stringa ("piccolo" oppure "grande")
    - 'x': coordinata orizzontale di partenza (float)
    """
    return {
        "tipo": tipo,
        "x": float(pos_x)
    }


def disegna_testo(schermo: Any, y: float, x: float, testo: str) -> None:
    """
    Disegna in modo sicuro una stringa sullo schermo alle coordinate (y, x),
    evitando che curses sollevi errori se il testo tocca i bordi.
    """
    if 0 <= y < ALTEZZA and 0 <= x < LARGHEZZA:
        # Tronca il testo se supera la larghezza massima
        spazio_disponibile = LARGHEZZA - x
        testo_visibile = testo[:spazio_disponibile]
        try:
            schermo.addstr(int(y), int(x), testo_visibile)
        except curses.error:
            pass


def disegna_dinosauro(schermo: Any, pos_y: float, in_salto: bool, frame_animazione: int) -> None:
    """
    Disegna il dinosauro selezionando il fotogramma adatto:
    - se sta saltando, mostra il fotogramma di salto
    - se corre, alterna i due fotogrammi di corsa
    """
    if in_salto:
        sprite = DINO_SALTO
    elif frame_animazione == 0:
        sprite = DINO_CORSA_1
    else:
        sprite = DINO_CORSA_2

    # Disegna ogni riga dello sprite
    for riga_idx, riga_testo in enumerate(sprite):
        riga_y = int(pos_y) + riga_idx
        disegna_testo(schermo, riga_y, DINO_POS_X, riga_testo)


def disegna_cactus(schermo: Any, cactus: Dict[str, Any]) -> None:
    """
    Disegna un cactus sullo schermo in base al suo tipo e alla sua posizione x.
    """
    tipo = cactus["tipo"]
    pos_x = int(cactus["x"])

    if tipo == "piccolo":
        sprite = CACTUS_PICCOLO
        altezza = CACTUS_PICCOLO_H
    else:
        sprite = CACTUS_GRANDE
        altezza = CACTUS_GRANDE_H

    # La base del cactus poggia esattamente sul terreno
    pos_y = RIGA_TERRENO - altezza

    for riga_idx, riga_testo in enumerate(sprite):
        y_corrente = pos_y + riga_idx

        # Se il cactus è completamente o parzialmente all'interno dello schermo
        if pos_x >= 0:
            disegna_testo(schermo, y_corrente, pos_x, riga_testo)
        elif pos_x + len(riga_testo) > 0:
            # Taglio dello sprite quando sta uscendo a sinistra dello schermo
            offset = abs(pos_x)
            testo_ritagliato = riga_testo[offset:]
            disegna_testo(schermo, y_corrente, 0, testo_ritagliato)


def disegna_terreno(schermo: Any, tick_gioco: int) -> None:
    """
    Disegna la linea del terreno e dettagli scorrevoli sotto di essa
    per dare un effetto di velocità.
    """
    # Linea orizzontale continua
    linea = "=" * LARGHEZZA
    disegna_testo(schermo, RIGA_TERRENO, 0, linea)

    # Dettagli del suolo in movimento
    dettagli = ""
    for colonna in range(LARGHEZZA):
        pattern = (colonna + tick_gioco) % 16
        if pattern == 0:
            dettagli += "."
        elif pattern == 6:
            dettagli += "_"
        elif pattern == 11:
            dettagli += "^"
        else:
            dettagli += " "
    disegna_testo(schermo, RIGA_TERRENO + 1, 0, dettagli)


def controlla_collisione(dino_y: float, cactus: Dict[str, Any]) -> bool:
    """
    Verifica se c'è collisione tra il dinosauro e un cactus
    utilizzando il controllo di sovrapposizione tra rettangoli (Bounding Box).
    """
    # Rettangolo del Dinosauro (con un piccolo margine di tolleranza)
    dino_x1 = DINO_POS_X + 1
    dino_x2 = DINO_POS_X + DINO_LARGHEZZA - 1
    dino_y1 = int(dino_y)
    dino_y2 = int(dino_y) + DINO_ALTEZZA

    # Dimensioni del cactus in base al tipo
    cactus_x1 = int(cactus["x"])
    if cactus["tipo"] == "piccolo":
        cactus_w = CACTUS_PICCOLO_W
        cactus_h = CACTUS_PICCOLO_H
    else:
        cactus_w = CACTUS_GRANDE_W
        cactus_h = CACTUS_GRANDE_H

    cactus_x2 = cactus_x1 + cactus_w
    cactus_y1 = RIGA_TERRENO - cactus_h
    cactus_y2 = RIGA_TERRENO

    # Due rettangoli si sovrappongono se si intersecano sia in X sia in Y
    sovrapposizione_x = (dino_x1 < cactus_x2) and (dino_x2 > cactus_x1)
    sovrapposizione_y = (dino_y1 < cactus_y2) and (dino_y2 > cactus_y1)

    return sovrapposizione_x and sovrapposizione_y


# ==============================================================================
# 3. CICLO PRINCIPALE DEL GIOCO (GAME LOOP)
# ==============================================================================

def esegui_gioco(schermo: Any) -> None:
    """
    Funzione principale del gioco.
    Contiene il 'Game Loop' suddiviso nelle 3 fasi standard:
    1. Input: lettura dei tasti
    2. Update: aggiornamento di posizioni, gravità e punteggi
    3. Render: disegno degli elementi a video
    """
    # Configurazione della libreria curses
    curses.curs_set(0)       # Nasconde il cursore di testo
    schermo.nodelay(True)    # getch() non blocca il programma se non ci sono tasti
    schermo.timeout(0)

    # Variabili di stato del punteggio
    punteggio = 0
    record = 0
    game_over = False
    in_esecuzione = True

    # Variabili del dinosauro (posizione e fisica del salto)
    dino_y_terra = float(RIGA_TERRENO - DINO_ALTEZZA)
    dino_y = float(dino_y_terra)
    velocita_y = 0.0
    in_salto = False

    # Lista degli ostacoli attualmente attivi sullo schermo
    ostacoli = []
    distanza_da_ultimo_cactus = 0

    # Contatore di fotogrammi
    tick = 0

    while in_esecuzione:
        # Verifica dimensione della finestra del terminale
        max_y, max_x = schermo.getmaxyx()
        if max_y < ALTEZZA or max_x < LARGHEZZA:
            schermo.clear()
            messaggio = f"Ingrandisci la finestra a min. {LARGHEZZA}x{ALTEZZA}"
            disegna_testo(schermo, 0, 0, messaggio)
            schermo.refresh()
            time.sleep(0.2)
            continue

        # ----------------------------------------------------------------------
        # FASE 1: GESTIONE DEGLI INPUT
        # ----------------------------------------------------------------------
        tasto = schermo.getch()

        # Uscita dal gioco con 'q', 'Q' o ESC
        if tasto in (27, ord('q'), ord('Q')):
            in_esecuzione = False

        if game_over:
            # Se siamo in Game Over, premiamo SPAZIO, INVIO, 'R' o Freccia SU per ricominciare
            if tasto in (ord(' '), ord('\n'), curses.KEY_UP, ord('r'), ord('R')):
                punteggio = 0
                ostacoli = []
                dino_y = float(dino_y_terra)
                velocita_y = 0.0
                in_salto = False
                distanza_da_ultimo_cactus = 0
                tick = 0
                game_over = False
        else:
            # Durante la partita: SPAZIO o Freccia SU avviano il salto
            if tasto in (ord(' '), curses.KEY_UP) and not in_salto:
                in_salto = True
                velocita_y = VELOCITA_SALTO

        # ----------------------------------------------------------------------
        # FASE 2: AGGIORNAMENTO DELLA LOGICA (FISICA, PUNTI, OSTACOLI)
        # ----------------------------------------------------------------------
        if not game_over:
            tick += 1

            # Incremento del punteggio (ogni 2 tick)
            if tick % 2 == 0:
                punteggio += 1
                if punteggio > record:
                    record = punteggio

            # Fisica del salto (Gravità)
            if in_salto:
                dino_y += velocita_y
                velocita_y += GRAVITA  # La gravità accelera verso il basso

                # Controllo atterraggio al suolo
                if dino_y >= dino_y_terra:
                    dino_y = float(dino_y_terra)
                    in_salto = False
                    velocita_y = 0.0

            # Spostamento dei cactus verso sinistra
            for cactus in ostacoli:
                cactus["x"] -= 1.5

            # Rimozione dei cactus che sono usciti fuori schermo
            ostacoli_visibili = []
            for c in ostacoli:
                if c["x"] > -10:
                    ostacoli_visibili.append(c)
            ostacoli = ostacoli_visibili

            # Generazione di nuovi cactus (singoli o coppie ravvicinate)
            distanza_da_ultimo_cactus += 1
            if distanza_da_ultimo_cactus > 24:
                # 25% di probabilità di generare un nuovo ostacolo
                if random.random() < 0.25:
                    pattern = random.choice(["piccolo", "grande", "coppia_grande_piccolo", "coppia_piccolo_grande"])

                    if pattern == "piccolo":
                        ostacoli.append(crea_cactus("piccolo", LARGHEZZA - 2))
                        distanza_da_ultimo_cactus = 0
                    elif pattern == "grande":
                        ostacoli.append(crea_cactus("grande", LARGHEZZA - 2))
                        distanza_da_ultimo_cactus = 0
                    elif pattern == "coppia_grande_piccolo":
                        # Cactus grande seguito da un cactus piccolo
                        ostacoli.append(crea_cactus("grande", LARGHEZZA - 2))
                        ostacoli.append(crea_cactus("piccolo", LARGHEZZA - 2 + CACTUS_GRANDE_W + 1))
                        distanza_da_ultimo_cactus = -6  # Margine extra dopo la coppia
                    elif pattern == "coppia_piccolo_grande":
                        # Cactus piccolo seguito da un cactus grande
                        ostacoli.append(crea_cactus("piccolo", LARGHEZZA - 2))
                        ostacoli.append(crea_cactus("grande", LARGHEZZA - 2 + CACTUS_PICCOLO_W + 1))
                        distanza_da_ultimo_cactus = -6  # Margine extra dopo la coppia

            # Controllo delle collisioni con ciascun cactus
            for cactus in ostacoli:
                if controlla_collisione(dino_y, cactus):
                    game_over = True
                    break

        # ----------------------------------------------------------------------
        # FASE 3: DISEGNO A SCHERMO (RENDERING)
        # ----------------------------------------------------------------------
        schermo.clear()

        # Intestazione con punteggio, record e comandi
        barra_info = f"SCORE: {punteggio:05d}   HI: {record:05d}   [SPAZIO]: Salta   [Q]/[ESC]: Esci"
        disegna_testo(schermo, 1, 2, barra_info)

        # Terreno
        disegna_terreno(schermo, tick)

        # Cactus
        for cactus in ostacoli:
            disegna_cactus(schermo, cactus)

        # Dinosauro: alterna il fotogramma di corsa ogni 3 tick
        frame_corsa = (tick // 3) % 2
        disegna_dinosauro(schermo, dino_y, in_salto, frame_corsa)

        # Messaggio di Game Over
        if game_over:
            testo_go = "=== GAME OVER ==="
            testo_sub = "Premi [SPAZIO] o [R] per rigiocare oppure [Q] per uscire"
            disegna_testo(schermo, 6, (LARGHEZZA - len(testo_go)) // 2, testo_go)
            disegna_testo(schermo, 8, (LARGHEZZA - len(testo_sub)) // 2, testo_sub)

        # Visualizza le modifiche nel terminale
        schermo.refresh()

        # Controllo della velocità di gioco (~30 FPS)
        time.sleep(0.035)


# ==============================================================================
# 4. AVVIO DEL PROGRAMMA
# ==============================================================================

def main() -> None:
    """
    Inizializza la modalità curses in modo sicuro:
    curses.wrapper si assicura di ripristinare il terminale
    anche in caso di interruzioni o errori.
    """
    curses.wrapper(esegui_gioco)


if __name__ == "__main__":
    main()

