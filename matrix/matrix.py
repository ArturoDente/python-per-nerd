#!/usr/bin/env python3
"""
================================================================================
  MATRIX DIGITAL RAIN — PYTHON PER NERDS
  Dal Normale Scrolling della Shell alla Grafica 2D con Curses
================================================================================
Autore: Francesco Clementoni
Librerie: Esclusivamente Libreria Standard Python (curses, time, random, sys, argparse)
Modalità:
  1. --scroll : Dimostrazione didattica a scorrimento riga per riga (senza librerie)
  2. Standard : Animazione 2D autentica con Curses, code sfumate, glitch e Easter Egg
================================================================================
"""

import sys
import time
import random
import argparse
import curses
from typing import List, Dict, Any, Tuple

# ==============================================================================
# 1. SET DI CARATTERI ASCII & COSTANTI DI CONFIGURAZIONE
# ==============================================================================

# Set di caratteri ASCII visivamente densi per ricreare l'effetto "Matrix"
CARATTERI_MATRIX = (
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "@#$%&*+-=<>/\\[]|~^!?{}()[]:;\""
)

# Messaggio segreto per l'Easter Egg tematico
MESSAGGIO_SEGRETO = "Wake up, Neo..."
DURATA_FLASH_SECONDI = 2.0         # Durata della pausa luminosa a centro schermo
COOLDOWN_MESSAGGIO_SECONDI = 30.0  # Intervallo minimo tra comparsate automatiche

# Temi cromatici supportati per la modalità Curses
TEMI_COLORE = [
    "Verde Matrix (Classico)",
    "Ambra CRT (Fosfori Caldi)",
    "Cyberpunk Ciano (Neon)",
    "Allarme Rosso (Red Alert)",
    "Monocromatico Bianco"
]


# ==============================================================================
# 2. IMPLEMENTAZIONE 1: SCORRIMENTO DELLA SHELL SENZA LIBRERIE ("FOR DUMMIES")
# ==============================================================================

def esegui_scorrimento_senza_librerie() -> None:
    """
    Versione introduttiva elementare:
    genera una riga di testo con caratteri casuali o spazi vuoti e la stampa
    a schermo, sfruttando il normale scorrimento verticale (scrolling) di print().
    """
    LARGHEZZA_SCHERMO = 80
    print("\033[2J\033[H", end="")  # Pulisce lo schermo
    print("=== MATRIX RAIN: VERSIONE BASE (SCORRIMENTO CON PRINT) ===")
    print("Premi CTRL+C per fermare.\n")
    time.sleep(1.0)

    try:
        while True:
            riga = ""
            for _ in range(LARGHEZZA_SCHERMO):
                # 5% di probabilità di avere un carattere, 95% di avere uno spazio vuoto
                if random.random() < 0.05:
                    riga += random.choice(CARATTERI_MATRIX)
                else:
                    riga += " "

            # Stampa la riga in verde usando il codice colore ANSI \033[32m
            print(f"\033[32m{riga}\033[0m")
            time.sleep(0.04)

    except KeyboardInterrupt:
        print("\nSimulazione a scorrimento interrotta.")


# ==============================================================================
# 3. IMPLEMENTAZIONE 2: DIGITAL RAIN 2D CON CURSES (ANIMAZIONE AUTENTICA)
# ==============================================================================

def crea_colonna_matrix(max_y: int, x: int, e_messaggio: bool = False) -> Dict[str, Any]:
    """
    Inizializza lo stato matematico di un flusso di caratteri indipendente (Stream).
    Ogni flusso possiede una posizione verticale y (in virgola mobile per velocità
    fluide), una velocità di caduta autonoma, una lunghezza e una coda di caratteri.
    Se 'e_messaggio' è True, la colonna trasporterà il messaggio segreto 'Wake up, Neo...'.
    """
    if e_messaggio:
        # Invertiamo l'ordine dei caratteri nella lista in modo che l'indice 0 (la testa che cade per prima, in basso)
        # contenga l'ultimo carattere ('.'), mentre la coda in alto contenga il primo carattere ('W').
        # In questo modo, leggendo dall'alto verso il basso a video si legge correttamente "Wake up, Neo...".
        caratteri = list(reversed(MESSAGGIO_SEGRETO))
        lunghezza = len(caratteri)
        velocita = 0.50  # Velocità controllata per ottima leggibilità
        pos_y = 0.0      # Parte immediatamente dal bordo superiore senza attese
        cooldown = 0
    else:
        lunghezza = random.randint(8, max(12, max_y - 2))
        velocita = random.uniform(0.35, 1.25)  # Righe per frame
        pos_y = float(-random.randint(0, max_y))
        caratteri = [random.choice(CARATTERI_MATRIX) for _ in range(lunghezza)]
        cooldown = random.randint(0, 15)

    return {
        "x": x,
        "y": pos_y,
        "lunghezza": lunghezza,
        "velocita": velocita,
        "caratteri": caratteri,
        "cooldown": cooldown,
        "e_messaggio": e_messaggio,
        "flash_attivo": False,
        "flash_inizio": 0.0,
        "flash_eseguito": False
    }


def inizializza_coppie_colore_curses() -> None:
    """Configura le coppie di colori per tutti i temi cromatici supportati."""
    curses.start_color()
    curses.use_default_colors()

    # TEMA 0: Verde Matrix
    # Testa: Bianco / Corpo: Verde
    curses.init_pair(1, curses.COLOR_GREEN, -1)   # Verde standard
    curses.init_pair(2, curses.COLOR_WHITE, -1)   # Bianco luminoso (Testa / Flash)

    # TEMA 1: Ambra CRT
    curses.init_pair(3, curses.COLOR_YELLOW, -1)  # Giallo/Ambra standard
    curses.init_pair(4, curses.COLOR_RED, -1)     # Rosso/Arancio (Coda calda)

    # TEMA 2: Cyberpunk Ciano
    curses.init_pair(5, curses.COLOR_CYAN, -1)    # Ciano standard
    curses.init_pair(6, curses.COLOR_BLUE, -1)    # Blu scuro (Coda neon)

    # TEMA 3: Allarme Rosso
    curses.init_pair(7, curses.COLOR_RED, -1)     # Rosso intenso
    curses.init_pair(8, curses.COLOR_MAGENTA, -1) # Magenta (Coda)


def ottieni_attributo_gradiente(indice_dalla_testa: int, lunghezza: int, tema_idx: int) -> int:
    """
    Calcola l'attributo di colore e brillantezza in base alla distanza dalla testa del flusso.
    Realizza il celebre gradiente luminoso decrescente della pioggia digitale.
    """
    # 1. La testa (indice 0) brilla sempre in Bianco Luminoso
    if indice_dalla_testa == 0:
        return curses.color_pair(2) | curses.A_BOLD

    frazione_distanza = indice_dalla_testa / max(1, lunghezza)

    # TEMA 0: Verde Matrix
    if tema_idx == 0:
        if frazione_distanza < 0.25:
            return curses.color_pair(1) | curses.A_BOLD  # Verde brillante
        elif frazione_distanza < 0.70:
            return curses.color_pair(1)                  # Verde medio
        else:
            return curses.color_pair(1) | curses.A_DIM   # Verde attenuato

    # TEMA 1: Ambra CRT
    elif tema_idx == 1:
        if frazione_distanza < 0.30:
            return curses.color_pair(3) | curses.A_BOLD  # Giallo ambra intenso
        elif frazione_distanza < 0.75:
            return curses.color_pair(3)                  # Ambra normale
        else:
            return curses.color_pair(4) | curses.A_DIM   # Rosso tenue

    # TEMA 2: Cyberpunk Ciano
    elif tema_idx == 2:
        if frazione_distanza < 0.30:
            return curses.color_pair(5) | curses.A_BOLD  # Ciano elettrico
        elif frazione_distanza < 0.75:
            return curses.color_pair(5)                  # Ciano medio
        else:
            return curses.color_pair(6) | curses.A_DIM   # Blu attenuato

    # TEMA 3: Allarme Rosso
    elif tema_idx == 3:
        if frazione_distanza < 0.30:
            return curses.color_pair(7) | curses.A_BOLD  # Rosso fuoco
        elif frazione_distanza < 0.75:
            return curses.color_pair(7)                  # Rosso normale
        else:
            return curses.color_pair(8) | curses.A_DIM   # Magenta scuro

    # TEMA 4: Monocromatico Bianco
    else:
        if frazione_distanza < 0.35:
            return curses.color_pair(2) | curses.A_BOLD
        elif frazione_distanza < 0.80:
            return curses.color_pair(2)
        else:
            return curses.color_pair(2) | curses.A_DIM


def esegui_matrix_curses(stdscr) -> None:
    """
    Game Loop 2D con Curses: anima gocce indipendenti con velocità asincrone,
    mutazione casuale dei caratteri (glitch), trigger del messaggio segreto
    ed effetto flash a centro schermo.
    """
    curses.curs_set(0)           # Nasconde il cursore lampeggiante
    stdscr.nodelay(True)         # Lettura tastiera non bloccante
    stdscr.keypad(True)          # Supporto tasti speciali
    inizializza_coppie_colore_curses()

    max_y, max_x = stdscr.getmaxyx()

    # Inizializza flussi per ogni colonna del terminale
    colonne: List[Dict[str, Any]] = [crea_colonna_matrix(max_y, x) for x in range(max_x)]

    # Avvia subito il messaggio segreto all'apertura al centro dello schermo
    idx_segreto = max_x // 2
    if 0 <= idx_segreto < len(colonne):
        colonne[idx_segreto] = crea_colonna_matrix(max_y, idx_segreto, e_messaggio=True)

    # Variabili di stato dell'animazione
    tema_idx = 0
    in_pausa = False
    mostra_hud = True
    moltiplicatore_velocita = 1.0
    fps_target = 30
    periodo_frame = 1.0 / fps_target
    in_esecuzione = True
    ultimo_spawn_messaggio = time.perf_counter()

    while in_esecuzione:
        t_inizio = time.perf_counter()

        # 1. Gestione ridimensionamento dinamico della finestra
        cur_y, cur_x = stdscr.getmaxyx()
        if cur_y != max_y or cur_x != max_x:
            max_y, max_x = cur_y, cur_x
            colonne = [crea_colonna_matrix(max_y, x) for x in range(max_x)]

        # 2. Gestione Input Asincrono da Tastiera
        try:
            tasto = stdscr.getch()
        except Exception:
            tasto = -1

        if tasto in (27, ord('q'), ord('Q')):        # ESC o Q: Esci
            in_esecuzione = False
            break
        elif tasto == ord(' '):                       # Spazio: Pausa/Riprendi
            in_pausa = not in_pausa
        elif tasto in (ord('c'), ord('C')):           # C: Cambia Tema Cromatico
            tema_idx = (tema_idx + 1) % len(TEMI_COLORE)
        elif tasto in (ord('w'), ord('W')):           # W: Genera IMMEDIATAMENTE il messaggio segreto
            idx_seg = max_x // 2
            if 0 <= idx_seg < len(colonne):
                colonne[idx_seg] = crea_colonna_matrix(max_y, idx_seg, e_messaggio=True)
                ultimo_spawn_messaggio = time.perf_counter()
        elif tasto in (ord('m'), ord('M')):           # M: Toggle HUD informativo
            mostra_hud = not mostra_hud
        elif tasto in (ord('r'), ord('R')):           # R: Reset e re-inizializzazione
            colonne = [crea_colonna_matrix(max_y, x) for x in range(max_x)]
            idx_seg = max_x // 2
            if 0 <= idx_seg < len(colonne):
                colonne[idx_seg] = crea_colonna_matrix(max_y, idx_seg, e_messaggio=True)
            ultimo_spawn_messaggio = time.perf_counter()
        elif tasto in (ord('+'), ord('='), curses.KEY_UP):   # Aumenta velocità
            moltiplicatore_velocita = min(2.5, moltiplicatore_velocita + 0.15)
        elif tasto in (ord('-'), ord('_'), curses.KEY_DOWN): # Diminuisci velocità
            moltiplicatore_velocita = max(0.2, moltiplicatore_velocita - 0.15)

        # 3. Fase di Aggiornamento Logica (Update)
        if not in_pausa:
            ora_attuale = time.perf_counter()

            # Controllo spawn automatico periodico del messaggio segreto (ogni ~30 secondi)
            c_e_messaggio_attivo = any(c.get("e_messaggio", False) for c in colonne)
            if not c_e_messaggio_attivo and (ora_attuale - ultimo_spawn_messaggio > COOLDOWN_MESSAGGIO_SECONDI):
                idx_seg = random.randint(5, max(5, max_x - 6))
                if 0 <= idx_seg < len(colonne):
                    colonne[idx_seg] = crea_colonna_matrix(max_y, idx_seg, e_messaggio=True)
                    ultimo_spawn_messaggio = ora_attuale

            for colonna in colonne:
                # Se è in cooldown prima della rinascita, decrementa il timer
                if colonna["cooldown"] > 0:
                    colonna["cooldown"] -= 1
                    continue

                # Gestione speciale del messaggio segreto: trigger a centro schermo
                if colonna.get("e_messaggio", False):
                    y_centro_msg = colonna["y"] - (colonna["lunghezza"] / 2.0)
                    y_centro_schermo = max_y / 2.0

                    # Trigger garantito non appena il centro del messaggio attraversa la mezzeria dello schermo
                    if y_centro_msg >= y_centro_schermo and not colonna["flash_eseguito"]:
                        colonna["flash_attivo"] = True
                        colonna["flash_inizio"] = time.perf_counter()
                        colonna["flash_eseguito"] = True

                    # Se il flash è attivo, verifica se sono trascorsi i 2 secondi di durata
                    if colonna["flash_attivo"]:
                        if time.perf_counter() - colonna["flash_inizio"] > DURATA_FLASH_SECONDI:
                            colonna["flash_attivo"] = False
                        else:
                            # Durante il flash il messaggio si sofferma a centro schermo per essere letto con calma
                            continue

                # Avanzamento verticale continuo in base alla velocità
                colonna["y"] += colonna["velocita"] * moltiplicatore_velocita

                # Mutazione stocastica (effetto "glitch" del codice Matrix sulle sole colonne normali)
                if not colonna.get("e_messaggio", False) and random.random() < 0.10:
                    idx_mutazione = random.randint(0, colonna["lunghezza"] - 1)
                    colonna["caratteri"][idx_mutazione] = random.choice(CARATTERI_MATRIX)

                # Controllo se la coda del flusso è completamente uscita dal fondo dello schermo
                coda_y = int(colonna["y"]) - colonna["lunghezza"]
                if coda_y > max_y:
                    # Rigenera una normale colonna casuale
                    nuova_colonna = crea_colonna_matrix(max_y, colonna["x"], e_messaggio=False)
                    colonna.update(nuova_colonna)

        # 4. Fase di Disegno (Render)
        stdscr.erase()

        # Disegna tutti i caratteri delle colonne
        for colonna in colonne:
            x_pos = colonna["x"]
            y_testa = int(colonna["y"])
            lunghezza = colonna["lunghezza"]
            e_msg = colonna.get("e_messaggio", False)
            is_flash = colonna.get("flash_attivo", False)

            for i in range(lunghezza):
                riga_y = y_testa - i
                if 0 <= riga_y < max_y and 0 <= x_pos < max_x:
                    char = colonna["caratteri"][i]

                    if is_flash:
                        # Effetto Flash a centro schermo: Bianco puro brillante nitido
                        attr = curses.color_pair(2) | curses.A_BOLD
                    elif e_msg:
                        # Mentre scende, il messaggio è in verde brillante ben evidenziato
                        attr = curses.color_pair(1) | curses.A_BOLD
                    else:
                        attr = ottieni_attributo_gradiente(i, lunghezza, tema_idx)

                    try:
                        stdscr.addstr(riga_y, x_pos, char, attr)
                    except Exception:
                        pass

        # Disegna l'HUD informativo se abilitato
        if mostra_hud and max_y > 4 and max_x > 30:
            stato_txt = "[PAUSA]" if in_pausa else "[ATTIVO]"
            info_linea = (
                f" THE MATRIX RAIN 2D │ {TEMI_COLORE[tema_idx]} │ "
                f"Vel: {moltiplicatore_velocita:.1f}x │ {stato_txt} │ "
                f"[SPAZIO] Pausa  [C] Colore  [W] Messaggio  [+/-] Vel  [M] HUD  [Q] Esci "
            )
            attr_hud = curses.color_pair(2) | curses.A_STANDOUT
            try:
                stdscr.addstr(0, max(0, (max_x - len(info_linea)) // 2), info_linea[:max_x - 1], attr_hud)
            except Exception:
                pass

        # Visualizzazione buffer e stabilizzazione FPS
        stdscr.refresh()
        tempo_impiegato = time.perf_counter() - t_inizio
        tempo_attesa = periodo_frame - tempo_impiegato
        if tempo_attesa > 0:
            time.sleep(tempo_attesa)


# ==============================================================================
# 4. ENTRY POINT PRINCIPALE CON PARSER CLI
# ==============================================================================

def main() -> None:
    """Punto d'ingresso con selezione della modalità dimostrativa o Curses."""
    parser = argparse.ArgumentParser(
        description="Matrix Digital Rain — Dal normale scrolling alla grafica 2D con Curses (Python per Nerds)"
    )
    parser.add_argument(
        "-s", "--scroll",
        action="store_true",
        help="Esegue la dimostrazione introduttiva a scorrimento riga per riga (senza libreria curses)."
    )

    args = parser.parse_args()

    if args.scroll:
        # Modalità 1: puro scrolling shell senza curses
        esegui_scorrimento_senza_librerie()
    else:
        # Modalità 2: animazione autentica 2D con Curses
        try:
            curses.wrapper(esegui_matrix_curses)
        except KeyboardInterrupt:
            pass
        finally:
            print("\nSei uscito dal Matrix. Buona programmazione con Python per Nerds!\n")


if __name__ == "__main__":
    main()
