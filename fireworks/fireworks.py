#!/usr/bin/env python3
"""
=============================================================================
             SPETTACOLO PIROTECNICO ASCII IN PYTHON (CURSES & OOP)
=============================================================================
Questo programma dimostra:
 1. L'uso della libreria standard 'curses' per trasformare il terminale in una canvas 2D.
 2. La Programmazione Orientata agli Oggetti (OOP) per modellare entità autonome:
    - Classe 'FuocoArtificio': gestisce il ciclo vitale e la macchina a stati.
    - Classe 'Particella': modella la fisica di ogni frammento dell'esplosione.
 3. Una Macchina a Stati Finiti (FSM):
    - LANCIO -> ESPLOSIONE -> DIFFUSIONE -> DISSOLVENZA -> CONCLUSO
 4. Il Game Loop con temporizzazione e gestione di animazioni simultanee.
=============================================================================
"""

import curses
import math
import random
import time
from enum import Enum, auto
from typing import Any, List


class StatoFuoco(Enum):
    """
    Stati del ciclo di vita di un fuoco d'artificio.
    Una Macchina a Stati Finiti (FSM) permette all'oggetto di cambiare
    comportamento e grafica in base alla fase in cui si trova.
    """
    LANCIO = auto()        # Il razzo sale verso il cielo lasciando una scia
    ESPLOSIONE = auto()    # Breve lampo iniziale al culmine della salita
    DIFFUSIONE = auto()    # Le particelle si espandono nello spazio
    DISSOLVENZA = auto()   # I frammenti perdono energia, cadono e svaniscono
    CONCLUSO = auto()      # L'animazione è conclusa, pronto per la rimozione


class Particella:
    """
    Rappresenta una singola particella generata dall'esplosione.
    Incapsula posizione, velocità, gravità, colore e durata della vita.
    """

    # Caratteri ASCII usati per rappresentare la degradazione energetica della particella
    CARATTERI_SCINTILLA = ["*", "+", "o", ".", "'", "·"]

    def __init__(self, x: float, y: float, vx: float, vy: float, coppia_colore: int, vita: int):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.coppia_colore = coppia_colore
        self.vita_massima = vita
        self.vita = vita
        # Attrito dell'aria e gravità
        self.gravita = 0.04
        self.attrito = 0.96

    def aggiorna(self) -> None:
        """Aggiorna la fisica della particella (posizione, velocità e vita)."""
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravita  # La gravità spinge verso il basso (y crescente in curses)
        self.vx *= self.attrito  # La resistenza dell'aria rallenta la velocità orizzontale
        self.vita -= 1

    def e_viva(self) -> bool:
        """Verifica se la particella ha ancora energia vitale residua."""
        return self.vita > 0

    def ottieni_carattere(self) -> str:
        """Restituisce un carattere ASCII in base all'energia residua."""
        if self.vita <= 0:
            return " "
        # Calcola la percentuale di vita rimanente
        rapporto = 1.0 - (self.vita / self.vita_massima)
        idx = int(rapporto * (len(self.CARATTERI_SCINTILLA) - 1))
        idx = max(0, min(len(self.CARATTERI_SCINTILLA) - 1, idx))
        return self.CARATTERI_SCINTILLA[idx]


class FuocoArtificio:
    """
    Rappresenta un fuoco d'artificio completo.
    Gestisce la transizione tra i vari stati:
      LANCIO -> ESPLOSIONE -> DIFFUSIONE -> DISSOLVENZA -> CONCLUSO
    """

    CARATTERI_SCIA = ["|", "!", "^", ":", ".", "·"]

    def __init__(self, max_y: int, max_x: int, target_x: int = None, coppia_colore: int = None):
        self.max_y = max_y
        self.max_x = max_x

        # Posizione di partenza (fondo dello schermo)
        self.x = float(target_x if target_x is not None else random.randint(5, max_x - 6))
        self.y = float(max_y - 2)

        # Destinazione e traiettoria di lancio
        # Il rapporto d'aspetto dei caratteri del terminale è circa 2:1 (altezza:larghezza),
        # per cui moltiplichiamo le velocità orizzontali per compensare.
        self.target_y = float(random.randint(int(max_y * 0.15), int(max_y * 0.55)))
        self.velocita_lancio = random.uniform(0.7, 1.2)
        # Leggera deviazione orizzontale durante la salita
        self.vx = random.uniform(-0.15, 0.15)
        self.vy = -self.velocita_lancio

        # Colori e grafica
        self.coppia_colore = coppia_colore if coppia_colore is not None else random.randint(1, 6)
        self.stato = StatoFuoco.LANCIO

        # Contatori per le durate degli stati
        self.tick_esplosione = 0
        self.max_tick_esplosione = random.randint(3, 5)

        # Scia del razzo in salita: lista di coordinate [y, x, char, life]
        self.scia = []

        # Lista di particelle create durante l'esplosione
        self.particelle: list[Particella] = []

        # Tipo di disegno dell'esplosione (circolare, anello, scintille, salice piangente)
        self.pattern = random.choice(["circolare", "anello", "scintille", "salice"])

    def _crea_particelle(self) -> None:
        """Genera le particelle dell'esplosione in base al pattern scelto."""
        num_particelle = random.randint(35, 70)

        for _ in range(num_particelle):
            angolo = random.uniform(0, 2 * math.pi)

            if self.pattern == "circolare":
                velocita = random.uniform(0.3, 1.4)
                vita = random.randint(18, 32)
            elif self.pattern == "anello":
                velocita = random.uniform(1.0, 1.3)
                vita = random.randint(20, 28)
            elif self.pattern == "salice":  # Salice piangente: cade lentamente a pioggia
                velocita = random.uniform(0.2, 1.0)
                vita = random.randint(35, 55)
            else:  # scintille: velocità e vite molto variegate
                velocita = random.uniform(0.2, 1.8)
                vita = random.randint(12, 40)

            # Il fattore 2.0 su x compensa il fatto che le celle del terminale sono più alte che larghe (2:1)
            vx = math.cos(angolo) * velocita * 2.0
            vy = math.sin(angolo) * velocita

            p = Particella(
                x=self.x,
                y=self.y,
                vx=vx,
                vy=vy,
                coppia_colore=self.coppia_colore,
                vita=vita
            )
            if self.pattern == "salice":
                p.gravita = 0.02
                p.attrito = 0.98

            self.particelle.append(p)

    def aggiorna(self) -> None:
        """
        Aggiorna la logica interna del fuoco d'artificio in base al suo stato attuale.
        """
        if self.stato == StatoFuoco.LANCIO:
            # Aggiorna la scia
            self.scia.append([int(self.y), int(self.x), random.choice(self.CARATTERI_SCIA), 4])
            for t in self.scia:
                t[3] -= 1  # Decrementa la vita della traccia di scia
            self.scia = [t for t in self.scia if t[3] > 0]

            # Sposta il razzo verso l'alto
            self.x += self.vx
            self.y += self.vy

            # Controlla se il razzo ha raggiunto l'altezza prestabilita o la sommità
            if self.y <= self.target_y or self.y <= 2:
                self.stato = StatoFuoco.ESPLOSIONE
                self.tick_esplosione = 0

        elif self.stato == StatoFuoco.ESPLOSIONE:
            self.tick_esplosione += 1
            if self.tick_esplosione >= self.max_tick_esplosione:
                self._crea_particelle()
                self.stato = StatoFuoco.DIFFUSIONE

        elif self.stato == StatoFuoco.DIFFUSIONE:
            # Aggiorna tutte le particelle
            vive = 0
            for p in self.particelle:
                p.aggiorna()
                if p.e_viva():
                    vive += 1

            # Quando molte particelle hanno perso oltre metà vita, passiamo a DISSOLVENZA
            if vive < len(self.particelle) * 0.6:
                self.stato = StatoFuoco.DISSOLVENZA

        elif self.stato == StatoFuoco.DISSOLVENZA:
            vive = 0
            for p in self.particelle:
                p.aggiorna()
                if p.e_viva():
                    vive += 1

            # Quando tutte le particelle sono morte, il fuoco d'artificio è terminato
            if vive == 0:
                self.stato = StatoFuoco.CONCLUSO

    def disegna(self, stdscr: Any) -> None:
        """
        Disegna il fuoco d'artificio sulla canvas di curses in base al suo stato.
        """
        def disegna_sicuro(y: int, x: int, ch: str, attr: int):
            """Funzione helper per evitare crash se si disegna fuori dai limiti del terminale."""
            if 0 <= y < self.max_y - 1 and 0 <= x < self.max_x - 1:
                try:
                    stdscr.addch(y, x, ch, attr)
                except curses.error:
                    pass

        # 1. STATO: LANCIO
        if self.stato == StatoFuoco.LANCIO:
            # Disegna la scia
            for ty, tx, tch, tvita in self.scia:
                colore_scia = curses.color_pair(7) | curses.A_DIM if tvita < 3 else curses.color_pair(self.coppia_colore)
                disegna_sicuro(ty, tx, tch, colore_scia)

            # Disegna la testa del razzo
            disegna_sicuro(int(self.y), int(self.x), "^", curses.color_pair(self.coppia_colore) | curses.A_BOLD)

        # 2. STATO: ESPLOSIONE (Flash / Lampo iniziale)
        elif self.stato == StatoFuoco.ESPLOSIONE:
            cx, cy = int(self.x), int(self.y)
            flash_attr = curses.color_pair(7) | curses.A_BOLD  # Bianco brillante

            # Disegna un pattern di lampo attorno al centro
            disegna_sicuro(cy, cx, "#", flash_attr)
            disegna_sicuro(cy - 1, cx, "|", flash_attr)
            disegna_sicuro(cy + 1, cx, "|", flash_attr)
            disegna_sicuro(cy, cx - 2, "-", flash_attr)
            disegna_sicuro(cy, cx + 2, "-", flash_attr)
            disegna_sicuro(cy - 1, cx - 2, "/", flash_attr)
            disegna_sicuro(cy + 1, cx + 2, "/", flash_attr)
            disegna_sicuro(cy - 1, cx + 2, "\\", flash_attr)
            disegna_sicuro(cy + 1, cx - 2, "\\", flash_attr)

        # 3. STATO: DIFFUSIONE (Particelle in piena espansione luminosa)
        elif self.stato == StatoFuoco.DIFFUSIONE:
            for p in self.particelle:
                if p.e_viva():
                    ch = p.ottieni_carattere()
                    # Particelle con molta vita sono in grassetto/evidenza
                    attr = curses.color_pair(p.coppia_colore)
                    if p.vita > p.vita_massima * 0.6:
                        attr |= curses.A_BOLD
                    disegna_sicuro(int(p.y), int(p.x), ch, attr)

        # 4. STATO: DISSOLVENZA (Particelle che sfumano verso lo spegnimento)
        elif self.stato == StatoFuoco.DISSOLVENZA:
            for p in self.particelle:
                if p.e_viva():
                    ch = p.ottieni_carattere()
                    # Particelle morenti usano l'attributo A_DIM per un effetto visivo attenuato
                    attr = curses.color_pair(p.coppia_colore) | curses.A_DIM
                    disegna_sicuro(int(p.y), int(p.x), ch, attr)

    def e_concluso(self) -> bool:
        """Restituisce True se l'animazione del fuoco è completamente conclusa."""
        return self.stato == StatoFuoco.CONCLUSO


def inizializza_colori() -> None:
    """Inizializza le coppie di colori curses (Foreground / Background)."""
    curses.start_color()
    curses.use_default_colors()

    # Inizializziamo combinazioni di colori vibranti su sfondo predefinito/trasparente (-1)
    curses.init_pair(1, curses.COLOR_RED, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_BLUE, -1)
    curses.init_pair(5, curses.COLOR_MAGENTA, -1)
    curses.init_pair(6, curses.COLOR_CYAN, -1)
    curses.init_pair(7, curses.COLOR_WHITE, -1)


def disegna_hud(stdscr: Any, max_y: int, max_x: int, fuochi_attivi: int, spawn_automatico: bool) -> None:
    """Disegna l'interfaccia utente (HUD) con statistiche e tasti di controllo."""
    titolo = " 🎆 PYTHON ASCII FIREWORKS SHOW 🎆 "
    istruzioni = "[SPAZIO]: Lancia | [A]: Auto (" + ("ON" if spawn_automatico else "OFF") + ") | [C]: Pulisci | [Q]: Esci"
    stats = f"Fuochi attivi: {fuochi_attivi:02d}"

    try:
        if max_x > len(titolo) + 4 and max_y > 4:
            stdscr.addstr(0, max(0, (max_x - len(titolo)) // 2), titolo, curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(max_y - 1, 2, istruzioni, curses.color_pair(7) | curses.A_DIM)
            stdscr.addstr(max_y - 1, max(2, max_x - len(stats) - 3), stats, curses.color_pair(6) | curses.A_BOLD)
    except curses.error:
        pass


def main(stdscr: Any) -> None:
    """
    Funzione principale del Game Loop.
    Gestisce la frequenza dei fotogrammi (FPS), gli input utente non bloccanti
    e l'aggiornamento/rendering di tutte le istanze di FuocoArtificio.
    """
    curses.curs_set(0)       # Nasconde il cursore lampeggiante
    stdscr.nodelay(True)     # Rende getch() non bloccante
    stdscr.timeout(0)        # Nessun ritardo di attesa tasto
    inizializza_colori()

    # Lista contenente tutti i fuochi d'artificio contemporanei (gestione multi-oggetto)
    fuochi: list[FuocoArtificio] = []

    # Parametri di controllo del loop e dello spettacolo
    spawn_automatico = True
    cooldown_spawn = 0
    fps_target = 30
    durata_fotogramma = 1.0 / fps_target

    while True:
        inizio_fotogramma = time.time()

        # Dimensioni dinamiche del terminale (gestisce anche il resize della finestra)
        max_y, max_x = stdscr.getmaxyx()

        # 1. GESTIONE INPUT UTENTE (Non bloccante)
        try:
            tasto = stdscr.getch()
        except curses.error:
            tasto = -1

        if tasto in (ord('q'), ord('Q'), 27):  # Tasto 'q', 'Q' o ESC per uscire
            break
        elif tasto == ord(' '):  # Barra spaziatrice: lancia un fuoco manuale
            if len(fuochi) < 30:
                fuochi.append(FuocoArtificio(max_y, max_x))
        elif tasto in (ord('a'), ord('A')):  # 'a': attiva/disattiva spawn automatico
            spawn_automatico = not spawn_automatico
        elif tasto in (ord('c'), ord('C')):  # 'c': cancella i fuochi attivi
            fuochi.clear()

        # 2. AUTO-SPAWN PERIODICO DI NUOVI FUOCHI
        if spawn_automatico:
            cooldown_spawn -= 1
            if cooldown_spawn <= 0:
                # 25% di probabilità di sparare una salva multipla sincronizzata
                if random.random() < 0.25:
                    quanti = random.randint(2, 4)
                    for _ in range(quanti):
                        if len(fuochi) < 25:
                            fuochi.append(FuocoArtificio(max_y, max_x))
                else:
                    if len(fuochi) < 20:
                        fuochi.append(FuocoArtificio(max_y, max_x))

                # Intervallo casuale prima della prossima esplosione
                cooldown_spawn = random.randint(6, 20)

        # 3. AGGIORNAMENTO LOGICO DEGLI OGGETTI (UPDATE)
        for fw in fuochi:
            fw.aggiorna()

        # Pulizia (Garbage Collection logico): rimuove i fuochi nello stato CONCLUSO
        fuochi = [fw for fw in fuochi if not fw.e_concluso()]

        # 4. RENDERING GRAFICO (DRAW)
        stdscr.erase()  # Pulisce il buffer dello schermo

        # Disegna tutti i fuochi d'artificio
        for fw in fuochi:
            fw.disegna(stdscr)

        # Disegna la barra di stato / HUD
        disegna_hud(stdscr, max_y, max_x, len(fuochi), spawn_automatico)

        # Applica i cambiamenti sullo schermo reale (Double Buffering)
        stdscr.refresh()

        # 5. REGOLAZIONE DELLA TEMPORIZZAZIONE (Frame Rate Limiting)
        tempo_impiegato = time.time() - inizio_fotogramma
        tempo_attesa = durata_fotogramma - tempo_impiegato
        if tempo_attesa > 0:
            time.sleep(tempo_attesa)


if __name__ == "__main__":
    # curses.wrapper protegge il terminale ripristinandolo in caso di chiusura imprevista
    curses.wrapper(main)
